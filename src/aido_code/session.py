"""Minimal, versioned frontend session state and its local JSON store."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

__all__ = [
    "SESSION_SCHEMA_VERSION",
    "Session",
    "SessionError",
    "InvalidSessionError",
    "UnsupportedSessionVersionError",
    "SessionNotFoundError",
    "create_session",
    "session_directory",
    "save_session",
    "load_session",
]

SESSION_SCHEMA_VERSION = 1
_SESSION_FIELDS = frozenset({
    "schema_version", "session_id", "created_at", "updated_at", "project_path",
})


class SessionError(Exception):
    """Base error for session persistence."""


class InvalidSessionError(SessionError):
    """The session data or identifier is malformed."""


class UnsupportedSessionVersionError(SessionError):
    """The file uses a schema this version of AIDO Code cannot read."""


class SessionNotFoundError(SessionError):
    """No session file exists for the requested identifier."""


@dataclass(frozen=True)
class Session:
    schema_version: int
    session_id: str
    created_at: str
    updated_at: str
    project_path: str | None = None


def _valid_id(session_id: str) -> str:
    try:
        if not isinstance(session_id, str) or str(UUID(session_id)) != session_id:
            raise ValueError("noncanonical UUID")
    except (ValueError, AttributeError) as exc:
        raise InvalidSessionError(f"invalid session id {session_id!r}") from exc
    return session_id


def _validate(session: Session) -> None:
    if type(session.schema_version) is not int or session.schema_version != SESSION_SCHEMA_VERSION:
        raise UnsupportedSessionVersionError(
            f"unsupported session schema_version {session.schema_version!r}"
        )
    _valid_id(session.session_id)
    for field in ("created_at", "updated_at"):
        value = getattr(session, field)
        try:
            if not isinstance(value, str) or datetime.fromisoformat(value).tzinfo is None:
                raise ValueError("timestamp must include a timezone")
        except ValueError as exc:
            raise InvalidSessionError(f"invalid session {field}: {value!r}") from exc
    if session.project_path is not None:
        if not isinstance(session.project_path, str) or not Path(session.project_path).is_absolute():
            raise InvalidSessionError("session project_path must be an absolute path or null")
        if "\x00" in session.project_path or os.path.normpath(session.project_path) != session.project_path:
            raise InvalidSessionError("session project_path must be normalized")


def create_session(project_path: str | Path | None = None) -> Session:
    """Create an unbound session or bind one to a project root directory."""
    now = datetime.now(timezone.utc).isoformat()
    root = str(Path(project_path).expanduser().resolve()) if project_path is not None else None
    return Session(SESSION_SCHEMA_VERSION, str(uuid4()), now, now, root)


def session_directory() -> Path:
    """Return the XDG state location, without creating it."""
    state_home = os.environ.get("XDG_STATE_HOME")
    base = Path(state_home) if state_home else Path.home() / ".local" / "state"
    return base.expanduser() / "aido" / "sessions"


def save_session(session: Session) -> Path:
    """Atomically replace this session's JSON file with its five fields."""
    _validate(session)
    directory = session_directory()
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{session.session_id}.json"
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=directory, prefix=f".{session.session_id}.",
            suffix=".tmp", delete=False,
        ) as handle:
            temporary = handle.name
            json.dump(asdict(session), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
    return target


def load_session(session_id: str) -> Session:
    """Read one session; reject malformed or unsupported files explicitly."""
    _valid_id(session_id)
    source = session_directory() / f"{session_id}.json"
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SessionNotFoundError(f"unknown session {session_id}") from exc
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise InvalidSessionError(f"invalid session {session_id}: malformed JSON") from exc
    if not isinstance(data, dict):
        raise InvalidSessionError(f"invalid session {session_id}: expected a JSON object")
    if type(data.get("schema_version")) is not int or data["schema_version"] != SESSION_SCHEMA_VERSION:
        raise UnsupportedSessionVersionError(
            f"unsupported session schema_version {data.get('schema_version')!r} in {session_id}"
        )
    if data.keys() != _SESSION_FIELDS:
        raise InvalidSessionError(f"invalid session {session_id}: unexpected or missing fields")
    session = Session(**data)
    _validate(session)
    if session.session_id != session_id:
        raise InvalidSessionError(f"invalid session {session_id}: id does not match filename")
    return session
