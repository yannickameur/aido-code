"""Minimal REPL loop for AIDO Code.

WI-06 scope: `/help`, `/exit`, `/status`, `/config`, `/validate`,
`/workers`, `/run`, and a clear message (never a traceback) for anything
unrecognized or for any engine/config error. `/run` is also how a
project resumes: there is no separate resume command in this MVP; see
docs/CLI_SPEC.md and docs/ENGINE_CONTRACT.md ("`.run()` is also resume").

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
from aido_code.project_command import ProjectCommandContext, load_project_command_context
from aido_code.project_manifest import ProjectManifestError
from aido_code.project_resources import ProjectResourcesError
from aido_code.roadmap import CurrentMilestone, RoadmapError
from aido_code.session import Session, SessionProjectError, project_manifest_path
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


def format_help() -> str:
    lines = ["Available commands:"]
    lines.extend(f"  {name} - {description}" for name, description in COMMANDS.items())
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


def format_run(result: RunResult) -> str:
    lines = [
        f"cycles_run: {sanitize_for_terminal(result.cycles_run)}",
        f"all_terminal: {sanitize_for_terminal(result.all_terminal)}",
        f"reached_max_cycles: {sanitize_for_terminal(result.reached_max_cycles)}",
    ]

    if result.work_items:
        lines.append("")
        lines.append("work items:")
        for work_item in result.work_items:
            line = (
                f"  {sanitize_for_terminal(work_item.work_item_id)}: "
                f"{sanitize_for_terminal(work_item.status)}"
            )
            if work_item.blocked_reason:
                line += f" (blocked_reason={sanitize_for_terminal(work_item.blocked_reason)})"
            lines.append(line)

    if result.events:
        lines.append("")
        lines.append("events:")
        for event in result.events:
            lines.append(
                f"  {sanitize_for_terminal(event.kind)}: "
                f"work_item={sanitize_for_terminal(event.work_item_id)}"
            )

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


def _run_status(
    config_path: str,
    *,
    probe: bool = False,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> str:
    try:
        context, client = _open_project_command_engine(
            config_path, provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
        )
        with client:
            snapshot = client.status()
            workers = client.workers()
            providers = client.probe_workers() if probe else None
    except _PROJECT_COMMAND_ERRORS as exc:
        return f"Error: {exc}"
    return "\n\n".join(
        [
            format_status(context.roadmap.milestone, snapshot),
            "workers:",
            _format_workers_section(workers, providers),
        ]
    )


def _run_config(config_path: str) -> str:
    try:
        context, client = _open_project_command_engine(config_path)
        with client:
            snapshot = client.validate()
    except _PROJECT_COMMAND_ERRORS as exc:
        return f"Error: {exc}"
    return format_config(context, snapshot)


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
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> str:
    try:
        with EngineClient.open(
            config_path, provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
        ) as client:
            result = client.run()
    except EngineError as exc:
        return f"Error: {exc}"
    return format_run(result)


def _run_session_validate(config_path: str) -> str:
    try:
        load_project_command_context(config_path)
    except _PROJECT_COMMAND_ERRORS as exc:
        return f"Validation failed: {exc}"
    return "Configuration is valid."


def _run_session_project(
    config_path: str,
    *,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
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
            return format_run(client.run())
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


def run(
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    prompt: str = "aido> ",
    config_path: str = DEFAULT_CONFIG_PATH,
    session: Session | None = None,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> None:
    """Read commands from ``input_stream`` until ``/exit`` or EOF.

    A resumed ``session`` supplies its saved project directory to each
    project command. The files are loaded again on every command through
    the shared M1.4 project loader. ``provider_adapters`` and
    ``subprocess_runner`` are test seams for engine construction.
    """
    while True:
        output_stream.write(prompt)
        output_stream.flush()
        line = input_stream.readline()
        if line == "":
            return

        command = line.strip()
        if not command:
            continue
        tokens = command.split()
        name, flags = tokens[0], tokens[1:]
        if name == "/exit" and not flags:
            return
        if name == "/help" and not flags:
            output_stream.write(format_help() + "\n")
            continue
        needs_project = (
            (name in ("/status", "/workers") and flags in ([], ["--probe"]))
            or command in ("/config", "/validate", "/run")
        )
        if needs_project and session is not None:
            try:
                config_path = str(project_manifest_path(session))
            except SessionProjectError as exc:
                output_stream.write(f"Error: {exc}\n")
                continue
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
            continue
        if name == "/workers" and flags in ([], ["--probe"]):
            output_stream.write(
                _run_workers(
                    config_path,
                    probe=flags == ["--probe"],
                    provider_adapters=provider_adapters,
                    subprocess_runner=subprocess_runner,
                )
                + "\n"
            )
            continue
        if command == "/config":
            output_stream.write(_run_config(config_path) + "\n")
            continue
        if command == "/validate":
            output_stream.write(
                (_run_session_validate(config_path) if session is not None else _run_validate(config_path)) + "\n"
            )
            continue
        if command == "/run":
            output_stream.write(
                (_run_session_project if session is not None else _run_run)(
                    config_path,
                    provider_adapters=provider_adapters,
                    subprocess_runner=subprocess_runner,
                )
                + "\n"
            )
            continue

        output_stream.write(f"Unknown command: {command!r}. Type /help for a list of commands.\n")
