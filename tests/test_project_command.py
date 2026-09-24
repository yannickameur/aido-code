"""WI-M1.4-07A: project-command context loading + ``aido-code validate``
integration (``aido_code.project_command``). See ``docs/
PROJECT_CONTRACT.md`` §7.

Offline only: every case here uses a real ``tmp_path`` project scaffolded
by ``aido_code.project_init.run_init`` (WI-M1.4-06) — never a network/
provider call. ``aido-code run``/``/status``/``/workers``/``/config``
remain WI-M1.4-07B/C/D's own scope; this file only proves the shared
loading path (manifest -> roadmap -> resources -> AIDO WorkerRegistry, in
that order) and the ``validate`` command built on it.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from orchestrator.worker_registry import WorkerRegistryError

from aido_code import __main__ as entrypoint
from aido_code import project_init
from aido_code.project_command import load_project_command_context
from aido_code.project_manifest import ProjectManifestError
from aido_code.project_resources import ProjectResourcesError
from aido_code.roadmap import RoadmapError

MALFORMED_WORKERS_OVERRIDE = dedent(
    """
    workers:
      - worker_id: broken
        display_name: Broken
        provider: anthropic
        backend: claude_code
        capabilities: [development]
        profiles: {}
    """
)


def _init(tmp_path: Path, name: str = "roadmaplab") -> Path:
    assert project_init.run_init(str(tmp_path), name) == 0
    return tmp_path / name


def _approve(target: Path) -> None:
    roadmap_path = target / "ROADMAP.md"
    roadmap_path.write_text(
        roadmap_path.read_text().replace("Status: DRAFT", "Status: APPROVED"), encoding="utf-8",
    )


class TestLoadProjectCommandContext:
    def test_loads_manifest_roadmap_resources_and_registry_in_order(self, tmp_path: Path) -> None:
        target = _init(tmp_path)

        context = load_project_command_context(target / "aido.yaml")

        assert context.manifest.project.id == "roadmaplab"
        assert context.roadmap.milestone.status == "DRAFT"
        assert context.resources.mvp_objective
        assert context.worker_registry.enabled_workers()

    def test_invalid_manifest_stops_before_roadmap_is_parsed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = _init(tmp_path)
        (target / "aido.yaml").write_text("not: [valid: yaml", encoding="utf-8")
        monkeypatch.setattr(
            "aido_code.project_command.parse_roadmap",
            lambda *a, **k: pytest.fail("manifest error did not stop before roadmap parsing"),
        )

        with pytest.raises(ProjectManifestError):
            load_project_command_context(target / "aido.yaml")

    def test_invalid_roadmap_stops_before_resources_are_resolved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = _init(tmp_path)
        (target / "ROADMAP.md").write_text("not a roadmap at all", encoding="utf-8")
        monkeypatch.setattr(
            "aido_code.project_command.resolve_project_resources",
            lambda *a, **k: pytest.fail("roadmap error did not stop before resources resolution"),
        )

        with pytest.raises(RoadmapError):
            load_project_command_context(target / "aido.yaml")

    def test_missing_resource_stops_before_worker_registry_loads(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = _init(tmp_path)
        roadmap_path = target / "ROADMAP.md"
        roadmap_path.write_text(
            roadmap_path.read_text() + "\n## Sources\n\n- resources/missing.md\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(
            "aido_code.project_command.load_worker_registry",
            lambda *a, **k: pytest.fail("resources error did not stop before worker registry loading"),
        )

        with pytest.raises(ProjectResourcesError):
            load_project_command_context(target / "aido.yaml")

    def test_malformed_workers_override_fails_closed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = _init(tmp_path)
        xdg_home = tmp_path / "xdg"
        aido_dir = xdg_home / "aido"
        aido_dir.mkdir(parents=True)
        (aido_dir / "workers.yaml").write_text(MALFORMED_WORKERS_OVERRIDE)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))

        with pytest.raises(WorkerRegistryError):
            load_project_command_context(target / "aido.yaml")


class TestValidateCommand:
    def test_draft_reports_not_executable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = _init(tmp_path)
        capsys.readouterr()
        monkeypatch.chdir(target)

        assert entrypoint.main(["validate"]) == 0
        assert capsys.readouterr().out == "VALID\nCurrent milestone: DRAFT\nNot executable.\n"

    def test_approved_reports_executable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = _init(tmp_path)
        _approve(target)
        capsys.readouterr()
        monkeypatch.chdir(target)

        assert entrypoint.main(["validate"]) == 0
        assert capsys.readouterr().out == "VALID\nCurrent milestone: APPROVED\nExecutable.\n"

    def test_never_constructs_an_engine_or_provider(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        target = _init(tmp_path)
        _approve(target)
        monkeypatch.chdir(target)
        monkeypatch.setattr(
            entrypoint.EngineClient, "from_config",
            lambda *args, **kwargs: pytest.fail("validate constructed an engine"),
        )

        assert entrypoint.main(["validate"]) == 0

    def test_invalid_manifest_fails_with_nonzero_exit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = _init(tmp_path)
        (target / "aido.yaml").write_text("not: [valid: yaml", encoding="utf-8")
        monkeypatch.chdir(target)

        assert entrypoint.main(["validate"]) != 0
        assert capsys.readouterr().err.startswith("Error: ")

    def test_invalid_roadmap_fails_with_nonzero_exit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = _init(tmp_path)
        (target / "ROADMAP.md").write_text("not a roadmap at all", encoding="utf-8")
        monkeypatch.chdir(target)

        assert entrypoint.main(["validate"]) != 0
        assert capsys.readouterr().err.startswith("Error: ")

    def test_missing_resource_fails_with_nonzero_exit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = _init(tmp_path)
        roadmap_path = target / "ROADMAP.md"
        roadmap_path.write_text(
            roadmap_path.read_text() + "\n## Sources\n\n- resources/missing.md\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(target)

        assert entrypoint.main(["validate"]) != 0
        assert capsys.readouterr().err.startswith("Error: ")

    def test_malformed_workers_override_fails_with_nonzero_exit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = _init(tmp_path)
        xdg_home = tmp_path / "xdg"
        aido_dir = xdg_home / "aido"
        aido_dir.mkdir(parents=True)
        (aido_dir / "workers.yaml").write_text(MALFORMED_WORKERS_OVERRIDE)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))
        monkeypatch.chdir(target)

        assert entrypoint.main(["validate"]) != 0
        assert capsys.readouterr().err.startswith("Error: ")
