"""Tests for aido_code.repl: the minimal REPL loop (WI-03 scope only —
/help, /exit, and a clear message for unrecognized commands). Commands
backed by the engine client are covered by later WorkItems.
"""

from __future__ import annotations

import io
import subprocess
import sys

from aido_code.repl import format_help, run


def _run(commands: str) -> str:
    output = io.StringIO()
    run(io.StringIO(commands), output)
    return output.getvalue()


class TestHelp:
    def test_help_lists_available_commands(self) -> None:
        transcript = _run("/help\n/exit\n")
        assert "/help" in transcript
        assert "/exit" in transcript
        assert format_help() in transcript


class TestExit:
    def test_exit_cleanly_terminates_the_loop(self) -> None:
        transcript = _run("/exit\n")
        assert "Unknown command" not in transcript

    def test_eof_terminates_the_loop_without_error(self) -> None:
        # No trailing /exit: readline() hits EOF immediately.
        transcript = _run("")
        assert "Unknown command" not in transcript


class TestUnrecognizedCommand:
    def test_unrecognized_command_prints_clear_message_not_a_traceback(self) -> None:
        transcript = _run("/bogus\n/exit\n")
        assert "Unknown command: '/bogus'" in transcript
        assert "Traceback" not in transcript

    def test_blank_lines_are_ignored(self) -> None:
        transcript = _run("\n\n/exit\n")
        assert "Unknown command" not in transcript


class TestEntryPoints:
    def test_python_dash_m_aido_code_starts_repl_and_accepts_commands(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "aido_code"],
            input="/help\n/bogus\n/exit\n",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "/help" in result.stdout
        assert "Unknown command: '/bogus'" in result.stdout
        assert "Traceback" not in result.stderr
