"""Offline coverage for the five-field frontend session store."""

from __future__ import annotations

import json
from dataclasses import fields, replace
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from aido_code.session import (
    InvalidSessionError,
    Session,
    SessionNotFoundError,
    SessionStore,
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


def test_saved_project_path_survives_filesystem_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    project = tmp_path / "project"
    project.mkdir()
    session = create_session(project)
    save_session(session)

    project.rename(tmp_path / "moved")
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    project.symlink_to(replacement, target_is_directory=True)

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


def test_store_create_list_latest_and_resume(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    assert store.list() == []
    assert store.latest() is None
    assert not store.directory.exists()

    first = store.create()
    second = store.create(tmp_path)
    assert store.load(first.session_id) == first
    assert second.project_path == str(tmp_path.resolve())
    assert first.created_at == first.updated_at
    assert second.created_at == second.updated_at

    old = "2020-01-01T00:00:00+00:00"
    newer = "2021-01-01T00:00:00+00:00"
    store.save(replace(first, updated_at=old))
    store.save(replace(second, updated_at=newer))
    assert [session.session_id for session in store.list()] == [second.session_id, first.session_id]
    assert store.latest().session_id == second.session_id

    resumed = store.resume(first.session_id)
    assert resumed.created_at == first.created_at
    assert datetime.fromisoformat(resumed.updated_at) > datetime.fromisoformat(newer)
    assert store.load(first.session_id) == resumed
    assert store.latest() == resumed


def test_latest_breaks_timestamp_ties_by_id(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    first = store.create()
    second = store.create()
    same = "2026-01-01T00:00:00+00:00"
    store.save(replace(first, updated_at=same))
    store.save(replace(second, updated_at=same))

    assert [item.session_id for item in store.list()] == sorted(
        [first.session_id, second.session_id], reverse=True,
    )
    assert store.latest().session_id == max(first.session_id, second.session_id)


def test_listing_ignores_other_filenames_and_reports_corruption(tmp_path: Path) -> None:
    store = SessionStore(tmp_path)
    valid = store.create()
    (tmp_path / "index.json").write_text("{broken", encoding="utf-8")
    (tmp_path / f"{valid.session_id}.json.bak").write_text("{broken", encoding="utf-8")
    (tmp_path / f"{str(uuid4()).upper()}.json").write_text("{broken", encoding="utf-8")
    assert store.list() == [valid]

    corrupt_id = str(uuid4())
    corrupt = tmp_path / f"{corrupt_id}.json"
    corrupt.write_text("{broken", encoding="utf-8")
    with pytest.raises(InvalidSessionError, match=corrupt_id):
        store.list()
    assert corrupt.read_text(encoding="utf-8") == "{broken"


def test_resume_rejects_invalid_and_missing_ids_without_creating_files(tmp_path: Path) -> None:
    store = SessionStore(tmp_path / "sessions")
    with pytest.raises(InvalidSessionError, match="invalid session id"):
        store.resume("../escape")
    missing = str(uuid4())
    with pytest.raises(SessionNotFoundError, match=missing):
        store.resume(missing)
    assert not store.directory.exists()


def test_resume_preserves_file_on_failed_save(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = SessionStore(tmp_path)
    session = store.create()
    path = tmp_path / f"{session.session_id}.json"
    original = path.read_bytes()

    def fail_replace(_source: str, _target: Path) -> None:
        raise OSError("simulated replace failure")

    monkeypatch.setattr("aido_code.session.os.replace", fail_replace)
    with pytest.raises(OSError, match="simulated replace failure"):
        store.resume(session.session_id)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]
