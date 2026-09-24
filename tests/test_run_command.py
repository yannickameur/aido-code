"""WI-M1.4-07B: ``aido-code run`` integration + ``Status: APPROVED`` gate
(``aido_code.__main__._project_command("run")``). See ``docs/
PROJECT_CONTRACT.md`` §7 and ``ROADMAP.md`` WI-M1.4-07.

``run`` shares the exact ``aido_code.project_command.
load_project_command_context`` path WI-M1.4-07A extracted (manifest ->
ROADMAP.md -> resources -> AIDO WorkerRegistry) — this file proves the
command built on top of it: a ``DRAFT`` milestone is refused before any
engine/provider construction; an ``APPROVED`` milestone reaches a real
``OrchestratorEngine.run()`` WorkItem Flow cycle, injected via the same
``worker_registry=`` seam WI-M1.4-05 established.

Offline only, exactly this repository's own established convention
(``tests/conftest.py``'s ``FakeAdapter``/``NeverCalledAdapter``/
``ScriptedRalphRunner``, per ``CONTRIBUTING.md``): never a real Claude/
Codex/Vibe provider, never a real Ralph subprocess. ``HOME`` is pinned to
a fixed, empty ``tmp_path`` directory so the real engine call in
``TestApprovedRunReachesEngine`` never touches this machine's actual
``~/.local/state/ai-dev-orchestrator`` persisted state.
"""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

import pytest

from orchestrator.engine import RunResult

from aido_code import __main__ as entrypoint
from aido_code.engine_client import EngineClient
from tests.conftest import REGISTRY_TWO_WORKERS, FakeAdapter, ScriptedRalphRunner, commit_action, init_git_repo


def _roadmap_text(*, status: str) -> str:
    return dedent(
        f"""
        # ROADMAP — RoadmapLab

        ## Current milestone

        Status: {status}

        ### ID

        m1

        ### Objective

        Ship the first milestone.

        ### WorkItems

        #### wi-1 — First task

        Dependencies: none
        Capabilities: development

        Acceptance criteria:
        - Something is true.

        ### QA

        #### QA-01 — Tests

        Kind: unit_test
        Required: true
        Timeout: 300
        Argv: ["{sys.executable}", "-c", "pass"]
        """
    ).lstrip()


def _make_project(tmp_path: Path, *, status: str) -> Path:
    """Lays out a full AIDO project (``aido.yaml`` + ``ROADMAP.md``, a
    real Git repo) directly under ``tmp_path`` — returns the project
    directory (the ``aido-code run`` CLI reads ``./aido.yaml`` from the
    current directory, like every other project command)."""
    project_dir = tmp_path / "roadmaplab"
    project_dir.mkdir()
    (project_dir / "resources").mkdir()
    (project_dir / "ROADMAP.md").write_text(_roadmap_text(status=status))
    (project_dir / "aido.yaml").write_text(
        dedent(
            """
            schema_version: 1

            project:
              id: roadmaplab
              name: RoadmapLab
              workspace: "."

            roadmap: "./ROADMAP.md"

            resources: "./resources"

            initial_prompt: >
              Read ROADMAP.md before doing any work.
            """
        )
    )
    # tests/conftest.py's own init_git_repo() also writes a pyproject.toml
    # stub before the initial commit: the real OrchestratorEngine's
    # internal QA phase needs a detectable stack even for a trivial,
    # already-passing QA command, or it fails closed at the
    # infrastructure/execution level (QARunStatus.FAILED) rather than
    # ever reaching the QA command itself.
    init_git_repo(project_dir)
    return project_dir


def _set_worker_registry_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    xdg_home = tmp_path / "xdg"
    aido_dir = xdg_home / "aido"
    aido_dir.mkdir(parents=True)
    (aido_dir / "workers.yaml").write_text(REGISTRY_TWO_WORKERS)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))


def _pin_fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))


class TestDraftRunRefusesCleanly:
    def test_draft_run_exits_nonzero_without_touching_engine_or_provider(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = _make_project(tmp_path, status="DRAFT")
        _set_worker_registry_override(tmp_path, monkeypatch)
        _pin_fake_home(tmp_path, monkeypatch)
        monkeypatch.chdir(target)
        monkeypatch.setattr(
            entrypoint, "build_engine_plan",
            lambda *a, **k: pytest.fail("DRAFT run built an engine plan"),
        )
        monkeypatch.setattr(
            entrypoint.EngineClient, "from_config",
            lambda *a, **k: pytest.fail("DRAFT run constructed an engine"),
        )

        exit_code = entrypoint.main(["run"])

        assert exit_code != 0
        err = capsys.readouterr().err
        assert "DRAFT" in err
        assert "Not executable" in err

    def test_draft_run_never_reaches_a_provider_probe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = _make_project(tmp_path, status="DRAFT")
        _set_worker_registry_override(tmp_path, monkeypatch)
        _pin_fake_home(tmp_path, monkeypatch)
        monkeypatch.chdir(target)

        never_called = FakeAdapter(available=True)
        original_from_config = EngineClient.from_config

        def _poisoned_from_config(config, *, worker_registry, **kwargs):
            return original_from_config(
                config, worker_registry=worker_registry, provider_adapters={"anthropic": never_called},
                subprocess_runner=ScriptedRalphRunner([]),
            )

        monkeypatch.setattr(entrypoint.EngineClient, "from_config", _poisoned_from_config)

        assert entrypoint.main(["run"]) != 0
        assert never_called.calls == 0


class TestApprovedRunReachesEngine:
    def test_approved_run_drives_a_real_workitem_to_completed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = _make_project(tmp_path, status="APPROVED")
        _set_worker_registry_override(tmp_path, monkeypatch)
        _pin_fake_home(tmp_path, monkeypatch)
        monkeypatch.chdir(target)

        runner = ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )

        original_from_config = EngineClient.from_config

        def _fake_from_config(config, *, worker_registry, **kwargs):
            assert worker_registry is not None
            assert worker_registry.enabled_workers()
            return original_from_config(
                config, worker_registry=worker_registry,
                provider_adapters={"anthropic": FakeAdapter(available=True)},
                subprocess_runner=runner,
            )

        monkeypatch.setattr(entrypoint.EngineClient, "from_config", _fake_from_config)

        exit_code = entrypoint.main(["run"])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "all_terminal: True" in out
        assert "wi-1: completed" in out
        assert len(runner.calls) == 2

    def test_approved_run_passes_the_typed_plan_and_injected_registry_to_from_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = _make_project(tmp_path, status="APPROVED")
        _set_worker_registry_override(tmp_path, monkeypatch)
        _pin_fake_home(tmp_path, monkeypatch)
        monkeypatch.chdir(target)

        captured: dict[str, object] = {}

        class _StubClient:
            def __enter__(self) -> "_StubClient":
                return self

            def __exit__(self, *exc_info: object) -> bool:
                return False

            def run(self):
                return RunResult(cycles_run=0, all_terminal=True, reached_max_cycles=False, work_items=())

        def _capturing_from_config(config, *, worker_registry, **kwargs):
            captured["config"] = config
            captured["worker_registry"] = worker_registry
            return _StubClient()

        monkeypatch.setattr(entrypoint.EngineClient, "from_config", _capturing_from_config)

        assert entrypoint.main(["run"]) == 0
        assert captured["config"].project.id == "roadmaplab"
        assert captured["config"].mvp.id == "m1"
        assert captured["config"].work_items[0].id == "wi-1"
        assert captured["worker_registry"].enabled_workers()
