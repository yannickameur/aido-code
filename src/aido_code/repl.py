"""Minimal REPL loop for AIDO Code.

WI-03 scope only: `/help`, `/exit`, and a clear message (never a
traceback) for anything unrecognized. Commands backed by the engine
client (`/status`, `/workers`, `/config`, `/validate`, `/run`) are later
WorkItems; see docs/CLI_SPEC.md and aido.yaml's work_items.
"""

from __future__ import annotations

from typing import TextIO

COMMANDS: dict[str, str] = {
    "/help": "List available commands.",
    "/exit": "Exit the REPL.",
}


def format_help() -> str:
    lines = ["Available commands:"]
    lines.extend(f"  {name} - {description}" for name, description in COMMANDS.items())
    return "\n".join(lines)


def run(input_stream: TextIO, output_stream: TextIO, *, prompt: str = "aido> ") -> None:
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

        output_stream.write(f"Unknown command: {command!r}. Type /help for a list of commands.\n")
