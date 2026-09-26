"""Shared, engine-free session selection for the CLI and REPL."""

from __future__ import annotations

from typing import TextIO

from aido_code.session import Session, SessionStore


def pick_session(store: SessionStore, input_stream: TextIO, output_stream: TextIO) -> str | None:
    sessions = store.list()
    if not sessions:
        output_stream.write("No sessions found.\n")
        return None
    output_stream.write("Sessions (most recently used first):\n")
    for number, session in enumerate(sessions, 1):
        project = session.project_path if session.project_path is not None else "(no project)"
        output_stream.write(f"  {number}. {session.session_id}  {session.updated_at}  {project}\n")
    output_stream.write("Select a session number (blank to cancel): ")
    output_stream.flush()
    choice = input_stream.readline().strip()
    if not choice:
        output_stream.write("Session selection cancelled.\n")
        return None
    if not choice.isdecimal() or not 1 <= int(choice) <= len(sessions):
        output_stream.write("Invalid session selection.\n")
        return None
    return sessions[int(choice) - 1].session_id


def resume_selected(store: SessionStore, session_id: str) -> Session:
    """The one resume path; SessionStore refreshes updated_at here."""
    return store.resume(session_id)
