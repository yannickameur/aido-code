"""Tests for aido_code.repl: the minimal REPL loop, `/help`/`/exit` (WI-03)
plus the engine-backed `/status`, `/config`, `/validate`, `/workers`,
`/run` commands (WI-04, WI-05, WI-06). Offline only; see tests/conftest.py
and CONTRIBUTING.md.
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from orchestrator.providers.contracts import UnavailabilityReason

from aido_code.engine_client import EngineClient
from aido_code.repl import DEFAULT_CONFIG_PATH, format_help, run
from tests.conftest import (
    REGISTRY_ENABLED_AND_DISABLED,
    FakeAdapter,
    ScriptedRalphRunner,
    UnavailableAdapter,
    commit_action,
    write_config,
)


def _run(
    commands: str,
    *,
    config_path: str = DEFAULT_CONFIG_PATH,
    provider_adapters: dict[str, Any] | None = None,
    subprocess_runner: object | None = None,
) -> str:
    output = io.StringIO()
    run(
        io.StringIO(commands),
        output,
        config_path=config_path,
        provider_adapters=provider_adapters,
        subprocess_runner=subprocess_runner,
    )
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

    def test_python_dash_m_aido_code_reports_missing_config_cleanly(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "aido_code"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 1
        assert "Error:" in result.stderr
        assert "Traceback" not in result.stderr


class TestStatus:
    def test_uninitialized_project_reports_not_initialized(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path)
        transcript = _run("/status\n/exit\n", config_path=str(config_path))
        assert "NOT_INITIALIZED" in transcript
        assert "Traceback" not in transcript

    def test_initialized_project_reports_real_persisted_status(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path)
        runner = ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )
        client = EngineClient.open(
            str(config_path), provider_adapters={"anthropic": FakeAdapter(available=True)},
            subprocess_runner=runner,
        )
        client.run()

        transcript = _run("/status\n/exit\n", config_path=str(config_path))
        assert "NOT_INITIALIZED" not in transcript
        assert "project: demo (Demo)" in transcript
        assert "wi-1: completed" in transcript
        assert "Traceback" not in transcript

    def test_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/status\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript

    def test_renders_full_worker_list_with_zero_provider_probes(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path, registry=REGISTRY_ENABLED_AND_DISABLED)
        transcript = _run("/status\n/exit\n", config_path=str(config_path))
        assert "workers:" in transcript
        assert "alice" in transcript
        assert "enabled" in transcript
        assert "bob" in transcript
        assert "disabled" in transcript
        assert "probe=" not in transcript
        assert "Traceback" not in transcript

    def test_no_provider_adapter_is_ever_instantiated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import orchestrator.engine as engine_module

        def _fail_resolve(providers: object) -> None:
            raise AssertionError("provider adapters must never be resolved by plain /status")

        monkeypatch.setattr(engine_module, "resolve_provider_adapters", _fail_resolve)

        config_path = write_config(tmp_path, registry=REGISTRY_ENABLED_AND_DISABLED)
        transcript = _run("/status\n/exit\n", config_path=str(config_path))
        assert "alice" in transcript
        assert "Traceback" not in transcript

    def test_probe_renders_same_status_plus_real_worker_states(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path, registry=REGISTRY_ENABLED_AND_DISABLED)
        adapter = FakeAdapter(available=True)
        transcript = _run(
            "/status --probe\n/exit\n",
            config_path=str(config_path),
            provider_adapters={"anthropic": adapter},
        )
        assert "NOT_INITIALIZED" in transcript
        assert "alice" in transcript
        assert "probe=available" in transcript
        assert "bob" in transcript
        assert "probe=disabled" in transcript
        assert adapter.calls == 1
        assert "Traceback" not in transcript

    def test_probe_reports_quota_exhaustion_honestly(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path)
        adapter = UnavailableAdapter(UnavailabilityReason.QUOTA_EXHAUSTED)
        transcript = _run(
            "/status --probe\n/exit\n",
            config_path=str(config_path),
            provider_adapters={"anthropic": adapter},
        )
        assert "alice" in transcript
        assert "bob" in transcript
        assert transcript.count("probe=quota") == 2

    def test_probe_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/status --probe\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript


class TestConfig:
    def test_config_renders_project_snapshot_never_a_raw_file_dump(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path)
        transcript = _run("/config\n/exit\n", config_path=str(config_path))
        assert "project: demo (Demo)" in transcript
        assert "enabled_workers: 2" in transcript
        assert "providers: anthropic" in transcript
        assert "schema_version" not in transcript
        assert "Traceback" not in transcript

    def test_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/config\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript


class TestValidate:
    def test_valid_configuration_reports_success_with_no_side_effect(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path)
        transcript = _run("/validate\n/exit\n", config_path=str(config_path))
        assert "Configuration is valid." in transcript
        assert not (tmp_path / "state").exists()

    def test_invalid_worker_registry_reports_failure_not_a_traceback(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path, registry="workers:\n  - worker_id: alice\n")
        transcript = _run("/validate\n/exit\n", config_path=str(config_path))
        assert "Validation failed" in transcript
        assert "Traceback" not in transcript

    def test_missing_aido_yaml_reports_failure_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/validate\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Validation failed" in transcript


class TestRun:
    def test_run_calls_the_real_engine_and_renders_the_run_result(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path)
        runner = ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )
        transcript = _run(
            "/run\n/exit\n",
            config_path=str(config_path),
            provider_adapters={"anthropic": FakeAdapter(available=True)},
            subprocess_runner=runner,
        )
        assert "Traceback" not in transcript
        assert "cycles_run: 1" in transcript
        assert "all_terminal: True" in transcript
        assert "wi-1: completed" in transcript
        assert "work_item.completed: work_item=wi-1" in transcript
        assert len(runner.calls) == 2

    def test_rerunning_an_already_completed_project_does_nothing_and_never_re_executes(
        self, tmp_path: Path
    ) -> None:
        config_path = write_config(tmp_path)
        first_runner = ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )
        client = EngineClient.open(
            str(config_path),
            provider_adapters={"anthropic": FakeAdapter(available=True)},
            subprocess_runner=first_runner,
        )
        first_result = client.run()
        assert first_result.all_terminal is True

        async def never_called_runner(*args: object, **kwargs: object) -> tuple[int, bytes, bytes]:
            raise AssertionError("completed projects must not invoke the subprocess runner")

        transcript = _run(
            "/run\n/exit\n",
            config_path=str(config_path),
            provider_adapters={"anthropic": FakeAdapter(available=True)},
            subprocess_runner=never_called_runner,
        )
        assert "Traceback" not in transcript
        assert "all_terminal: True" in transcript
        assert "wi-1: completed" in transcript

    def test_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/run\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript


class TestWorkers:
    def test_lists_enabled_and_disabled_workers(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path, registry=REGISTRY_ENABLED_AND_DISABLED)
        transcript = _run("/workers\n/exit\n", config_path=str(config_path))
        assert "alice" in transcript
        assert "enabled" in transcript
        assert "bob" in transcript
        assert "disabled" in transcript
        assert "Traceback" not in transcript

    def test_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/workers\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript

    def test_no_provider_adapter_is_ever_instantiated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import orchestrator.engine as engine_module

        def _fail_resolve(providers: object) -> None:
            raise AssertionError("provider adapters must never be resolved by /workers")

        monkeypatch.setattr(engine_module, "resolve_provider_adapters", _fail_resolve)

        config_path = write_config(tmp_path, registry=REGISTRY_ENABLED_AND_DISABLED)
        transcript = _run("/workers\n/exit\n", config_path=str(config_path))
        assert "alice" in transcript
        assert "Traceback" not in transcript

    def test_probe_renders_the_same_worker_states_as_status_probe(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path, registry=REGISTRY_ENABLED_AND_DISABLED)
        adapter = FakeAdapter(available=True)
        transcript = _run(
            "/workers --probe\n/exit\n",
            config_path=str(config_path),
            provider_adapters={"anthropic": adapter},
        )
        assert "alice" in transcript
        assert "probe=available" in transcript
        assert "bob" in transcript
        assert "probe=disabled" in transcript
        assert adapter.calls == 1
        assert "project:" not in transcript
        assert "Traceback" not in transcript

    def test_probe_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/workers --probe\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript
