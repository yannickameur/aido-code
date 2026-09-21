"""WI-07: one offline, end-to-end test driving a fake project through the
full REPL lifecycle in a single session: /status (NOT_INITIALIZED) ->
/validate -> /run (drives a fake WorkItem to completed via a scripted
fake Ralph subprocess) -> /status (reflects completion) -> /exit.

Offline only: no real provider or Ralph subprocess anywhere in this test,
via the same tests/conftest.py fixtures as test_repl.py and
test_engine_client.py (see CONTRIBUTING.md).
"""

from __future__ import annotations

import io
from pathlib import Path

from aido_code.repl import run
from tests.conftest import FakeAdapter, ScriptedRalphRunner, commit_action, write_config


class TestFullProjectLifecycle:
    def test_status_validate_run_status_exit(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path)
        runner = ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )

        output = io.StringIO()
        run(
            io.StringIO("/status\n/validate\n/run\n/status\n/exit\n"),
            output,
            config_path=str(config_path),
            provider_adapters={"anthropic": FakeAdapter(available=True)},
            subprocess_runner=runner,
        )
        transcript = output.getvalue()

        assert "Traceback" not in transcript
        assert "Unknown command" not in transcript

        idx_not_initialized = transcript.index("NOT_INITIALIZED")
        idx_valid = transcript.index("Configuration is valid.")
        idx_run_result = transcript.index("cycles_run: 1")
        idx_final_status = transcript.rindex("project: demo (Demo)")

        # The lifecycle happened in order, in one REPL session.
        assert idx_not_initialized < idx_valid < idx_run_result < idx_final_status

        # /run drove the fake WorkItem to completed via the scripted Ralph
        # subprocess, exactly twice (DEV A execution + completion event).
        assert "all_terminal: True" in transcript
        assert "work_item.completed: work_item=wi-1" in transcript
        assert len(runner.calls) == 2

        # The final /status reflects that same completion, from real
        # persisted state, not a re-run.
        final_status = transcript[idx_final_status:]
        assert "wi-1: completed" in final_status
        assert "NOT_INITIALIZED" not in final_status
