"""WI-07/WI-M1.4-07D: one offline, end-to-end test driving a real M1.4
project through its actual, documented lifecycle (``docs/CLI_SPEC.md``):
CLI-level ``aido-code validate``/``aido-code run`` (``aido_code.
__main__``, the modern manifest/``ROADMAP.md``/``WorkerRegistry`` path,
WI-M1.4-07A/B) followed by a REPL session's ``/status`` reflecting that
same real, persisted engine state (WI-M1.4-07D) — before any run
(``NOT_INITIALIZED``) and after a real WorkItem Flow completes.

``/validate``/``/run`` inside the REPL still delegate to the legacy,
``ProjectConfig``-shaped ``EngineClient.open()`` path (unmigrated, out
of scope for WI-M1.4-07D — see ``tests/test_repl.py``'s own
``TestValidate``/``TestRun``, which keep exercising that path directly),
so a single project can no longer run this whole lifecycle through REPL
commands alone: this test drives ``validate``/``run`` at the CLI level
instead, exactly as a real ``aido-code`` user would, per
``docs/CLI_SPEC.md``.

Offline only: no real provider or Ralph subprocess anywhere in this
test, via the same tests/conftest.py fixtures as test_repl.py and
test_run_command.py (see CONTRIBUTING.md).
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from aido_code import __main__ as entrypoint
from aido_code.repl import run
from tests.conftest import REGISTRY_TWO_WORKERS, FakeAdapter, ScriptedRalphRunner, commit_action, init_git_repo


def _roadmap_text() -> str:
    return dedent(
        f"""
        # ROADMAP — RoadmapLab

        ## Current milestone

        Status: APPROVED

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


def _make_project(tmp_path: Path) -> Path:
    """Lays out a full AIDO project (``aido.yaml`` + ``ROADMAP.md``, a
    real Git repo) directly under ``tmp_path`` — returns the project
    directory. Its milestone is already ``APPROVED`` since this test's
    concern is the status/run lifecycle, not the DRAFT/APPROVED gate
    itself (covered by ``tests/test_run_command.py``'s own
    ``TestDraftRunRefusesCleanly``)."""
    project_dir = tmp_path / "roadmaplab"
    project_dir.mkdir()
    (project_dir / "resources").mkdir()
    (project_dir / "ROADMAP.md").write_text(_roadmap_text())
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


class TestFullProjectLifecycle:
    def test_status_validate_run_status_exit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = _make_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch)
        _pin_fake_home(tmp_path, monkeypatch)
        monkeypatch.chdir(target)

        # /status, before any run: real, persisted engine state, never a
        # status guessed from the roadmap's own APPROVED milestone.
        output = io.StringIO()
        run(io.StringIO("/status\n/exit\n"), output, config_path=str(target / "aido.yaml"))
        before_transcript = output.getvalue()
        assert "Traceback" not in before_transcript
        assert "current_milestone_status: APPROVED" in before_transcript
        assert "NOT_INITIALIZED" in before_transcript

        # `aido-code validate` (CLI-level, provider-free).
        capsys.readouterr()
        assert entrypoint.main(["validate"]) == 0
        assert capsys.readouterr().out == "VALID\nCurrent milestone: APPROVED\nExecutable.\n"

        # `aido-code run` (CLI-level): a real OrchestratorEngine WorkItem
        # Flow cycle, offline fake provider/subprocess seams injected the
        # same way tests/test_run_command.py's own
        # TestApprovedRunReachesEngine does (aido_code.__main__.main()
        # itself exposes no provider_adapters/subprocess_runner
        # parameter).
        runner = ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )
        original_from_config = entrypoint.EngineClient.from_config

        def _fake_from_config(config, *, worker_registry, **kwargs):
            return original_from_config(
                config, worker_registry=worker_registry,
                provider_adapters={"anthropic": FakeAdapter(available=True)},
                subprocess_runner=runner,
            )

        monkeypatch.setattr(entrypoint.EngineClient, "from_config", _fake_from_config)

        capsys.readouterr()
        assert entrypoint.main(["run"]) == 0
        run_out = capsys.readouterr().out
        assert "all_terminal: True" in run_out
        assert "wi-1: completed" in run_out
        assert len(runner.calls) == 2

        # /status, after that same real run: reflects the real persisted
        # completion, not a re-run and not anything read back out of
        # ROADMAP.md.
        output = io.StringIO()
        run(io.StringIO("/status\n/exit\n"), output, config_path=str(target / "aido.yaml"))
        after_transcript = output.getvalue()
        assert "Traceback" not in after_transcript
        assert "current_milestone_status: APPROVED" in after_transcript
        assert "NOT_INITIALIZED" not in after_transcript
        assert "project: roadmaplab (RoadmapLab)" in after_transcript
        assert "wi-1: completed" in after_transcript


class TestInitDraftToApprovedLifecycle:
    """Final regression/clean-install/portability acceptance: the whole
    product-boundary story chained through the *real* CLI entry points a
    user actually runs — ``aido-code init`` (``aido_code.project_init``,
    WI-M1.4-06), never a hand-crafted project directory — through a
    genuine ``DRAFT`` scaffold, an edit to ``ROADMAP.md``, and on into a
    real ``OrchestratorEngine`` WorkItem Flow cycle (offline fake
    provider/subprocess seams only, per ``CONTRIBUTING.md``).

    This single test proves, together with these already-dedicated,
    exhaustive proofs elsewhere in this suite:
    - ``ROADMAP.md``, not ``aido.yaml``, is the functional source of
      truth for executability (below: identical ``aido.yaml``, DRAFT vs.
      APPROVED ``ROADMAP.md`` content flips ``validate``'s verdict).
    - a project's own ``aido.yaml`` can never carry a worker/provider/
      model — structurally impossible, not just untested (``aido_code.
      project_manifest``'s top-level key allowlist; exhaustively
      unit-tested in ``tests/test_project_manifest.py``'s own
      ``TestUnknownTopLevelKeys``) — checked again below directly against
      the real, ``aido-code init``-generated file.
    - AIDO's workers are global, resolved independently of this project
      and injected into the engine (below: the injected
      ``WorkerRegistry`` is asserted non-empty; the global resolution
      rules themselves, including the clean-install case and every
      forbidden path ``docs/PROJECT_CONTRACT.md`` §4 names, are
      exhaustively covered in ``tests/test_worker_config.py``).
    - ``resources/`` confinement is exercised through ``validate``
      below; edge cases have dedicated coverage in
      ``tests/test_project_resources.py``.
    - no private engine orchestration component (``MVPManager``/
      ``WorkerSelector``/``QuotaManager``/a ``ProviderAdapter``/
      ``InternalQAEngine``/``GitGovernanceService``/a ``Store``) is ever
      importable from ``aido_code`` — a static, package-wide proof
      stronger than any single runtime test could give, in
      ``tests/test_structural.py``.
    """

    def test_real_init_draft_refuses_then_approved_reaches_real_engine(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        # `aido-code init` — a fresh, real DRAFT project, exactly as a
        # user would create one.
        assert entrypoint.main(["init", str(tmp_path), "acceptance-project"]) == 0
        target = tmp_path / "acceptance-project"
        _set_worker_registry_override(tmp_path, monkeypatch)
        _pin_fake_home(tmp_path, monkeypatch)
        monkeypatch.chdir(target)

        manifest_text = (target / "aido.yaml").read_text()
        for forbidden in ("workers:", "providers:", "models:"):
            assert forbidden not in manifest_text, f"aido.yaml must never carry {forbidden!r}"

        original_from_config = entrypoint.EngineClient.from_config

        # `aido-code validate` on the untouched scaffold: DRAFT, not
        # executable.
        capsys.readouterr()
        assert entrypoint.main(["validate"]) == 0
        assert capsys.readouterr().out == "VALID\nCurrent milestone: DRAFT\nNot executable.\n"

        # `aido-code run` on that same DRAFT project: refused before any
        # engine/provider is ever constructed.
        monkeypatch.setattr(
            entrypoint.EngineClient, "from_config",
            lambda *a, **k: pytest.fail("DRAFT run constructed an engine"),
        )
        assert entrypoint.main(["run"]) != 0
        assert "DRAFT" in capsys.readouterr().err

        # Prepare an APPROVED mini milestone. A trivial pyproject.toml is added
        # alongside it (a real user's own stack file): the real engine's
        # QA phase needs a detectable stack even for a trivial,
        # already-passing QA command, or it fails closed before ever
        # reaching that command (see tests/conftest.py's init_git_repo()).
        (target / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
        source = target / "resources" / "specification.md"
        source.write_text("Ship only the first task.\n")
        sources_heading = "## Sources\n\n- resources/specification.md\n\n"
        approved_roadmap = _roadmap_text().replace("## Current milestone", sources_heading + "## Current milestone")
        # The same CLI validation path must reject a source escaping the
        # project, even when the milestone is otherwise executable.
        (target / "ROADMAP.md").write_text(
            approved_roadmap.replace("resources/specification.md", "../outside.md")
        )
        (tmp_path / "outside.md").write_text("outside\n")
        capsys.readouterr()
        assert entrypoint.main(["validate"]) != 0
        assert "without '..' traversal" in capsys.readouterr().err
        (target / "ROADMAP.md").write_text(approved_roadmap)
        subprocess.run(["git", "add", "-A"], cwd=target, check=True)
        subprocess.run(
            [
                "git", "-c", "user.email=e2e@example.invalid", "-c", "user.name=E2E",
                "commit", "-q", "-m", "Approve first milestone",
            ],
            cwd=target, check=True,
        )

        # `aido-code validate` again: the unchanged aido.yaml and the
        # now-valid ROADMAP.md yield APPROVED and executable.
        capsys.readouterr()
        assert entrypoint.main(["validate"]) == 0
        assert capsys.readouterr().out == "VALID\nCurrent milestone: APPROVED\nExecutable.\n"
        assert (target / "aido.yaml").read_text() == manifest_text

        # `aido-code run`: a real OrchestratorEngine WorkItem Flow cycle,
        # offline fake provider/subprocess seams injected the same way
        # TestFullProjectLifecycle above does.
        runner = ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )
        captured: dict[str, object] = {}

        def _fake_from_config(config, *, worker_registry, **kwargs):
            captured["worker_registry"] = worker_registry
            assert config.workers_registry_path is None
            assert "resources/specification.md" in config.mvp.objective
            return original_from_config(
                config, worker_registry=worker_registry,
                provider_adapters={"anthropic": FakeAdapter(available=True)},
                subprocess_runner=runner,
            )

        monkeypatch.setattr(entrypoint.EngineClient, "from_config", _fake_from_config)

        capsys.readouterr()
        assert entrypoint.main(["run"]) == 0
        run_out = capsys.readouterr().out
        assert "all_terminal: True" in run_out
        assert "wi-1: completed" in run_out
        assert len(runner.calls) == 2

        # The engine received AIDO's own globally-resolved WorkerRegistry
        # — never one read from this project.
        assert captured["worker_registry"] is not None
        assert captured["worker_registry"].enabled_workers()
