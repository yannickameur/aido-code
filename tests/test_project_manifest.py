"""WI-M1.4-02: project manifest (``aido.yaml``) parser
(``aido_code.project_manifest``). See ``docs/PROJECT_CONTRACT.md`` §2.

Offline only: every case here uses a real ``tmp_path`` file — never a
network/provider call.
"""

from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

import pytest

from aido_code.project_manifest import (
    InvalidProjectManifestError,
    UnsupportedSchemaVersionError,
    load_project_manifest,
)


def _write_manifest(directory: Path, content: str, *, name: str = "aido.yaml") -> Path:
    path = directory / name
    path.write_text(dedent(content))
    return path


def _valid_manifest_text(*, workspace: str = ".") -> str:
    return dedent(
        f"""
        schema_version: 1

        project:
          id: myproject
          name: MyProject
          workspace: "{workspace}"

        roadmap: "./ROADMAP.md"

        resources: "./resources"

        initial_prompt: >
          Read ROADMAP.md and the project resources referenced by it before doing
          any work.
        """
    )


def _make_valid_project(tmp_path: Path) -> Path:
    """Lays out a minimal valid project: aido.yaml + workspace containing
    ROADMAP.md and resources/. Returns the aido.yaml path."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / "ROADMAP.md").write_text("# ROADMAP\n")
    (project_dir / "resources").mkdir()
    return _write_manifest(project_dir, _valid_manifest_text())


class TestValidMinimalManifest:
    def test_parses_all_fields(self, tmp_path: Path) -> None:
        manifest_path = _make_valid_project(tmp_path)
        manifest = load_project_manifest(manifest_path)

        assert manifest.schema_version == 1
        assert manifest.project.id == "myproject"
        assert manifest.project.name == "MyProject"
        assert manifest.project.workspace == manifest_path.parent.resolve()
        assert manifest.roadmap == (manifest_path.parent / "ROADMAP.md").resolve()
        assert manifest.resources == (manifest_path.parent / "resources").resolve()
        assert "Read ROADMAP.md" in manifest.initial_prompt
        assert manifest.source_path == manifest_path.resolve()


class TestUnknownTopLevelKeys:
    @pytest.mark.parametrize(
        "extra_key",
        ["workers", "providers", "models", "mvp", "work_items", "qa", "execution", "git", "made_up_key"],
    )
    def test_rejected(self, tmp_path: Path, extra_key: str) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "ROADMAP.md").write_text("# ROADMAP\n")
        (project_dir / "resources").mkdir()
        manifest_path = _write_manifest(
            project_dir, _valid_manifest_text() + f"\n{extra_key}: {{}}\n"
        )

        with pytest.raises(InvalidProjectManifestError, match="unknown field"):
            load_project_manifest(manifest_path)

    def test_mixed_type_unknown_keys_rejected(self, tmp_path: Path) -> None:
        manifest_path = _make_valid_project(tmp_path)
        manifest_path.write_text(_valid_manifest_text() + "\nother: 1\n42: value\n")
        with pytest.raises(InvalidProjectManifestError, match="unknown field"):
            load_project_manifest(manifest_path)


class TestSchemaVersion:
    @pytest.mark.parametrize("version", ["true", "1.0", "'1'"])
    def test_non_integer_schema_version_rejected(self, tmp_path: Path, version: str) -> None:
        manifest_path = _make_valid_project(tmp_path)
        manifest_path.write_text(
            _valid_manifest_text().replace("schema_version: 1", f"schema_version: {version}")
        )
        with pytest.raises(UnsupportedSchemaVersionError):
            load_project_manifest(manifest_path)

    def test_missing_schema_version_rejected(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        manifest_path = _write_manifest(
            project_dir,
            """
            project:
              id: myproject
              name: MyProject
              workspace: "."
            roadmap: "./ROADMAP.md"
            resources: "./resources"
            initial_prompt: "hello"
            """,
        )
        with pytest.raises(UnsupportedSchemaVersionError):
            load_project_manifest(manifest_path)

    def test_wrong_schema_version_rejected(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        manifest_path = _write_manifest(
            project_dir, _valid_manifest_text().replace("schema_version: 1", "schema_version: 2")
        )
        with pytest.raises(UnsupportedSchemaVersionError):
            load_project_manifest(manifest_path)


class TestProjectIdPattern:
    @pytest.mark.parametrize("bad_id", ["../evil", "has/slash", "-startswithdash", "has space", ""])
    def test_invalid_id_rejected(self, tmp_path: Path, bad_id: str) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "ROADMAP.md").write_text("# ROADMAP\n")
        (project_dir / "resources").mkdir()
        manifest_path = _write_manifest(
            project_dir, _valid_manifest_text().replace("id: myproject", f"id: {bad_id!r}")
        )
        with pytest.raises(InvalidProjectManifestError):
            load_project_manifest(manifest_path)

    def test_double_dot_in_id_rejected(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "ROADMAP.md").write_text("# ROADMAP\n")
        (project_dir / "resources").mkdir()
        manifest_path = _write_manifest(
            project_dir, _valid_manifest_text().replace("id: myproject", "id: a..b")
        )
        with pytest.raises(InvalidProjectManifestError):
            load_project_manifest(manifest_path)


class TestSecretGuardRail:
    @pytest.mark.parametrize(
        "field_name", ["api_key", "apikey", "token", "secret", "password", "passwd", "credential"]
    )
    def test_secret_like_field_rejected(self, tmp_path: Path, field_name: str) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "ROADMAP.md").write_text("# ROADMAP\n")
        (project_dir / "resources").mkdir()
        # Nest the secret-like key under project: (a *known* top-level
        # key) so this exercises _reject_secrets itself, not merely the
        # unknown-top-level-key check (which would also reject an
        # unknown key at the top level, masking whether the secret
        # guard-rail actually ran).
        manifest_path = _write_manifest(
            project_dir,
            _valid_manifest_text().replace(
                "workspace: \".\"", f"workspace: \".\"\n  {field_name}: sk-fake-value-12345"
            ),
        )
        with pytest.raises(InvalidProjectManifestError, match="looks like a secret"):
            load_project_manifest(manifest_path)


class TestPathEscapeRejected:
    def test_roadmap_dotdot_traversal_rejected(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "resources").mkdir()
        outside = tmp_path / "outside_ROADMAP.md"
        outside.write_text("# ROADMAP\n")
        manifest_path = _write_manifest(
            project_dir,
            _valid_manifest_text().replace('roadmap: "./ROADMAP.md"', 'roadmap: "../outside_ROADMAP.md"'),
        )
        with pytest.raises(InvalidProjectManifestError, match="outside project.workspace"):
            load_project_manifest(manifest_path)

    def test_resources_dotdot_traversal_rejected(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "ROADMAP.md").write_text("# ROADMAP\n")
        outside = tmp_path / "outside_resources"
        outside.mkdir()
        manifest_path = _write_manifest(
            project_dir,
            _valid_manifest_text().replace('resources: "./resources"', 'resources: "../outside_resources"'),
        )
        with pytest.raises(InvalidProjectManifestError, match="outside project.workspace"):
            load_project_manifest(manifest_path)

    def test_roadmap_symlink_escape_rejected(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "resources").mkdir()
        outside = tmp_path / "outside_ROADMAP.md"
        outside.write_text("# ROADMAP\n")
        symlink_path = project_dir / "ROADMAP.md"
        symlink_path.symlink_to(outside)
        manifest_path = _write_manifest(project_dir, _valid_manifest_text())

        with pytest.raises(InvalidProjectManifestError, match="outside project.workspace"):
            load_project_manifest(manifest_path)

    def test_resources_symlink_escape_rejected(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "ROADMAP.md").write_text("# ROADMAP\n")
        outside = tmp_path / "outside_resources"
        outside.mkdir()
        symlink_path = project_dir / "resources"
        symlink_path.symlink_to(outside, target_is_directory=True)
        manifest_path = _write_manifest(project_dir, _valid_manifest_text())

        with pytest.raises(InvalidProjectManifestError, match="outside project.workspace"):
            load_project_manifest(manifest_path)


class TestWorkspaceValidation:
    def test_missing_workspace_rejected(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "ROADMAP.md").write_text("# ROADMAP\n")
        (project_dir / "resources").mkdir()
        manifest_path = _write_manifest(
            project_dir, _valid_manifest_text(workspace="./does-not-exist")
        )
        with pytest.raises(InvalidProjectManifestError, match="not an existing directory"):
            load_project_manifest(manifest_path)

    def test_non_directory_workspace_rejected(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "ROADMAP.md").write_text("# ROADMAP\n")
        (project_dir / "resources").mkdir()
        (project_dir / "not-a-dir").write_text("plain file")
        manifest_path = _write_manifest(project_dir, _valid_manifest_text(workspace="./not-a-dir"))
        with pytest.raises(InvalidProjectManifestError, match="not an existing directory"):
            load_project_manifest(manifest_path)

    def test_non_directory_resources_rejected(self, tmp_path: Path) -> None:
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "ROADMAP.md").write_text("# ROADMAP\n")
        (project_dir / "resources").write_text("plain file, not a directory")
        manifest_path = _write_manifest(project_dir, _valid_manifest_text())
        with pytest.raises(InvalidProjectManifestError, match="not an existing directory"):
            load_project_manifest(manifest_path)


class TestRelativeToManifestDirNotCwd:
    def test_resolution_ignores_caller_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        manifest_path = _make_valid_project(tmp_path)

        elsewhere = tmp_path / "totally_unrelated_cwd"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)

        manifest = load_project_manifest(manifest_path)

        assert manifest.project.workspace == manifest_path.parent.resolve()
        assert manifest.roadmap == (manifest_path.parent / "ROADMAP.md").resolve()
        assert manifest.resources == (manifest_path.parent / "resources").resolve()
        # Proves resolution never touched os.getcwd()'s value.
        assert os.getcwd() == str(elsewhere)

    def test_absolute_manifest_path_argument_also_resolves_relative_to_its_own_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        manifest_path = _make_valid_project(tmp_path)
        monkeypatch.chdir(tmp_path)  # cwd is the parent of "project", not "project" itself

        manifest = load_project_manifest(str(manifest_path))

        assert manifest.project.workspace == manifest_path.parent.resolve()
