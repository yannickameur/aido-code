"""WI-M1.4-06: project bootstrap ``init`` (``aido_code.project_init``).
See ``docs/PROJECT_CONTRACT.md`` §7 and ``ROADMAP.md``, WI-M1.4-06.

Offline only: every case here uses a real ``tmp_path`` directory and a
real, local Git repository — never a network/provider call. Git's own
author/committer identity is supplied via environment variables so
these tests never depend on (or mutate) the host's global Git config.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from aido_code import __main__ as entrypoint
from aido_code import project_init
from aido_code.engine_plan import build_engine_plan
from aido_code.project_manifest import load_project_manifest
from aido_code.project_resources import resolve_project_resources
from aido_code.roadmap import parse_roadmap


@pytest.fixture(autouse=True)
def _hermetic_git_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_AUTHOR_NAME", "Test")
    monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@example.invalid")
    monkeypatch.setenv("GIT_COMMITTER_NAME", "Test")
    monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@example.invalid")


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class TestSuccessfulBootstrap:
    def test_creates_every_expected_file_and_a_git_history(self, tmp_path: Path) -> None:
        exit_code = project_init.run_init(str(tmp_path), "roadmaplab")

        assert exit_code == 0
        target = tmp_path / "roadmaplab"
        assert (target / ".git").is_dir()
        assert (target / ".gitignore").is_file()
        assert (target / "README.md").is_file()
        assert (target / "ROADMAP.md").is_file()
        assert (target / "aido.yaml").is_file()
        assert (target / "resources").is_dir()
        assert (target / "resources" / "README.md").is_file()

        log = _git(["log", "--format=%s"], cwd=target).stdout.strip().splitlines()
        assert log == ["Initialize AIDO project"]

        tracked = set(_git(["ls-files"], cwd=target).stdout.split())
        assert tracked == {".gitignore", "README.md", "ROADMAP.md", "aido.yaml", "resources/README.md"}

        status = _git(["status", "--porcelain"], cwd=target).stdout
        assert status == ""

    def test_scaffold_validates_as_draft_and_not_executable(self, tmp_path: Path) -> None:
        assert project_init.run_init(str(tmp_path), "roadmaplab") == 0
        target = tmp_path / "roadmaplab"

        manifest = load_project_manifest(target / "aido.yaml")
        roadmap = parse_roadmap(manifest.roadmap)
        resolved = resolve_project_resources(manifest, roadmap)

        assert roadmap.milestone.status == "DRAFT"
        assert roadmap.milestone.is_executable is False

        # A "run" gate (WI-M1.4-07) only ever proceeds when is_executable is
        # True — proven False above, so this scaffold's own milestone must
        # never reach an engine/provider call in its current, unedited
        # state. The typed engine plan itself is still buildable (the
        # deeper structural proof of "validate succeeds"): workspace is a
        # real Git work tree by the time this assertion runs.
        plan = build_engine_plan(manifest, roadmap, resolved)
        assert plan.mvp.id == "m1"

    def test_real_cli_validates_and_refuses_draft_run(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        assert project_init.run_init(str(tmp_path), "roadmaplab") == 0
        capsys.readouterr()
        monkeypatch.chdir(tmp_path / "roadmaplab")
        monkeypatch.setattr(
            entrypoint.EngineClient, "from_config",
            lambda *args, **kwargs: pytest.fail("DRAFT run constructed an engine"),
        )

        assert entrypoint.main(["validate"]) == 0
        assert capsys.readouterr().out == "VALID\nCurrent milestone: DRAFT\nNot executable.\n"
        assert entrypoint.main(["run"]) != 0
        assert "Not executable" in capsys.readouterr().err

    def test_approved_run_reaches_engine(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        assert project_init.run_init(str(tmp_path), "roadmaplab") == 0
        target = tmp_path / "roadmaplab"
        roadmap_path = target / "ROADMAP.md"
        roadmap_path.write_text(
            roadmap_path.read_text().replace("Status: DRAFT", "Status: APPROVED"),
            encoding="utf-8",
        )
        monkeypatch.chdir(target)
        calls: list[object] = []

        class FakeClient:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def run(self):
                calls.append("run")
                return object()

        def fake_from_config(plan, *, worker_registry):
            calls.append(plan)
            assert worker_registry is not None
            return FakeClient()

        monkeypatch.setattr(entrypoint.EngineClient, "from_config", fake_from_config)
        monkeypatch.setattr(entrypoint, "format_run", lambda result: "RUN COMPLETE")

        assert entrypoint.main(["run"]) == 0
        assert calls[0].mvp.id == "m1"
        assert calls[1] == "run"

    def test_project_name_with_spaces_produces_valid_manifest(self, tmp_path: Path) -> None:
        exit_code = project_init.run_init(str(tmp_path), "My Project")

        assert exit_code == 0
        target = tmp_path / "My Project"
        manifest = load_project_manifest(target / "aido.yaml")
        assert manifest.project.name == "My Project"
        assert manifest.project.id == "my-project"

    def test_expands_tilde_in_parent_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        exit_code = project_init.run_init("~", "roadmaplab")

        assert exit_code == 0
        assert (tmp_path / "roadmaplab" / "aido.yaml").is_file()


class TestGitMissing:
    def test_scaffold_kept_nonzero_exit_instructions_printed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setattr(project_init.shutil, "which", lambda name: None)

        exit_code = project_init.run_init(str(tmp_path), "roadmaplab")

        assert exit_code != 0
        target = tmp_path / "roadmaplab"
        assert (target / "aido.yaml").is_file()
        assert not (target / ".git").exists()

        err = capsys.readouterr().err
        assert "Git is not installed" in err
        assert "git init -b main" in err
        assert "git add ." in err
        assert 'git commit -m "Initialize AIDO project"' in err


class TestGitStepFailing:
    def test_commit_failure_keeps_scaffold_and_prints_recovery(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
    ) -> None:
        real_run = subprocess.run

        def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess:
            if len(cmd) >= 2 and cmd[1] == "commit":
                raise subprocess.CalledProcessError(1, cmd, output="", stderr="simulated commit failure")
            return real_run(cmd, **kwargs)

        monkeypatch.setattr(project_init.subprocess, "run", fake_run)

        exit_code = project_init.run_init(str(tmp_path), "roadmaplab")

        assert exit_code != 0
        target = tmp_path / "roadmaplab"
        assert (target / "aido.yaml").is_file()
        assert (target / ".git").is_dir()

        err = capsys.readouterr().err
        assert "Git step 'commit' failed" in err
        assert "simulated commit failure" in err
        assert "git commit -m \"Initialize AIDO project\"" in err


class TestNonemptyTarget:
    def test_refused_no_files_touched(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    ) -> None:
        target = tmp_path / "roadmaplab"
        target.mkdir()
        (target / "existing.txt").write_text("keep me")

        exit_code = project_init.run_init(str(tmp_path), "roadmaplab")

        assert exit_code != 0
        assert set(p.name for p in target.iterdir()) == {"existing.txt"}
        assert (target / "existing.txt").read_text() == "keep me"
        err = capsys.readouterr().err
        assert "already exists and is not empty" in err

    def test_existing_empty_directory_is_allowed(self, tmp_path: Path) -> None:
        target = tmp_path / "roadmaplab"
        target.mkdir()

        exit_code = project_init.run_init(str(tmp_path), "roadmaplab")

        assert exit_code == 0
        assert (target / "aido.yaml").is_file()

    def test_symlink_target_refused(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        real_dir = tmp_path / "elsewhere"
        real_dir.mkdir()
        target = tmp_path / "roadmaplab"
        target.symlink_to(real_dir, target_is_directory=True)

        exit_code = project_init.run_init(str(tmp_path), "roadmaplab")

        assert exit_code != 0
        assert not (real_dir / "aido.yaml").exists()
        err = capsys.readouterr().err
        assert "is a symlink" in err


class TestUnsafeProjectName:
    @pytest.mark.parametrize(
        "name",
        [
            "../evil",
            "..",
            ".",
            "a/b",
            "/absolute",
            ".hidden",
            "-leading-hyphen",
            "trailing-dot.",
            "trailing-space ",
        ],
    )
    def test_rejected(self, tmp_path: Path, name: str, capsys: pytest.CaptureFixture[str]) -> None:
        exit_code = project_init.run_init(str(tmp_path), name)

        assert exit_code != 0
        assert list(tmp_path.iterdir()) == []
        err = capsys.readouterr().err
        assert "safe directory name" in err
