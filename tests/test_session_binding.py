"""A resumed session binds commands to its saved path, not the current directory."""

from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from aido_code.project_init import run_init
from aido_code.repl import run
from aido_code.session import Session, SessionStore
from orchestrator.engine import OrchestratorEngine


def _commands(session: Session, commands: str) -> str:
    output = StringIO()
    run(StringIO(commands + "/exit\n"), output, session=session)
    return output.getvalue()


def test_resumed_project_uses_saved_path_and_reads_current_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run_init(str(tmp_path), "bound") == 0
    project = tmp_path / "bound"
    store = SessionStore(tmp_path / "sessions")
    session = store.create(project)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    resumed = store.resume(session.session_id)
    assert resumed.project_path == str(project)
    assert "Configuration is valid." in _commands(resumed, "/validate\n")
    assert "current_milestone_status: DRAFT" in _commands(resumed, "/config\n")

    roadmap = project / "ROADMAP.md"
    roadmap.write_text(roadmap.read_text().replace("Status: DRAFT", "Status: APPROVED"))
    assert "current_milestone_status: APPROVED" in _commands(resumed, "/config\n")


def test_status_after_resume_queries_current_engine_and_roadmap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run_init(str(tmp_path), "bound") == 0
    project = tmp_path / "bound"
    store = SessionStore(tmp_path / "sessions")
    resumed = store.resume(store.create(project).session_id)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    calls = 0
    original_status = OrchestratorEngine.status

    def current_status(self: OrchestratorEngine):
        nonlocal calls
        calls += 1
        return original_status(self)

    monkeypatch.setattr(OrchestratorEngine, "status", current_status)
    first = _commands(resumed, "/status\n")
    assert "current_milestone_status: DRAFT" in first
    assert "NOT_INITIALIZED" in first

    roadmap = project / "ROADMAP.md"
    roadmap.write_text(roadmap.read_text().replace("Status: DRAFT", "Status: APPROVED"))
    second = _commands(resumed, "/status\n")
    assert "current_milestone_status: APPROVED" in second
    assert "NOT_INITIALIZED" in second
    assert calls == 2


def test_resumed_unbound_session_reports_no_project(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    session = store.resume(store.create().session_id)
    assert session.project_path is None
    assert "no project bound" in _commands(session, "/status\n/validate\n/run\n")


def test_deleted_project_keeps_session_resumable_without_rebinding(tmp_path: Path) -> None:
    project = tmp_path / "bound"
    project.mkdir()
    store = SessionStore(tmp_path / "sessions")
    session = store.create(project)
    project.rmdir()
    replacement = tmp_path / "replacement"
    replacement.mkdir()

    resumed = store.resume(session.session_id)
    assert resumed.project_path == str(project)
    output = _commands(resumed, "/workers\n/run\n")
    assert str(project) in output
    assert "bound project is unavailable" in output
    assert "Traceback" not in output


def test_invalid_bound_project_fails_cleanly_and_does_not_search_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert run_init(str(tmp_path), "bound") == 0
    project = tmp_path / "bound"
    store = SessionStore(tmp_path / "sessions")
    created = store.create(project)
    (project / "aido.yaml").write_text("not: a project\n")
    session = store.resume(created.session_id)
    assert run_init(str(tmp_path), "valid_elsewhere") == 0
    monkeypatch.chdir(tmp_path / "valid_elsewhere")

    output = _commands(session, "/config\n/validate\n")
    assert "invalid project manifest" in output
    assert "Configuration is valid." not in output
    assert "Traceback" not in output
