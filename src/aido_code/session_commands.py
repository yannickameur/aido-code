"""Shared, engine-free session selection for the CLI and REPL."""

from __future__ import annotations

from typing import TextIO

from aido_code.i18n import t
from aido_code.session import Session, SessionStore


def pick_session(
    store: SessionStore, input_stream: TextIO, output_stream: TextIO, *, lang: str = "en",
) -> str | None:
    sessions = store.list()
    if not sessions:
        output_stream.write(t("session.none_found", lang) + "\n")
        return None
    output_stream.write(t("session.list_header", lang) + "\n")
    for number, session in enumerate(sessions, 1):
        project = session.project_path if session.project_path is not None else t("session.no_project", lang)
        output_stream.write(f"  {number}. {session.session_id}  {session.updated_at}  {project}\n")
    output_stream.write(t("session.select_prompt", lang))
    output_stream.flush()
    try:
        choice = input_stream.readline().strip()
    except KeyboardInterrupt:
        output_stream.write("\n" + t("session.cancelled", lang) + "\n")
        return None
    if not choice:
        output_stream.write(t("session.cancelled", lang) + "\n")
        return None
    if not choice.isdecimal() or not 1 <= int(choice) <= len(sessions):
        output_stream.write(t("session.invalid", lang) + "\n")
        return None
    return sessions[int(choice) - 1].session_id


def resume_selected(store: SessionStore, session_id: str) -> Session:
    """The one resume path; SessionStore refreshes updated_at here."""
    return store.resume(session_id)
