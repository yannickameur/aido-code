"""Session commands select and switch frontend state without running an engine."""

from __future__ import annotations

from datetime import datetime
from io import StringIO
from pathlib import Path

import pytest

from aido_code import __main__ as entrypoint
from aido_code.repl import run
from aido_code.session import SessionStore


@pytest.fixture
def isolated_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SessionStore:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return SessionStore()


def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("session command called the engine")

    monkeypatch.setattr("aido_code.engine_client.EngineClient.run", forbidden)
    monkeypatch.setattr("aido_code.engine_client.EngineClient.probe_workers", forbidden)


def test_cli_resume_by_id_and_continue_refresh_timestamp(
    isolated_store: SessionStore, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    _offline(monkeypatch)
    first = isolated_store.create()
    second = isolated_store.create()
    monkeypatch.setattr(entrypoint.sys, "stdin", StringIO("/exit\n"))
    assert entrypoint.main(["resume", first.session_id]) == 0
    refreshed = isolated_store.load(first.session_id)
    assert datetime.fromisoformat(refreshed.updated_at) > datetime.fromisoformat(first.updated_at)
    assert isolated_store.latest().session_id == first.session_id
    assert isolated_store.load(second.session_id) == second
    monkeypatch.setattr(entrypoint.sys, "stdin", StringIO("/exit\n"))
    assert entrypoint.main(["-c"]) == 0
    monkeypatch.setattr(entrypoint.sys, "stdin", StringIO("/exit\n"))
    assert entrypoint.main(["--continue"]) == 0
    assert first.session_id in capsys.readouterr().out


def test_cli_picker_sorted_and_empty_paths(
    isolated_store: SessionStore, monkeypatch: pytest.MonkeyPatch, capsys,
) -> None:
    _offline(monkeypatch)
    monkeypatch.setattr(entrypoint.sys, "stdin", StringIO(""))
    assert entrypoint.main(["resume"]) == 0
    assert "No sessions found" in capsys.readouterr().out
    assert entrypoint.main(["--continue"]) == 1
    assert "no sessions found" in capsys.readouterr().err
    assert isolated_store.list() == []
    first = isolated_store.create()
    second = isolated_store.create()
    monkeypatch.setattr(entrypoint.sys, "stdin", StringIO("2\n/exit\n"))
    assert entrypoint.main(["resume"]) == 0
    output = capsys.readouterr().out
    assert output.index(second.session_id) < output.index(first.session_id)
    assert first.updated_at in output
    assert isolated_store.latest().session_id == first.session_id


def test_repl_new_and_resume_switch_without_changing_previous(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _offline(monkeypatch)
    store = SessionStore(tmp_path / "sessions")
    project = tmp_path / "project"
    project.mkdir()
    first = store.create(project)
    output = StringIO()
    run(StringIO("/new\n/resume\n1\n/exit\n"), output, session=first, session_store=store)
    sessions = store.list()
    assert len(sessions) == 2
    assert all(item.project_path == str(project) for item in sessions)
    assert store.load(first.session_id) == first
    assert "Created session" in output.getvalue()
    assert "Resumed session" in output.getvalue()


def test_repl_new_without_project_and_invalid_picker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    store = SessionStore(tmp_path / "sessions")
    output = StringIO()
    run(StringIO("/resume\n/new\n/resume\n9\n/exit\n"), output, session_store=store)
    assert "No sessions found" in output.getvalue()
    assert "Invalid session selection" in output.getvalue()
    assert len(store.list()) == 1
    assert store.latest().project_path is None
