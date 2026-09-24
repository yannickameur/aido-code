"""WI-M1.4-04: resources resolution/confinement + ``initial_prompt``
(``aido_code.project_resources``). See ``docs/PROJECT_CONTRACT.md`` §5.

Offline only: every case here uses a real ``tmp_path`` project layout —
never a network/provider call.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from aido_code.project_manifest import InvalidProjectManifestError, load_project_manifest
from aido_code.project_resources import (
    InvalidSourceError,
    build_mvp_objective,
    resolve_project_resources,
    resolve_sources,
)
from aido_code.roadmap import parse_roadmap


def _roadmap_text(*, sources_block: str, objective: str = "Free text — this milestone's own objective.") -> str:
    template = dedent(
        """
        # ROADMAP — My Project

        ## Vision

        Free text. Not parsed structurally.

        __SOURCES_BLOCK__## Current milestone

        Status: APPROVED

        ### ID

        m1

        ### Objective

        __OBJECTIVE__

        ### WorkItems

        #### WI-01 — First task

        Dependencies: none
        Capabilities: development

        Acceptance criteria:
        - Something is true.
        """
    ).lstrip()
    return template.replace("__SOURCES_BLOCK__", sources_block).replace("__OBJECTIVE__", objective)


def _make_project(
    tmp_path: Path,
    *,
    sources_block: str = "## Sources\n\n- resources/specification.md\n\n",
    objective: str = "Free text — this milestone's own objective.",
    make_resources_dir: bool = True,
    make_declared_sources: bool = True,
    initial_prompt: str = "Read ROADMAP.md and the project resources referenced by it.",
) -> Path:
    """Lays out a full project: aido.yaml + workspace containing
    ROADMAP.md, resources/, and (optionally) the declared source files.
    Returns the aido.yaml path."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "ROADMAP.md").write_text(_roadmap_text(sources_block=sources_block, objective=objective))
    if make_resources_dir:
        (project_dir / "resources").mkdir()
        if make_declared_sources:
            (project_dir / "resources" / "specification.md").write_text("spec content\n")
    manifest_path = project_dir / "aido.yaml"
    manifest_path.write_text(
        dedent(
            f"""
            schema_version: 1

            project:
              id: myproject
              name: MyProject
              workspace: "."

            roadmap: "./ROADMAP.md"

            resources: "./resources"

            initial_prompt: >
              {initial_prompt}
            """
        )
    )
    return manifest_path


class TestMissingResourcesDirectory:
    def test_rejected_at_manifest_load(self, tmp_path: Path) -> None:
        manifest_path = _make_project(tmp_path, make_resources_dir=False)
        with pytest.raises(InvalidProjectManifestError, match="not an existing directory"):
            load_project_manifest(manifest_path)


class TestMissingDeclaredSourceFile:
    def test_rejected(self, tmp_path: Path) -> None:
        manifest_path = _make_project(tmp_path, make_declared_sources=False)
        manifest = load_project_manifest(manifest_path)
        roadmap = parse_roadmap(manifest.roadmap)

        with pytest.raises(InvalidSourceError, match="does not exist on disk"):
            resolve_project_resources(manifest, roadmap)


class TestDotDotTraversal:
    def test_rejected(self, tmp_path: Path) -> None:
        outside = tmp_path / "outside_secret.md"
        outside.write_text("secret\n")
        manifest_path = _make_project(
            tmp_path,
            sources_block="## Sources\n\n- ../outside_secret.md\n\n",
            make_declared_sources=False,
        )
        manifest = load_project_manifest(manifest_path)
        roadmap = parse_roadmap(manifest.roadmap)

        with pytest.raises(InvalidSourceError, match="outside workspace"):
            resolve_project_resources(manifest, roadmap)


class TestSymlinkEscape:
    def test_symlinked_source_file_rejected(self, tmp_path: Path) -> None:
        outside = tmp_path / "outside_target.md"
        outside.write_text("outside content\n")
        manifest_path = _make_project(tmp_path, make_declared_sources=False)
        symlink_path = manifest_path.parent / "resources" / "specification.md"
        symlink_path.symlink_to(outside)
        manifest = load_project_manifest(manifest_path)
        roadmap = parse_roadmap(manifest.roadmap)

        with pytest.raises(InvalidSourceError, match="outside workspace"):
            resolve_project_resources(manifest, roadmap)

    def test_symlinked_intermediate_directory_rejected(self, tmp_path: Path) -> None:
        outside_dir = tmp_path / "outside_dir"
        outside_dir.mkdir()
        (outside_dir / "file.md").write_text("content\n")
        manifest_path = _make_project(
            tmp_path,
            sources_block="## Sources\n\n- resources/escape/file.md\n\n",
            make_declared_sources=False,
        )
        symlink_dir = manifest_path.parent / "resources" / "escape"
        symlink_dir.symlink_to(outside_dir, target_is_directory=True)
        manifest = load_project_manifest(manifest_path)
        roadmap = parse_roadmap(manifest.roadmap)

        with pytest.raises(InvalidSourceError, match="outside workspace"):
            resolve_project_resources(manifest, roadmap)


class TestUnreferencedResourceFileIsInert:
    def test_only_declared_sources_are_resolved(self, tmp_path: Path) -> None:
        manifest_path = _make_project(tmp_path)
        (manifest_path.parent / "resources" / "unreferenced.md").write_text("not declared\n")
        manifest = load_project_manifest(manifest_path)
        roadmap = parse_roadmap(manifest.roadmap)

        resolved = resolve_project_resources(manifest, roadmap)

        resolved_names = {path.name for path in resolved.sources}
        assert resolved_names == {"specification.md"}
        assert "unreferenced.md" not in resolved.mvp_objective


class TestResolveSourcesDoesNotWrite:
    def test_resource_file_contents_unchanged(self, tmp_path: Path) -> None:
        manifest_path = _make_project(tmp_path)
        source_file = manifest_path.parent / "resources" / "specification.md"
        before_mtime = source_file.stat().st_mtime_ns
        before_content = source_file.read_text()

        manifest = load_project_manifest(manifest_path)
        roadmap = parse_roadmap(manifest.roadmap)
        resolve_project_resources(manifest, roadmap)

        assert source_file.read_text() == before_content
        assert source_file.stat().st_mtime_ns == before_mtime


class TestCombinedObjectiveTemplate:
    def _assert_three_sections_in_order(
        self, objective: str, *, initial_prompt: str, milestone_id: str, milestone_objective: str
    ) -> None:
        prompt_index = objective.find(initial_prompt)
        milestone_header_index = objective.find(f"--- Current milestone objective (ROADMAP.md, {milestone_id}) ---")
        milestone_objective_index = objective.find(milestone_objective, milestone_header_index)
        sources_header_index = objective.find("--- Declared sources (ROADMAP.md, ## Sources) ---")

        assert prompt_index == 0
        assert -1 < milestone_header_index
        assert prompt_index < milestone_header_index < milestone_objective_index < sources_header_index

    def test_fixture_one_with_sources(self, tmp_path: Path) -> None:
        manifest_path = _make_project(
            tmp_path,
            initial_prompt="Read ROADMAP.md and the project resources referenced by it.",
            objective="Ship the first milestone.",
            sources_block="## Sources\n\n- resources/specification.md\n\n",
        )
        manifest = load_project_manifest(manifest_path)
        roadmap = parse_roadmap(manifest.roadmap)

        resolved = resolve_project_resources(manifest, roadmap)

        self._assert_three_sections_in_order(
            resolved.mvp_objective,
            initial_prompt=manifest.initial_prompt,
            milestone_id="m1",
            milestone_objective="Ship the first milestone.",
        )
        assert "resources/specification.md" in resolved.mvp_objective
        assert "(none)" not in resolved.mvp_objective

    def test_fixture_two_without_sources_uses_none_placeholder(self, tmp_path: Path) -> None:
        manifest_path = _make_project(
            tmp_path,
            initial_prompt="Follow the project contract exactly, nothing more.",
            objective="Deliver the second milestone's scope only.",
            sources_block="",
            make_declared_sources=False,
        )
        manifest = load_project_manifest(manifest_path)
        roadmap = parse_roadmap(manifest.roadmap)

        resolved = resolve_project_resources(manifest, roadmap)

        self._assert_three_sections_in_order(
            resolved.mvp_objective,
            initial_prompt=manifest.initial_prompt,
            milestone_id="m1",
            milestone_objective="Deliver the second milestone's scope only.",
        )
        assert resolved.sources == ()
        assert resolved.mvp_objective.endswith("(none)")


class TestResolveSourcesDirectly:
    def test_empty_sources_returns_empty_tuple(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        assert resolve_sources((), workspace=workspace) == ()

    def test_resolves_and_confines_a_valid_source(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "resources").mkdir()
        (workspace / "resources" / "doc.md").write_text("doc\n")

        resolved = resolve_sources(("resources/doc.md",), workspace=workspace)

        assert resolved == ((workspace / "resources" / "doc.md").resolve(),)


class TestBuildMvpObjectiveDirectly:
    def test_no_sources_renders_none_placeholder(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        objective = build_mvp_objective(
            initial_prompt="Do the thing.",
            milestone_id="m1",
            milestone_objective="The objective.",
            resolved_sources=(),
            workspace=workspace,
        )
        expected = (
            "Do the thing.\n"
            "\n"
            "--- Current milestone objective (ROADMAP.md, m1) ---\n"
            "The objective.\n"
            "\n"
            "--- Declared sources (ROADMAP.md, ## Sources) ---\n"
            "(none)"
        )
        assert objective == expected

    def test_sources_rendered_workspace_relative_one_per_line(self, tmp_path: Path) -> None:
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "resources").mkdir()
        first = workspace / "resources" / "a.md"
        second = workspace / "resources" / "b.md"
        first.write_text("a\n")
        second.write_text("b\n")

        objective = build_mvp_objective(
            initial_prompt="Do the thing.",
            milestone_id="m1",
            milestone_objective="The objective.",
            resolved_sources=(first.resolve(), second.resolve()),
            workspace=workspace,
        )

        assert objective.endswith("resources/a.md\nresources/b.md")
