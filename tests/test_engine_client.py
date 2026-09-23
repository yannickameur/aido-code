"""Tests for aido_code.engine_client.EngineClient: the thin wrapper this
package uses to talk to orchestrator.engine.OrchestratorEngine (see
docs/ENGINE_CONTRACT.md).

Offline only, via OrchestratorEngine.open()'s own provider_adapters/
subprocess_runner injection seams: never a real Claude/Codex/Vibe/
DeepSeek/Kimi provider, never a real Ralph subprocess (see
CONTRIBUTING.md).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from orchestrator.providers.contracts import QuotaWindow, ResetCredit, ResetCreditStatus

from aido_code.engine_client import (
    EngineClient,
    EngineConfigError,
    ProjectSnapshot,
    ProjectStatusSnapshot,
    ProviderSnapshot,
)
from tests.conftest import (
    UTC_T0,
    FakeAdapter as _FakeAdapter,
    NeverCalledAdapter as _NeverCalledAdapter,
    ScriptedRalphRunner as _ScriptedRalphRunner,
    commit_action as _commit_action,
    open_offline as _open_offline,
    write_config as _write_config,
)


class TestOpen:
    def test_open_returns_engine_client(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        client = _open_offline(config_path)
        assert isinstance(client, EngineClient)

    def test_open_raises_engine_config_error_for_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(EngineConfigError):
            EngineClient.open(str(tmp_path / "does-not-exist.yaml"))

    def test_open_raises_engine_config_error_for_bad_worker_registry(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path, registry="workers:\n  - worker_id: alice\n")
        with pytest.raises(EngineConfigError):
            _open_offline(config_path)


class TestValidate:
    def test_validate_returns_project_snapshot_without_touching_a_provider(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        client = EngineClient.open(str(config_path), provider_adapters={"anthropic": _NeverCalledAdapter()})
        snapshot = client.validate()
        assert isinstance(snapshot, ProjectSnapshot)
        assert snapshot.project_id == "demo"
        assert snapshot.mvp_id == "mvp-1"
        assert snapshot.enabled_worker_count == 2
        assert snapshot.providers == ("anthropic",)


class TestWorkers:
    def test_workers_lists_configured_workers_without_touching_a_provider(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        client = EngineClient.open(str(config_path), provider_adapters={"anthropic": _NeverCalledAdapter()})
        workers = client.workers()
        assert {w.worker_id for w in workers} == {"alice", "bob"}
        assert workers[0].provider == "anthropic"


class TestProbeWorkers:
    def test_probe_workers_returns_provider_snapshots_via_injected_adapter(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        client = EngineClient.open(str(config_path), provider_adapters={"anthropic": _FakeAdapter(available=True)})
        snapshots = client.probe_workers()
        assert len(snapshots) == 1
        assert isinstance(snapshots[0], ProviderSnapshot)
        assert snapshots[0].provider == "anthropic"
        assert snapshots[0].available is True

    def test_probe_workers_surfaces_quota_windows_and_reset_credits_from_injected_adapter(
        self, tmp_path: Path
    ) -> None:
        config_path = _write_config(tmp_path)
        reset_at = datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc)
        adapter = _FakeAdapter(
            available=True,
            quota_windows=(
                QuotaWindow(
                    window_type="five_hour", source="claude_code", observed_at=UTC_T0,
                    utilization=0.25, reset_at=reset_at,
                ),
                QuotaWindow(
                    window_type="seven_day", source="claude_code", observed_at=UTC_T0,
                    utilization=None, reset_at=None,
                ),
            ),
            reset_credits=(
                ResetCredit(title="weekly bonus", status=ResetCreditStatus.AVAILABLE, available_count=2),
                ResetCredit(title="mystery credit", status=ResetCreditStatus.UNKNOWN, available_count=None),
            ),
        )
        client = EngineClient.open(str(config_path), provider_adapters={"anthropic": adapter})
        snapshot = client.probe_workers()[0]
        known, unknown = snapshot.quota_windows
        assert known.window_type == "five_hour"
        assert known.utilization == 0.25
        assert known.remaining == 0.75
        assert known.reset_at == reset_at.isoformat()
        assert unknown.window_type == "seven_day"
        assert unknown.utilization is None
        assert unknown.remaining is None
        assert unknown.reset_at is None
        credited, uncredited = snapshot.reset_credits
        assert credited.title == "weekly bonus"
        assert credited.available_count == 2
        assert uncredited.available_count is None


class TestStatus:
    def test_uninitialized_project_reports_not_initialized_without_touching_a_provider(
        self, tmp_path: Path,
    ) -> None:
        config_path = _write_config(tmp_path)
        client = EngineClient.open(str(config_path), provider_adapters={"anthropic": _NeverCalledAdapter()})
        snapshot = client.status()
        assert isinstance(snapshot, ProjectStatusSnapshot)
        assert snapshot.initialized is False
        assert snapshot.work_items == ()


class TestRun:
    def test_run_drives_workitem_to_completed_via_injected_seams(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        runner = _ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": _commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )
        client = EngineClient.open(
            str(config_path), provider_adapters={"anthropic": _FakeAdapter(available=True)},
            subprocess_runner=runner,
        )
        result = client.run()
        assert result.all_terminal is True
        assert len(result.work_items) == 1
        assert result.work_items[0].status == "completed"
        assert len(runner.calls) == 2

    def test_run_again_resumes_without_rerunning_a_completed_workitem(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        runner = _ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": _commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )
        client = EngineClient.open(
            str(config_path), provider_adapters={"anthropic": _FakeAdapter(available=True)},
            subprocess_runner=runner,
        )
        client.run()

        second_runner = _ScriptedRalphRunner([])
        second_client = EngineClient.open(
            str(config_path), provider_adapters={"anthropic": _FakeAdapter(available=True)},
            subprocess_runner=second_runner,
        )
        result = second_client.run()
        assert result.all_terminal is True
        assert len(second_runner.calls) == 0
