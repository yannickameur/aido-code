"""Minimal REPL loop for AIDO Code.

WI-06 scope: `/help`, `/exit`, `/status`, `/config`, `/validate`,
`/workers`, `/run`, and a clear message for unknown commands. `/run`
advances project work; `/resume` switches frontend sessions.

WI-M1.1-03 extends `/status`/`/workers` with an explicit `--probe`
opt-in (see docs/CLI_SPEC.md, "M1.1"): `/status` (no flags) now also
renders the full worker list, still with zero provider probes; `--probe`
on either command is the only thing that ever calls
`EngineClient.probe_workers()`, and both share the exact same
`format_workers()` rendering path (see `_format_workers_section()`).

WI-M1.4-07C moved `/workers` and `/config` onto the modern project
loading path: `aido_code.project_command.load_project_command_context`
(manifest -> `ROADMAP.md` -> resources -> AIDO's own global
`WorkerRegistry`, see `docs/PROJECT_CONTRACT.md` §§2-4) plus
`aido_code.engine_plan.build_engine_plan` (§6), the exact same path
`aido-code validate`/`run` already use
(`aido_code.project_command`/`aido_code.__main__`). `aido.yaml` no
longer carries a `workers:` section at all, so neither command ever
reads one from a project; `/workers --probe` still shares
`_format_workers_section()`/`format_workers()` with `/status --probe`
— no second worker-rendering implementation.

WI-M1.4-07D moves `/status` onto that same modern loading path
(`_open_project_command_engine()`, shared with `/workers`/`/config`).
`format_status()` combines the roadmap's own current-milestone id/status
(`ROADMAP.md`'s "## Current milestone" — intended work) with the real,
unchanged `OrchestratorEngine.status()` snapshot (actual persisted
work) — never inventing a WorkItem/MVP status from `ROADMAP.md` itself:
before a project's first `/run`, `.status()` reports `initialized=False`
and nothing about work items is fabricated to fill the gap."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TextIO

from aido_code.engine_client import (
    EngineClient,
    EngineError,
    ProjectSnapshot,
    ProjectStatusSnapshot,
    ProviderSnapshot,
    RunResult,
    WorkerSnapshot,
)
from aido_code.engine_plan import EnginePlanError, build_engine_plan
from aido_code.i18n import event_label, interactive_lang, t
from aido_code.intent import Intent, interpret
from aido_code.project_command import ProjectCommandContext, load_project_command_context
from aido_code.project_manifest import ProjectManifestError
from aido_code.project_resources import ProjectResourcesError
from aido_code.roadmap import CurrentMilestone, RoadmapError
from aido_code.session import Session, SessionError, SessionProjectError, SessionStore, project_manifest_path
from aido_code.session_commands import pick_session, resume_selected
from orchestrator.worker_registry import WorkerRegistryError

COMMANDS: dict[str, str] = {
    "/help": "List available commands.",
    "/status": "Show the project's real, persisted status, plus the full worker list.",
    "/status --probe": "Same as /status, plus one real provider probe of each worker's state.",
    "/workers": "List configured workers (enabled and disabled), no provider probe.",
    "/workers --probe": "Same as /workers, plus one real provider probe of each worker's state.",
    "/config": "Show the loaded aido.yaml's validated configuration.",
    "/validate": "Validate aido.yaml and its worker registry.",
    "/run": "Start or resume the project (drives the engine to completion or WAITING).",
    "/resume": "Choose an existing session.",
    "/new": "Create and switch to a new session.",
    "/exit": "Exit the REPL.",
}

DEFAULT_CONFIG_PATH = "aido.yaml"

_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
_CONTROL_CHAR_ESCAPES = {"\r": "\\r", "\n": "\\n", "\t": "\\t"}


def sanitize_for_terminal(value: object) -> str:
    """Neutralizes ESC/ANSI sequences, bare CR, injected LF, and every other
    C0/C1 control character in a value read from an OrchestratorEngine
    snapshot, so it can never manipulate the terminal it is printed to.
    Every dynamic snapshot-derived value rendered anywhere in this module
    passes through this one function — never a second, duplicated one.
    Ordinary Unicode text (accents, emoji, non-Latin scripts) is returned
    unchanged; the snapshot value itself is never mutated, only the string
    handed back for printing."""
    text = value if isinstance(value, str) else str(value)

    def _escape(match: re.Match[str]) -> str:
        char = match.group()
        return _CONTROL_CHAR_ESCAPES.get(char, f"\\x{ord(char):02x}")

    return _CONTROL_CHAR_RE.sub(_escape, text)


def format_help(lang: str = "en") -> str:
    lines = [t("help.title", lang)]
    lines.extend(f"  {name} - {t(f'help.cmd.{name}', lang)}" for name in COMMANDS)
    return "\n".join(lines)


def format_config(context: ProjectCommandContext, snapshot: ProjectSnapshot) -> str:
    """Renders the manifest/roadmap facts (`docs/PROJECT_CONTRACT.md` §7)
    plus the same engine-derived facts `/config` already showed —
    `initial_prompt` passes through `sanitize_for_terminal()`, the same
    terminal-safety convention every other snapshot-derived value here
    uses (M1.3, WI-M1.3-02). Never a raw file dump, never a credential,
    never a project-owned worker registry (`aido.yaml` has none, §2)."""
    providers = (
        ", ".join(sanitize_for_terminal(provider) for provider in snapshot.providers)
        if snapshot.providers
        else "(none)"
    )
    manifest = context.manifest
    milestone = context.roadmap.milestone
    lines = [
        f"project: {sanitize_for_terminal(manifest.project.id)} ({sanitize_for_terminal(manifest.project.name)})",
        f"workspace: {sanitize_for_terminal(manifest.project.workspace)}",
        f"roadmap: {sanitize_for_terminal(manifest.roadmap)}",
        f"resources: {sanitize_for_terminal(manifest.resources)}",
        f"initial_prompt: {sanitize_for_terminal(manifest.initial_prompt)}",
        f"current_milestone_id: {sanitize_for_terminal(milestone.id)}",
        f"current_milestone_status: {sanitize_for_terminal(milestone.status)}",
        f"enabled_workers: {sanitize_for_terminal(snapshot.enabled_worker_count)}",
        f"providers: {providers}",
        f"permission_mode: {sanitize_for_terminal(snapshot.permission_mode.upper())}",
        f"base_branch: {sanitize_for_terminal(snapshot.base_branch)}",
        f"qa_commands: {sanitize_for_terminal(snapshot.qa_command_count)}",
    ]
    return "\n".join(lines)


def format_status(milestone: CurrentMilestone, snapshot: ProjectStatusSnapshot) -> str:
    """Combines `ROADMAP.md`'s own current-milestone facts (intended
    work: `milestone.id`/`.status`, DRAFT/APPROVED) with the real,
    persisted `OrchestratorEngine.status()` snapshot (actual work: what
    has genuinely run). The engine snapshot is the only source for
    project/MVP/WorkItem status — before a project's first `/run`,
    `snapshot.initialized` is `False` and nothing else is fabricated to
    fill the gap."""
    lines = [
        f"current_milestone_id: {sanitize_for_terminal(milestone.id)}",
        f"current_milestone_status: {sanitize_for_terminal(milestone.status)}",
        "",
    ]

    if not snapshot.initialized:
        lines.append("NOT_INITIALIZED")
        lines.append("Run /run to initialize and start this project.")
        return "\n".join(lines)

    lines.append(
        f"project: {sanitize_for_terminal(snapshot.project_id)} "
        f"({sanitize_for_terminal(snapshot.project_name)})"
    )
    if snapshot.mvp is None:
        lines.append("mvp: (not configured)")
    elif snapshot.mvp.status is None:
        lines.append(f"mvp: {sanitize_for_terminal(snapshot.mvp.mvp_id)} (not yet created)")
    else:
        lines.append(
            f"mvp: {sanitize_for_terminal(snapshot.mvp.mvp_id)} "
            f"status={sanitize_for_terminal(snapshot.mvp.status)}"
        )

    if snapshot.work_items:
        lines.append("")
        lines.append("work items:")
        for work_item in snapshot.work_items:
            line = (
                f"  {sanitize_for_terminal(work_item.work_item_id)}: "
                f"{sanitize_for_terminal(work_item.status)}"
            )
            if work_item.blocked_reason:
                line += f" (blocked_reason={sanitize_for_terminal(work_item.blocked_reason)})"
            lines.append(line)

            if work_item.last_execution is not None:
                execution = work_item.last_execution
                lines.append(
                    f"      last execution: worker={sanitize_for_terminal(execution.worker_id)} "
                    f"provider={sanitize_for_terminal(execution.provider)} "
                    f"status={sanitize_for_terminal(execution.status)}"
                )
            if work_item.wait is not None:
                wait = work_item.wait
                providers = ",".join(sanitize_for_terminal(provider) for provider in wait.providers) or "(any)"
                lines.append(
                    f"      wait: phase={sanitize_for_terminal(wait.phase)} "
                    f"eligible_at={sanitize_for_terminal(wait.eligible_at)} "
                    f"providers={providers}"
                )
    return "\n".join(lines)


def format_run(result: RunResult, *, include_events: bool = True, lang: str = "en") -> str:
    """``include_events=False`` omits the ``events:`` section, for callers
    that already streamed those events live."""
    def metric_label(name: str) -> str:
        return f"{name} ({t('run.' + name, lang)})" if lang != "en" else name

    lines = [
        f"{metric_label('cycles_run')}: {sanitize_for_terminal(result.cycles_run)}",
        f"{metric_label('all_terminal')}: {sanitize_for_terminal(result.all_terminal)}",
        f"{metric_label('reached_max_cycles')}: {sanitize_for_terminal(result.reached_max_cycles)}",
    ]
    if lang != "en":
        lines.insert(0, t("run.summary", lang))

    if result.work_items:
        lines.append("")
        lines.append(t("run.work_items", lang))
        for work_item in result.work_items:
            line = (
                f"  {sanitize_for_terminal(work_item.work_item_id)}: "
                f"{sanitize_for_terminal(work_item.status)}"
            )
            if work_item.blocked_reason:
                line += f" (blocked_reason={sanitize_for_terminal(work_item.blocked_reason)})"
            lines.append(line)

    if include_events and result.events:
        lines.append("")
        lines.append(t("run.events", lang))
        for event in result.events:
            label = event_label(event.kind, lang) if lang == "fr" else None
            kind = sanitize_for_terminal(event.kind)
            lines.append(
                f"  {kind}{f' ({label})' if label else ''}: "
                f"work_item={sanitize_for_terminal(event.work_item_id)}"
            )

    from aido_code.live_run import format_diagnostics

    diagnostics = format_diagnostics(getattr(result, "diagnostics", ()), lang=lang)
    if diagnostics:
        lines.append("")
        lines.append(diagnostics)

    return "\n".join(lines)


def _worker_probe_state(worker: WorkerSnapshot, provider_states: dict[str, ProviderSnapshot]) -> str:
    """Never fabricates a per-worker state: disabled workers are never
    probed (``probe_workers()`` only probes enabled workers' providers),
    and workers sharing one provider honestly share that provider's own
    observed state."""
    if not worker.enabled:
        return "disabled"
    state = provider_states.get(worker.provider)
    if state is None:
        return "unknown"
    if state.available:
        return "available"
    if state.reason.startswith("probe_error"):
        return sanitize_for_terminal(state.reason)
    if state.reason == "quota_exhausted":
        return "quota"
    if state.reason in ("auth_error", "provider_error"):
        return f"unavailable ({sanitize_for_terminal(state.reason)})"
    return "unknown"


def format_workers(
    snapshots: tuple[WorkerSnapshot, ...],
    provider_states: dict[str, ProviderSnapshot] | None = None,
) -> str:
    """Renders the static worker list; with ``provider_states`` (from
    ``probe_workers()``, keyed by provider) also renders each worker's
    real observable state. The single rendering path shared by
    `/status --probe` and `/workers --probe` (see `_format_workers_section()`)."""
    if not snapshots:
        return "(no workers configured)"

    lines = []
    for worker in snapshots:
        state = "enabled" if worker.enabled else "disabled"
        line = (
            f"  {sanitize_for_terminal(worker.worker_id)} ({sanitize_for_terminal(worker.display_name)}): "
            f"{state} provider={sanitize_for_terminal(worker.provider)} "
            f"backend={sanitize_for_terminal(worker.backend)} priority={sanitize_for_terminal(worker.priority)}"
        )
        if worker.model:
            line += f" model={sanitize_for_terminal(worker.model)}"
        if provider_states is not None:
            line += f" probe={_worker_probe_state(worker, provider_states)}"
        lines.append(line)
        capabilities = ", ".join(sanitize_for_terminal(capability) for capability in worker.capabilities) or "(none)"
        lines.append(f"      capabilities: {capabilities}")
    return "\n".join(lines)


def format_provider_quotas(providers: tuple[ProviderSnapshot, ...]) -> str:
    """Renders each provider's real quota facts exactly once per provider
    actually probed (``providers`` already has at most one ``ProviderSnapshot``
    per provider — see ``OrchestratorEngine.probe_workers()``), never once
    per worker. Unknown utilization/remaining/reset_at/reset-credit counts
    stay rendered as ``unknown`` text, never coerced to a fabricated value."""
    if not providers:
        return ""
    lines = ["provider quotas:"]
    for snapshot in sorted(providers, key=lambda p: p.provider):
        lines.append(f"  {sanitize_for_terminal(snapshot.provider)}:")
        if not snapshot.quota_windows:
            lines.append("    quota: unknown")
        for window in snapshot.quota_windows:
            utilization = sanitize_for_terminal(f"{window.utilization:.0%}") if window.utilization is not None else "unknown"
            remaining = sanitize_for_terminal(f"{window.remaining:.0%}") if window.remaining is not None else "unknown"
            reset_at = sanitize_for_terminal(window.reset_at) if window.reset_at is not None else "unknown"
            lines.append(
                f"    {sanitize_for_terminal(window.window_type)}: utilization={utilization} "
                f"remaining={remaining} reset_at={reset_at}"
            )
        for credit in snapshot.reset_credits:
            count = sanitize_for_terminal(credit.available_count) if credit.available_count is not None else "unknown"
            lines.append(
                f"    reset credit {sanitize_for_terminal(credit.title)}: "
                f"{sanitize_for_terminal(credit.status)} (available={count})"
            )
    return "\n".join(lines)


def _format_workers_section(
    workers: tuple[WorkerSnapshot, ...], providers: tuple[ProviderSnapshot, ...] | None
) -> str:
    """The one probe/rendering code path `/status --probe` and
    `/workers --probe` both call: `providers=None` renders the static
    view, otherwise it maps `probe_workers()`'s own ``ProviderSnapshot``
    tuple onto the workers that use each provider, plus that same tuple's
    quota facts (see `format_provider_quotas()`) — the single shared path
    for both commands, never a second, duplicated one."""
    if providers is None:
        return format_workers(workers)
    provider_states = {snapshot.provider: snapshot for snapshot in providers}
    sections = [format_workers(workers, provider_states)]
    quotas = format_provider_quotas(providers)
    if quotas:
        sections.append(quotas)
    return "\n\n".join(sections)


# Every domain error the modern project-command loading path
# (`load_project_command_context()`) or the typed engine plan builder
# (`build_engine_plan()`) can raise, plus the plain-constructor engine's
# own `EngineError` — the same set `aido_code.__main__._project_command`
# already catches for `validate`/`run`, reused here rather than
# duplicated for `/workers`/`/config`.
_PROJECT_COMMAND_ERRORS: tuple[type[Exception], ...] = (
    ProjectManifestError,
    RoadmapError,
    ProjectResourcesError,
    WorkerRegistryError,
    EnginePlanError,
    EngineError,
    OSError,
    ValueError,
)


def _open_project_command_engine(
    config_path: str,
    *,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> tuple[ProjectCommandContext, EngineClient]:
    """The one loading path `/status`, `/workers`, and `/config` share:
    manifest -> `ROADMAP.md` -> resources -> AIDO's own global
    `WorkerRegistry` (`aido_code.project_command.
    load_project_command_context`), then the typed engine plan
    (`aido_code.engine_plan.build_engine_plan`) injected into
    `OrchestratorEngine` via `EngineClient.from_config()` — never
    `EngineClient.open()`, since `aido.yaml` is no longer a
    `ProjectConfig`-shaped file. Exactly the same path `aido-code
    validate`/`run` already use (`aido_code.__main__`)."""
    context = load_project_command_context(config_path)
    plan = build_engine_plan(context.manifest, context.roadmap, context.resources)
    client = EngineClient.from_config(
        plan, worker_registry=context.worker_registry,
        provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
    )
    return context, client


def build_status_output(
    config_path: str,
    *,
    probe: bool = False,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> str:
    """The one `/status` rendering path — also called directly by the
    CLI-level `aido status` (`aido_code.__main__`), never a second
    implementation. Raises `_PROJECT_COMMAND_ERRORS` on a missing/invalid
    project rather than swallowing them: `_run_status()` below is the
    REPL's own thin wrapper that turns those into an inline error
    string; the CLI subcommand turns them into an `Error: ...` on
    stderr plus a non-zero exit instead."""
    context, client = _open_project_command_engine(
        config_path, provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
    )
    with client:
        snapshot = client.status()
        workers = client.workers()
        providers = client.probe_workers() if probe else None
    return "\n\n".join(
        [
            format_status(context.roadmap.milestone, snapshot),
            "workers:",
            _format_workers_section(workers, providers),
        ]
    )


def _run_status(
    config_path: str,
    *,
    probe: bool = False,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> str:
    try:
        return build_status_output(
            config_path,
            probe=probe,
            provider_adapters=provider_adapters,
            subprocess_runner=subprocess_runner,
        )
    except _PROJECT_COMMAND_ERRORS as exc:
        return f"Error: {exc}"


def _run_config(config_path: str) -> str:
    try:
        context, client = _open_project_command_engine(config_path)
        with client:
            snapshot = client.validate()
    except _PROJECT_COMMAND_ERRORS as exc:
        return f"Error: {exc}"
    return format_config(context, snapshot)


def _interrupt_helpers() -> tuple[object, str]:
    from aido_code.live_run import INTERRUPTED_NOTICE, run_interruptibly

    return run_interruptibly, INTERRUPTED_NOTICE


def _live_sink(output_stream: TextIO | None, lang: str = "en", event_sink: object | None = None) -> object | None:
    if event_sink is not None:
        return event_sink
    if output_stream is None:
        return None
    from aido_code.live_run import LiveRunRenderer

    return LiveRunRenderer(output_stream, lang=lang)


def _run_validate(config_path: str) -> str:
    try:
        with EngineClient.open(config_path) as client:
            client.validate()
    except EngineError as exc:
        return f"Validation failed: {exc}"
    return "Configuration is valid."


def _run_run(
    config_path: str,
    *,
    output_stream: TextIO | None = None,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
    lang: str = "en",
    interrupt: object | None = None,
    event_sink: object | None = None,
) -> str:
    try:
        with EngineClient.open(
            config_path, provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
        ) as client:
            run_interruptibly, notice = _interrupt_helpers()
            result = run_interruptibly(client, _live_sink(output_stream, lang, event_sink), interrupt)
    except EngineError as exc:
        return f"Error: {exc}"
    if result is None:
        return t("interrupted", lang) if lang != "en" else notice
    return format_run(result, include_events=output_stream is None, lang=lang)


def _run_session_validate(config_path: str) -> str:
    try:
        load_project_command_context(config_path)
    except _PROJECT_COMMAND_ERRORS as exc:
        return f"Validation failed: {exc}"
    return "Configuration is valid."


def _run_session_project(
    config_path: str,
    *,
    output_stream: TextIO | None = None,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
    lang: str = "en",
    interrupt: object | None = None,
    event_sink: object | None = None,
) -> str:
    try:
        context = load_project_command_context(config_path)
        if not context.roadmap.milestone.is_executable:
            return "Error: Current milestone is DRAFT. Not executable."
        plan = build_engine_plan(context.manifest, context.roadmap, context.resources)
        with EngineClient.from_config(
            plan, worker_registry=context.worker_registry,
            provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
        ) as client:
            run_interruptibly, notice = _interrupt_helpers()
            result = run_interruptibly(client, _live_sink(output_stream, lang, event_sink), interrupt)
            if result is None:
                return t("interrupted", lang) if lang != "en" else notice
            return format_run(result, include_events=output_stream is None, lang=lang)
    except _PROJECT_COMMAND_ERRORS as exc:
        return f"Error: {exc}"


def _run_workers(
    config_path: str,
    *,
    probe: bool = False,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> str:
    try:
        _context, client = _open_project_command_engine(
            config_path, provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
        )
        with client:
            snapshots = client.workers()
            providers = client.probe_workers() if probe else None
    except _PROJECT_COMMAND_ERRORS as exc:
        return f"Error: {exc}"
    return _format_workers_section(snapshots, providers)


def _format_why_waiting(snapshot: ProjectStatusSnapshot, work_item_id: str | None) -> str:
    """Answers only from the engine's own `status()` snapshot: a
    WorkItem's recorded status, `blocked_reason`, `wait` and last
    execution. Nothing is inferred or fabricated."""
    if not snapshot.initialized:
        return "Nothing has run yet (NOT_INITIALIZED); there is no WorkItem to explain. Run /run to start."
    items = snapshot.work_items
    if work_item_id is not None:
        items = tuple(i for i in items if i.work_item_id.lower() == work_item_id.lower())
        if not items:
            return f"The engine reports no WorkItem {sanitize_for_terminal(work_item_id)!s}."
    else:
        items = tuple(i for i in items if i.blocked_reason or i.wait is not None)
        if not items:
            return "The engine reports no WorkItem that is waiting or blocked."
    lines = []
    for item in items:
        line = f"{sanitize_for_terminal(item.work_item_id)}: status={sanitize_for_terminal(item.status)}"
        if item.blocked_reason:
            line += f", blocked_reason={sanitize_for_terminal(item.blocked_reason)}"
        if item.wait is not None:
            providers = ",".join(sanitize_for_terminal(p) for p in item.wait.providers) or "(any)"
            line += (
                f", wait: phase={sanitize_for_terminal(item.wait.phase)} "
                f"eligible_at={sanitize_for_terminal(item.wait.eligible_at)} providers={providers}"
            )
        if not item.blocked_reason and item.wait is None:
            line += " (the engine recorded no wait or block reason)"
        lines.append(line)
    return "\n".join(lines)


def _run_why_waiting(
    config_path: str,
    work_item_id: str | None,
    *,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> str:
    try:
        _context, client = _open_project_command_engine(
            config_path, provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
        )
        with client:
            snapshot = client.status()
    except _PROJECT_COMMAND_ERRORS as exc:
        return f"Error: {exc}"
    return _format_why_waiting(snapshot, work_item_id)


NOT_UNDERSTOOD = t("not_understood", "en")


@dataclass
class ReplState:
    """The mutable per-REPL state the dispatcher threads between lines."""

    config_path: str = DEFAULT_CONFIG_PATH
    session: Session | None = None
    store: SessionStore = field(default_factory=SessionStore)


def dispatch_line(
    line: str,
    state: ReplState,
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
    lang: str = "en",
    interrupt: object | None = None,
    event_sink: object | None = None,
) -> bool:
    """The one per-line handler shared by ``run()`` and any other
    front end: handles one raw input line, writes its output, updates
    ``state`` and returns ``False`` only when the REPL must exit."""
    command = line.strip()
    if not command:
        return True
    if not command.startswith("/"):
        match = interpret(command)
        if match.intent is Intent.WHY_WAITING:
            if state.session is not None:
                try:
                    state.config_path = str(project_manifest_path(state.session))
                except SessionProjectError as exc:
                    output_stream.write(f"Error: {exc}\n")
                    return True
            output_stream.write(
                _run_why_waiting(
                    state.config_path, match.work_item_id,
                    provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
                ) + "\n"
            )
            return True
        command = {
            Intent.STATUS: "/status",
            Intent.WORKERS: "/workers",
            Intent.RUN: "/run",
        }.get(match.intent, "")
        if not command:
            output_stream.write(t("not_understood", lang) + "\n")
            return True
    tokens = command.split()
    name, flags = tokens[0], tokens[1:]
    if name == "/exit" and not flags:
        return False
    if name == "/help" and not flags:
        output_stream.write(format_help(lang) + "\n")
        return True
    if name == "/resume" and len(flags) <= 1:
        try:
            session_id = flags[0] if flags else pick_session(state.store, input_stream, output_stream, lang=lang)
            if session_id is not None:
                state.session = resume_selected(state.store, session_id)
                output_stream.write(t("session.resumed", lang, session_id=state.session.session_id) + "\n")
        except (SessionError, OSError, ValueError) as exc:
            output_stream.write(f"Error: {exc}\n")
        return True
    if command == "/new":
        project_path = state.session.project_path if state.session is not None else (
            str(Path(state.config_path).resolve().parent) if Path(state.config_path).is_file() else None
        )
        try:
            state.session = state.store.create(project_path)
            output_stream.write(t("session.created", lang, session_id=state.session.session_id) + "\n")
        except (SessionError, OSError, ValueError) as exc:
            output_stream.write(f"Error: {exc}\n")
        return True
    needs_project = (
        (name in ("/status", "/workers") and flags in ([], ["--probe"]))
        or command in ("/config", "/validate", "/run")
    )
    if needs_project and state.session is not None:
        try:
            state.config_path = str(project_manifest_path(state.session))
        except SessionProjectError as exc:
            output_stream.write(f"Error: {exc}\n")
            return True
    config_path = state.config_path
    if name == "/status" and flags in ([], ["--probe"]):
        output_stream.write(
            _run_status(
                config_path,
                probe=flags == ["--probe"],
                provider_adapters=provider_adapters,
                subprocess_runner=subprocess_runner,
            )
            + "\n"
        )
    elif name == "/workers" and flags in ([], ["--probe"]):
        output_stream.write(
            _run_workers(
                config_path,
                probe=flags == ["--probe"],
                provider_adapters=provider_adapters,
                subprocess_runner=subprocess_runner,
            )
            + "\n"
        )
    elif command == "/config":
        output_stream.write(_run_config(config_path) + "\n")
    elif command == "/validate":
        output_stream.write(
            (_run_session_validate(config_path) if state.session is not None else _run_validate(config_path)) + "\n"
        )
    elif command == "/run":
        if lang != "en":
            output_stream.write(t("run.start", lang) + "\n")
        output_stream.write(
            (_run_session_project if state.session is not None else _run_run)(
                config_path,
                output_stream=output_stream,
                provider_adapters=provider_adapters,
                subprocess_runner=subprocess_runner,
                lang=lang,
                interrupt=interrupt,
                event_sink=event_sink,
            )
            + "\n"
        )
    else:
        output_stream.write(t("unknown_command", lang, command=repr(command)) + "\n")
    return True


def run(
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    prompt: str = "aido> ",
    config_path: str = DEFAULT_CONFIG_PATH,
    session: Session | None = None,
    session_store: SessionStore | None = None,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> None:
    """Read commands from ``input_stream`` until ``/exit`` or EOF.

    A resumed ``session`` supplies its saved project directory to each
    project command. The files are loaded again on every command through
    the shared M1.4 project loader. ``provider_adapters`` and
    ``subprocess_runner`` are test seams for engine construction.
    """
    state = ReplState(
        config_path=config_path, session=session,
        store=session_store if session_store is not None else SessionStore(),
    )
    while True:
        output_stream.write(prompt)
        output_stream.flush()
        try:
            line = input_stream.readline()
        except KeyboardInterrupt:
            output_stream.write("\n")
            return
        if line == "":
            return
        if not dispatch_line(
            line, state, input_stream, output_stream,
            provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
            lang=interactive_lang(),
        ):
            return
