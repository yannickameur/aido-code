"""Shared offline test fixtures: real git repos, real Ralph event files
written by a scripted fake subprocess runner, never a real provider or
Ralph invocation (see CONTRIBUTING.md).
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent

from orchestrator.providers.adapter import ProviderAdapter
from orchestrator.providers.contracts import ProviderAvailability, ProviderState, UnavailabilityReason

from aido_code.engine_client import EngineClient

UTC_T0 = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)

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


REGISTRY_ENABLED_AND_DISABLED = dedent(
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
        enabled: false
        profiles:
          standard: {quality_tier: STANDARD, model: sonnet}
    """
)


class NeverCalledAdapter(ProviderAdapter):
    async def probe(self) -> ProviderState:
        raise AssertionError("provider probe must never be called by this wrapper call")


class FakeAdapter(ProviderAdapter):
    def __init__(self, *, available: bool = True) -> None:
        self._available = available
        self.calls = 0

    async def probe(self) -> ProviderState:
        self.calls += 1
        return ProviderState(
            provider="anthropic",
            availability=ProviderAvailability(available=self._available, observed_at=UTC_T0, reason=None),
            observed_at=UTC_T0,
        )


class UnavailableAdapter(ProviderAdapter):
    """Reports a specific, real ``UnavailabilityReason`` (e.g. quota
    exhaustion), never a fabricated state."""

    def __init__(self, reason: UnavailabilityReason) -> None:
        self._reason = reason
        self.calls = 0

    async def probe(self) -> ProviderState:
        self.calls += 1
        return ProviderState(
            provider="anthropic",
            availability=ProviderAvailability(available=False, observed_at=UTC_T0, reason=self._reason),
            observed_at=UTC_T0,
        )


class ScriptedRalphRunner:
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


def commit_action(repo_cwd_relative_file: str, content: str, message: str):
    def _mutate(cwd: Path) -> None:
        (cwd / repo_cwd_relative_file).write_text(content)
        subprocess.run(["git", "add", "-A"], cwd=str(cwd), check=True)
        subprocess.run(
            ["git", "-c", "user.email=e2e@example.invalid", "-c", "user.name=E2E", "commit", "-q", "-m", message],
            cwd=str(cwd), check=True,
        )
    return _mutate


def init_git_repo(path: Path) -> Path:
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


def write_config(tmp_path: Path, *, registry: str = REGISTRY_TWO_WORKERS) -> Path:
    init_git_repo(tmp_path / "proj")
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


def open_offline(config_path: Path) -> EngineClient:
    return EngineClient.open(str(config_path), provider_adapters={"anthropic": NeverCalledAdapter()})
