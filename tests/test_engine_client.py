"""Tests for aido_code.engine_client.EngineClient: the thin wrapper this
package uses to talk to orchestrator.engine.OrchestratorEngine (see
docs/ENGINE_CONTRACT.md).

Offline only, via OrchestratorEngine.open()'s own provider_adapters/
subprocess_runner injection seams: never a real Claude/Codex/Vibe/
DeepSeek/Kimi provider, never a real Ralph subprocess (see
CONTRIBUTING.md).
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

import pytest
from orchestrator.providers.adapter import ProviderAdapter
from orchestrator.providers.contracts import ProviderAvailability, ProviderState

from aido_code.engine_client import (
    EngineClient,
    EngineConfigError,
    ProjectSnapshot,
    ProjectStatusSnapshot,
)

UTC_T0 = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)


class _NeverCalledAdapter(ProviderAdapter):
    async def probe(self) -> ProviderState:
        raise AssertionError("provider probe must never be called by this wrapper call")


class _FakeAdapter(ProviderAdapter):
    def __init__(self, *, available: bool = True) -> None:
        self._available = available

    async def probe(self) -> ProviderState:
        return ProviderState(
            provider="anthropic",
            availability=ProviderAvailability(available=self._available, observed_at=UTC_T0, reason=None),
            observed_at=UTC_T0,
        )


class _ScriptedRalphRunner:
    """Genuinely mutates the workspace and writes real Ralph event files,
    never a real Ralph/Claude/Codex/Vibe subprocess; same shape as
    ai-dev-orchestrator's own test fixtures."""

    def __init__(self, steps: list[dict]) -> None:
        self._steps = list(steps)
        self.calls: list[tuple] = []

    async def __call__(self, args: list[str], cwd: Path, timeout: float) -> tuple[int, bytes, bytes]:
        self.calls.append((args, cwd, timeout))
        assert self._steps, "fake Ralph runner called more times than scripted"
        step = self._steps.pop(0)
        mutate = step.get("mutate")
        if mutate is not None:
            mutate(Path(cwd))

        ralph_dir = Path(cwd) / ".ralph"
        ralph_dir.mkdir(parents=True, exist_ok=True)
        (ralph_dir / "current-loop-id").write_text(step.get("loop_id", "engine-client-test-loop"))
        events_filename = f"events-{len(self.calls)}.jsonl"
        (ralph_dir / "current-events").write_text(f".ralph/{events_filename}")
        line = json.dumps({"topic": step["topic"], "ts": UTC_T0.isoformat(), "payload": step.get("payload")})
        (ralph_dir / events_filename).write_text(line + "\n")
        return step.get("exit_code", 0), step.get("stdout", b""), step.get("stderr", b"")


def _commit_action(repo_cwd_relative_file: str, content: str, message: str):
    def _mutate(cwd: Path) -> None:
        (cwd / repo_cwd_relative_file).write_text(content)
        subprocess.run(["git", "add", "-A"], cwd=str(cwd), check=True)
        subprocess.run(
            ["git", "-c", "user.email=e2e@example.invalid", "-c", "user.name=E2E", "commit", "-q", "-m", message],
            cwd=str(cwd), check=True,
        )
    return _mutate


def _init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(path), check=True)
    subprocess.run(
        ["git", "-c", "user.email=e2e@example.invalid", "-c", "user.name=E2E", "add", "-A"],
        cwd=str(path), check=True,
    )
    subprocess.run(
        ["git", "-c", "user.email=e2e@example.invalid", "-c", "user.name=E2E", "commit", "-q", "-m", "init"],
        cwd=str(path), check=True,
    )
    return path


REGISTRY_TWO_WORKERS = dedent(
    """
    workers:
      - worker_id: alice
        display_name: Alice
        provider: anthropic
        backend: claude_code
        capabilities: [development]
        profiles:
          standard: {quality_tier: STANDARD, model: sonnet}
      - worker_id: bob
        display_name: Bob
        provider: anthropic
        backend: claude_code
        capabilities: [development]
        profiles:
          standard: {quality_tier: STANDARD, model: sonnet}
    """
)


def _write_config(tmp_path: Path, *, registry: str = REGISTRY_TWO_WORKERS) -> Path:
    _init_git_repo(tmp_path / "proj")
    (tmp_path / "workers.yaml").write_text(registry)
    config_path = tmp_path / "aido.yaml"
    config_path.write_text(
        dedent(
            f"""
            schema_version: 1
            project:
              id: demo
              name: Demo
              workspace: proj
              state_dir: state
            workers:
              registry: workers.yaml
            execution:
              permission_mode: standard
            git:
              base_branch: main
            mvp:
              id: mvp-1
              objective: Ship it
            work_items:
              - id: wi-1
                title: Do the thing
                required_capabilities: [development]
            qa:
              - id: qa-1
                kind: unit_test
                argv: ["{sys.executable}", "-c", "pass"]
            """
        )
    )
    return config_path


class TestOpen:
    def test_open_returns_engine_client(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path)
        client = EngineClient.open(str(config_path))
        assert isinstance(client, EngineClient)

    def test_open_raises_engine_config_error_for_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(EngineConfigError):
            EngineClient.open(str(tmp_path / "does-not-exist.yaml"))

    def test_open_raises_engine_config_error_for_bad_worker_registry(self, tmp_path: Path) -> None:
        config_path = _write_config(tmp_path, registry="workers:\n  - worker_id: alice\n")
        with pytest.raises(EngineConfigError):
            EngineClient.open(str(config_path))


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
