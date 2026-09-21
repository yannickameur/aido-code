"""Minimal REPL loop for AIDO Code.

WI-04 scope: `/help`, `/exit`, `/status`, `/config`, `/validate`, and a
clear message (never a traceback) for anything unrecognized or for any
engine/config error. `/workers` and `/run` are later WorkItems; see
docs/CLI_SPEC.md and aido.yaml's work_items.
"""

from __future__ import annotations

from typing import TextIO

from aido_code.engine_client import (
    EngineClient,
    EngineError,
    ProjectSnapshot,
    ProjectStatusSnapshot,
)

COMMANDS: dict[str, str] = {
    "/help": "List available commands.",
    "/status": "Show the project's real, persisted status.",
    "/config": "Show the loaded aido.yaml's validated configuration.",
    "/validate": "Validate aido.yaml and its worker registry.",
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


def _run_status(config_path: str) -> str:
    try:
        with EngineClient.open(config_path) as client:
            snapshot = client.status()
    except EngineError as exc:
        return f"Error: {exc}"
    return format_status(snapshot)


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


def run(
    input_stream: TextIO,
    output_stream: TextIO,
    *,
    prompt: str = "aido> ",
    config_path: str = DEFAULT_CONFIG_PATH,
) -> None:
    """Read commands from ``input_stream`` until ``/exit`` or EOF."""
    while True:
        output_stream.write(prompt)
        output_stream.flush()
        line = input_stream.readline()
        if line == "":
            return

        command = line.strip()
        if not command:
            continue
        if command == "/exit":
            return
        if command == "/help":
            output_stream.write(format_help() + "\n")
            continue
        if command == "/status":
            output_stream.write(_run_status(config_path) + "\n")
            continue
        if command == "/config":
            output_stream.write(_run_config(config_path) + "\n")
            continue
        if command == "/validate":
            output_stream.write(_run_validate(config_path) + "\n")
            continue

        output_stream.write(f"Unknown command: {command!r}. Type /help for a list of commands.\n")
