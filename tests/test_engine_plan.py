"""WI-M1.4-05: typed engine plan builder + WorkerRegistry injection
(``aido_code.engine_plan``). See ``docs/PROJECT_CONTRACT.md`` §6.

Offline only: every case uses a real ``tmp_path`` project layout and a
real ``git init`` repo — never a network/provider call. Worker-facing
engine calls (``.workers()``/``.validate()``) go through a real
``OrchestratorEngine`` with fake provider adapters/subprocess runner
injected, per ``CONTRIBUTING.md``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from orchestrator.execution_policy import ExecutionPermissionMode
from orchestrator.project_config import ProjectConfig
from orchestrator.validation import ValidationKind
from orchestrator.worker_registry import WorkerRegistry

from aido_code.engine_client import EngineClient
from aido_code.engine_plan import MissingGitWorkspaceError, build_engine_plan
from aido_code.project_manifest import load_project_manifest
from aido_code.project_resources import resolve_project_resources
from aido_code.roadmap import parse_roadmap
from tests.conftest import REGISTRY_TWO_WORKERS, NeverCalledAdapter

_GIT_ENV = ["-c", "user.email=e2e@example.invalid", "-c", "user.name=E2E"]


def _roadmap_text(*, project_name: str) -> str:
    return dedent(
        f"""
        # ROADMAP — {project_name}

        ## Sources

        - resources/specification.md

        ## Current milestone

        Status: APPROVED

        ### ID

        m1

        ### Objective

        Ship the first milestone.

        ### Acceptance criteria

        - The feature works as described.

        ### WorkItems

        #### WI-01 — First task

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


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=str(path), check=True)
    subprocess.run(["git", *_GIT_ENV, "add", "-A"], cwd=str(path), check=True)
    subprocess.run(["git", *_GIT_ENV, "commit", "-q", "-m", "init"], cwd=str(path), check=True)


def _make_project(
    tmp_path: Path,
    *,
    project_id: str = "myproject",
    project_name: str = "MyProject",
    init_git: bool = True,
) -> Path:
    """Lays out a full project (aido.yaml + ROADMAP.md + resources/) under
    ``tmp_path / project_id``, optionally a real Git repo. Returns the
    ``aido.yaml`` path."""
    project_dir = tmp_path / project_id
    project_dir.mkdir()
    (project_dir / "resources").mkdir()
    (project_dir / "resources" / "specification.md").write_text("spec content\n")
    (project_dir / "ROADMAP.md").write_text(_roadmap_text(project_name=project_name))
    manifest_path = project_dir / "aido.yaml"
    manifest_path.write_text(
        dedent(
            f"""
            schema_version: 1

            project:
              id: {project_id}
              name: {project_name}
              workspace: "."

            roadmap: "./ROADMAP.md"

            resources: "./resources"

            initial_prompt: >
              Read ROADMAP.md and the project resources referenced by it.
            """
        )
    )
    if init_git:
        _init_git_repo(project_dir)
    return manifest_path


def _build_plan(manifest_path: Path) -> ProjectConfig:
    manifest = load_project_manifest(manifest_path)
    roadmap = parse_roadmap(manifest.roadmap)
    resolved = resolve_project_resources(manifest, roadmap)
    return build_engine_plan(manifest, roadmap, resolved)


def _load_registry(tmp_path: Path, *, name: str = "workers.yaml") -> WorkerRegistry:
    registry_path = tmp_path / name
    registry_path.write_text(REGISTRY_TWO_WORKERS)
    return WorkerRegistry.load(registry_path)


class TestFieldMapping:
    def test_full_fixture_produces_expected_project_config(self, tmp_path: Path) -> None:
        manifest_path = _make_project(tmp_path, project_id="myproject", project_name="MyProject")
        manifest = load_project_manifest(manifest_path)
        roadmap = parse_roadmap(manifest.roadmap)
        resolved = resolve_project_resources(manifest, roadmap)

        config = build_engine_plan(manifest, roadmap, resolved)

        assert config.workers_registry_path is None
        assert config.project.id == "myproject"
        assert config.project.name == "MyProject"
        assert config.project.workspace == manifest.project.workspace
        assert config.project.state_dir == (
            Path.home() / ".local" / "state" / "ai-dev-orchestrator" / "projects" / "myproject"
        )
        assert config.execution.permission_mode == ExecutionPermissionMode.STANDARD
        assert config.git.base_branch == "main"
        assert config.mvp.id == "m1"
        assert config.mvp.objective == resolved.mvp_objective
        assert config.mvp.acceptance_criteria == ("The feature works as described.",)

        assert len(config.work_items) == 1
        work_item = config.work_items[0]
        assert work_item.id == "WI-01"
        assert work_item.title == "First task"
        assert work_item.required_capabilities == ("development",)
        assert work_item.dependencies == ()
        assert work_item.acceptance_criteria == ("Something is true.",)

        assert len(config.qa_commands) == 1
        qa_command = config.qa_commands[0]
        assert qa_command.validation_id == "QA-01"
        assert qa_command.kind == ValidationKind.UNIT_TEST
        assert qa_command.argv == (sys.executable, "-c", "pass")
        assert qa_command.timeout_seconds == 300.0
        assert qa_command.required is True

        assert config.qa_protected_paths == ()
        assert config.source_path == roadmap.source_path


class TestGitWorkspaceGate:
    def test_non_git_workspace_rejected_before_engine_call(self, tmp_path: Path) -> None:
        manifest_path = _make_project(tmp_path, init_git=False)
        manifest = load_project_manifest(manifest_path)
        roadmap = parse_roadmap(manifest.roadmap)
        resolved = resolve_project_resources(manifest, roadmap)

        with pytest.raises(MissingGitWorkspaceError):
            build_engine_plan(manifest, roadmap, resolved)


class TestWorkerRegistryInjectionReachesEngine:
    def test_injected_registry_reaches_workers_and_validate(self, tmp_path: Path) -> None:
        manifest_path = _make_project(tmp_path)
        config = _build_plan(manifest_path)
        registry = _load_registry(tmp_path)

        client = EngineClient.from_config(
            config, worker_registry=registry, provider_adapters={"anthropic": NeverCalledAdapter()},
        )

        workers = client.workers()
        assert {w.worker_id for w in workers} == {"alice", "bob"}

        snapshot = client.validate()
        assert snapshot.project_id == "myproject"
        assert snapshot.mvp_id == "m1"
        assert snapshot.enabled_worker_count == 2
        assert snapshot.providers == ("anthropic",)
        assert snapshot.permission_mode == "standard"
        assert snapshot.base_branch == "main"


class TestSharedWorkerRegistryAcrossProjects:
    def test_two_projects_share_one_registry_instance_independently(self, tmp_path: Path) -> None:
        registry = _load_registry(tmp_path)

        first_manifest = _make_project(tmp_path, project_id="project-a", project_name="Project A")
        second_manifest = _make_project(tmp_path, project_id="project-b", project_name="Project B")
        first_config = _build_plan(first_manifest)
        second_config = _build_plan(second_manifest)

        first_client = EngineClient.from_config(
            first_config, worker_registry=registry, provider_adapters={"anthropic": NeverCalledAdapter()},
        )
        second_client = EngineClient.from_config(
            second_config, worker_registry=registry, provider_adapters={"anthropic": NeverCalledAdapter()},
        )

        first_snapshot = first_client.validate()
        second_snapshot = second_client.validate()

        assert first_snapshot.project_id == "project-a"
        assert second_snapshot.project_id == "project-b"
        assert first_snapshot.enabled_worker_count == 2
        assert second_snapshot.enabled_worker_count == 2
        assert {w.worker_id for w in first_client.workers()} == {"alice", "bob"}
        assert {w.worker_id for w in second_client.workers()} == {"alice", "bob"}


class TestStateDirNonRegression:
    def test_state_dir_matches_the_convention_prior_milestones_already_use(self, tmp_path: Path) -> None:
        manifest_path = _make_project(tmp_path, project_id="aido-code", project_name="AIDO Code")

        config = _build_plan(manifest_path)

        assert config.project.state_dir == (
            Path.home() / ".local" / "state" / "ai-dev-orchestrator" / "projects" / "aido-code"
        )
