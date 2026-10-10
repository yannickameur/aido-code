"""Textual conversational front end: a scrollable log, a docked input line
and a status bar, driving the shared ``repl.dispatch_line`` dispatcher.

Imported only on the interactive TTY path, so the classic loop never loads
Textual. Every dynamic string is shown as a plain ``rich.text.Text`` (never
markup) after passing through ``sanitize_for_terminal``."""

from __future__ import annotations

import io
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Input, Static

from aido_code.i18n import t
from aido_code.repl import ReplState, dispatch_line, sanitize_for_terminal

_KINDS = {"user": "bold cyan", "info": "dim", "error": "bold red", "result": ""}


class Message(Static):
    """One conversation entry, rendered as plain text."""

    def __init__(self, kind: str, text: str) -> None:
        prefix = "> " if kind == "user" else ""
        body = "\n".join(sanitize_for_terminal(line) for line in text.split("\n"))
        super().__init__(Text(prefix + body, style=_KINDS[kind]), markup=False, classes=f"msg-{kind}")


class AidoApp(App[None]):
    CSS = """
    #log { height: 1fr; }
    #status { height: 1; dock: top; background: $boost; padding: 0 1; }
    #prompt { dock: bottom; }
    .msg-user { margin-top: 1; }
    """
    BINDINGS = [
        Binding("ctrl+d", "quit_idle", "Quit", priority=True),
        Binding("pageup", "scroll_log(-1)", show=False),
        Binding("pagedown", "scroll_log(1)", show=False),
    ]

    def __init__(self, state: ReplState, lang: str, **dispatch_kwargs: object) -> None:
        super().__init__()
        self.state = state
        self.lang = lang
        self._dispatch_kwargs = dispatch_kwargs
        self.running = False
        self._history: list[str] = []
        self._cursor = 0

    def compose(self) -> ComposeResult:
        yield Static(Text(""), id="status", markup=False)
        yield VerticalScroll(id="log")
        yield Input(id="prompt", placeholder="/help")

    def on_mount(self) -> None:
        self._refresh_status()
        self.add_message("info", t("help.title", self.lang))
        self.query_one("#prompt", Input).focus()

    # -- status bar ---------------------------------------------------
    def _refresh_status(self) -> None:
        session = self.state.session
        project = "-"
        if session is not None and session.project_path:
            project = Path(session.project_path).name or str(session.project_path)
        session_id = session.session_id if session is not None else "-"
        mode = "running" if self.running else "idle"
        line = f"project: {project} | session: {session_id} | lang: {self.lang} | {mode}"
        self.query_one("#status", Static).update(Text(sanitize_for_terminal(line)))

    # -- conversation log ---------------------------------------------
    def add_message(self, kind: str, text: str) -> None:
        log = self.query_one("#log", VerticalScroll)
        at_bottom = log.scroll_y >= log.max_scroll_y - 1
        log.mount(Message(kind, text))
        if at_bottom:
            log.call_after_refresh(log.scroll_end, animate=False)

    def action_scroll_log(self, direction: int) -> None:
        log = self.query_one("#log", VerticalScroll)
        (log.scroll_page_down if direction > 0 else log.scroll_page_up)(animate=False)

    def action_quit_idle(self) -> None:
        if not self.running:
            self.exit()

    # -- input ----------------------------------------------------------
    def on_key(self, event) -> None:
        if event.key not in ("up", "down") or not self._history:
            return
        prompt = self.query_one("#prompt", Input)
        step = -1 if event.key == "up" else 1
        self._cursor = max(0, min(len(self._history), self._cursor + step))
        prompt.value = self._history[self._cursor] if self._cursor < len(self._history) else ""
        prompt.cursor_position = len(prompt.value)
        event.stop()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        line = event.value
        event.input.value = ""
        if not line.strip() or self.running:
            return
        self._history.append(line)
        self._cursor = len(self._history)
        self.add_message("user", line)
        if line.strip() == "/exit":
            self.exit()
            return
        self.running = True
        self._refresh_status()
        self.run_worker(lambda: self._dispatch(line), thread=True, exclusive=True)

    def _dispatch(self, line: str) -> None:
        out = io.StringIO()
        try:
            keep = dispatch_line(
                line, self.state, io.StringIO(), out, lang=self.lang, **self._dispatch_kwargs
            )
        except Exception as exc:  # surfaced as an error message, never a crash
            out.write(f"Error: {exc}\n")
            keep = True
        self.call_from_thread(self._finish, out.getvalue().rstrip("\n"), keep)

    def _finish(self, text: str, keep: bool) -> None:
        if text:
            self.add_message("error" if text.startswith("Error") else "result", text)
        self.running = False
        self._refresh_status()
        if not keep:
            self.exit()


def run_tui(state: ReplState, lang: str, **dispatch_kwargs: object) -> None:
    AidoApp(state, lang, **dispatch_kwargs).run()
