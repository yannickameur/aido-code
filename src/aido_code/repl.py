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
"""

from __future__ import annotations

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


def format_help() -> str:
    lines = ["Available commands:"]
    lines.extend(f"  {name} - {description}" for name, description in COMMANDS.items())
    return "\n".join(lines)


def format_config(snapshot: ProjectSnapshot) -> str:
    providers = ", ".join(snapshot.providers) if snapshot.providers else "(none)"
    lines = [
        f"project: {snapshot.project_id} ({snapshot.name})",
        f"workspace: {snapshot.workspace}",
        f"state_dir: {snapshot.state_dir}",
        f"mvp: {snapshot.mvp_id}",
        f"work_items: {snapshot.work_item_count}",
        f"qa_commands: {snapshot.qa_command_count}",
        f"enabled_workers: {snapshot.enabled_worker_count}",
        f"providers: {providers}",
        f"permission_mode: {snapshot.permission_mode.upper()}",
        f"base_branch: {snapshot.base_branch}",
    ]
    return "\n".join(lines)


def format_status(snapshot: ProjectStatusSnapshot) -> str:
    if not snapshot.initialized:
        return "NOT_INITIALIZED\nRun /run to initialize and start this project."

    lines = [f"project: {snapshot.project_id} ({snapshot.project_name})"]
    if snapshot.mvp is None:
        lines.append("mvp: (not configured)")
    elif snapshot.mvp.status is None:
        lines.append(f"mvp: {snapshot.mvp.mvp_id} (not yet created)")
    else:
        lines.append(f"mvp: {snapshot.mvp.mvp_id} status={snapshot.mvp.status}")

    if snapshot.work_items:
        lines.append("")
        lines.append("work items:")
        for work_item in snapshot.work_items:
            line = f"  {work_item.work_item_id}: {work_item.status}"
            if work_item.blocked_reason:
                line += f" (blocked_reason={work_item.blocked_reason})"
            lines.append(line)

            if work_item.last_execution is not None:
                execution = work_item.last_execution
                lines.append(
                    f"      last execution: worker={execution.worker_id} "
                    f"provider={execution.provider} status={execution.status}"
                )
            if work_item.wait is not None:
                wait = work_item.wait
                lines.append(
                    f"      wait: phase={wait.phase} eligible_at={wait.eligible_at} "
                    f"providers={','.join(wait.providers) or '(any)'}"
                )
    return "\n".join(lines)


def format_run(result: RunResult) -> str:
    lines = [
        f"cycles_run: {result.cycles_run}",
        f"all_terminal: {result.all_terminal}",
        f"reached_max_cycles: {result.reached_max_cycles}",
    ]

    if result.work_items:
        lines.append("")
        lines.append("work items:")
        for work_item in result.work_items:
            line = f"  {work_item.work_item_id}: {work_item.status}"
            if work_item.blocked_reason:
                line += f" (blocked_reason={work_item.blocked_reason})"
            lines.append(line)

    if result.events:
        lines.append("")
        lines.append("events:")
        for event in result.events:
            lines.append(f"  {event.kind}: work_item={event.work_item_id}")

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
        return state.reason
    if state.reason == "quota_exhausted":
        return "quota"
    if state.reason in ("auth_error", "provider_error"):
        return f"unavailable ({state.reason})"
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
            f"  {worker.worker_id} ({worker.display_name}): {state} "
            f"provider={worker.provider} backend={worker.backend} priority={worker.priority}"
        )
        if worker.model:
            line += f" model={worker.model}"
        if provider_states is not None:
            line += f" probe={_worker_probe_state(worker, provider_states)}"
        lines.append(line)
        lines.append(f"      capabilities: {', '.join(worker.capabilities) or '(none)'}")
    return "\n".join(lines)


def _format_workers_section(
    workers: tuple[WorkerSnapshot, ...], providers: tuple[ProviderSnapshot, ...] | None
) -> str:
    """The one probe/rendering code path `/status --probe` and
    `/workers --probe` both call: `providers=None` renders the static
    view, otherwise it maps `probe_workers()`'s own ``ProviderSnapshot``
    tuple onto the workers that use each provider."""
    if providers is None:
        return format_workers(workers)
    provider_states = {snapshot.provider: snapshot for snapshot in providers}
    return format_workers(workers, provider_states)


def _run_status(
    config_path: str,
    *,
    probe: bool = False,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> str:
    try:
        with EngineClient.open(
            config_path, provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
        ) as client:
            snapshot = client.status()
            workers = client.workers()
            providers = client.probe_workers() if probe else None
    except EngineError as exc:
        return f"Error: {exc}"
    return "\n\n".join(
        [format_status(snapshot), "workers:", _format_workers_section(workers, providers)]
    )


def _run_config(config_path: str) -> str:
    try:
        with EngineClient.open(config_path) as client:
            snapshot = client.validate()
    except EngineError as exc:
        return f"Error: {exc}"
    return format_config(snapshot)


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


def _run_workers(
    config_path: str,
    *,
    probe: bool = False,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> str:
    try:
        with EngineClient.open(
            config_path, provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
        ) as client:
            snapshots = client.workers()
            providers = client.probe_workers() if probe else None
    except EngineError as exc:
        return f"Error: {exc}"
    return _format_workers_section(snapshots, providers)


def run(
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    prompt: str = "aido> ",
    config_path: str = DEFAULT_CONFIG_PATH,
    provider_adapters: dict[str, object] | None = None,
    subprocess_runner: object | None = None,
) -> None:
    """Read commands from ``input_stream`` until ``/exit`` or EOF.

    ``provider_adapters``/``subprocess_runner`` are forwarded to every
    ``EngineClient.open()`` call this loop makes (``/run``, and
    ``/status``/``/workers`` when ``--probe`` triggers a real
    ``probe_workers()``); same test-only seams as ``EngineClient.open()``
    itself (see ``engine_client.py``), production callers (``__main__.py``)
    never set them.
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
            output_stream.write(_run_validate(config_path) + "\n")
            continue
        if command == "/run":
            output_stream.write(
                _run_run(
                    config_path,
                    provider_adapters=provider_adapters,
                    subprocess_runner=subprocess_runner,
                )
                + "\n"
            )
            continue

        output_stream.write(f"Unknown command: {command!r}. Type /help for a list of commands.\n")
