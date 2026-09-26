"""Offline coverage for the five-field frontend session store."""

from __future__ import annotations

import json
from dataclasses import fields, replace
from pathlib import Path
from uuid import UUID

import pytest

from aido_code.session import (
    InvalidSessionError,
    Session,
    SessionNotFoundError,
    UnsupportedSessionVersionError,
    create_session,
    load_session,
    save_session,
    session_directory,
)


def test_create_and_round_trip_project_session(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "project"
    project.mkdir()
    session = create_session(project / ".." / "project")
    other = create_session(project)

    assert tuple(field.name for field in fields(Session)) == (
        "schema_version", "session_id", "created_at", "updated_at", "project_path",
    )
    assert str(UUID(session.session_id)) == session.session_id
    assert session.session_id != other.session_id
    assert session.project_path == str(project.resolve())
    assert session.created_at == session.updated_at

    path = save_session(session)
    assert path == tmp_path / "state" / "aido" / "sessions" / f"{session.session_id}.json"
    assert set(json.loads(path.read_text())) == {
        "schema_version", "session_id", "created_at", "updated_at", "project_path",
    }
    assert load_session(session.session_id) == session


def test_unbound_session_and_fallback_location(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert session_directory() == tmp_path / ".local" / "state" / "aido" / "sessions"
    session = create_session()
    assert session.project_path is None
    save_session(session)
    assert load_session(session.session_id) == session


def test_invalid_files_have_controlled_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    session = create_session()
    path = save_session(session)

    path.write_text("{broken", encoding="utf-8")
    with pytest.raises(InvalidSessionError, match="malformed JSON"):
        load_session(session.session_id)

    path.write_text(json.dumps({"schema_version": 42}), encoding="utf-8")
    with pytest.raises(UnsupportedSessionVersionError, match="42"):
        load_session(session.session_id)

    path.write_text(json.dumps({"schema_version": 1, "session_id": session.session_id}), encoding="utf-8")
    with pytest.raises(InvalidSessionError, match="missing fields"):
        load_session(session.session_id)

    extra = json.loads(json.dumps(vars(session)))
    extra["provider_state"] = {"token": "must not persist"}
    path.write_text(json.dumps(extra), encoding="utf-8")
    with pytest.raises(InvalidSessionError, match="unexpected or missing fields"):
        load_session(session.session_id)

    extra.pop("provider_state")
    extra["project_path"] = "/invalid\u0000path"
    path.write_text(json.dumps(extra), encoding="utf-8")
    with pytest.raises(InvalidSessionError, match="project_path"):
        load_session(session.session_id)

    path.unlink()
    with pytest.raises(SessionNotFoundError, match=session.session_id):
        load_session(session.session_id)
    with pytest.raises(InvalidSessionError, match="invalid session id"):
        load_session("../escape")


def test_failed_replace_preserves_old_file_and_cleans_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    session = create_session()
    path = save_session(session)
    original = path.read_bytes()

    def fail_replace(_source: str, _target: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr("aido_code.session.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        save_session(replace(session, updated_at="2026-09-26T00:00:00+00:00"))
    assert path.read_bytes() == original
    assert list(path.parent.iterdir()) == [path]
