"""Textual conversational front end: a scrollable log, a docked input line
and a status bar, driving the shared ``repl.dispatch_line`` dispatcher.

Imported only on the interactive TTY path, so the classic loop never loads
Textual. Every dynamic string is shown as a plain ``rich.text.Text`` (never
markup) after passing through ``sanitize_for_terminal``."""

from __future__ import annotations

import atexit
import contextlib
import io
import os
import re
import sys
import termios
import threading
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Input, Static
from textual.worker import Worker, WorkerState

from aido_code import repl
from aido_code.i18n import t
from aido_code.intent import Intent, interpret
from aido_code.live_run import render_event, simplified_event_sentence
from aido_code.repl import ReplState, dispatch_line, sanitize_for_terminal
from aido_code.session import project_manifest_path

_KINDS = {
    "user": "bold cyan", "info": "dim", "error": "bold red", "result": "",
    "worker": "dim", "dev": "bold", "qa": "green", "git": "magenta", "warn": "yellow",
}
_SGR = re.compile(r"\x1b\[[0-9;:]*m")
_EVENT_HISTORY_LIMIT = 2000
_PROVIDER_LABELS = {"anthropic": "Claude", "openai": "Codex", "mistral": "Mistral", "gravity": "Gravity"}
_FIVE_HOUR = ("five_hour", "primary_5h")
_SEVEN_DAY = ("seven_day", "secondary_7d")
_DOUBLE_CTRL_C_SECONDS = 2.0
_TERMINAL_RESET = "\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l\x1b[?2004l\x1b[?25h"


def _window_label(window_type: str, lang: str) -> str:
    if window_type in _FIVE_HOUR:
        return "5 h"
    if window_type in _SEVEN_DAY:
        return t("quota.window_7d", lang)
    return window_type


def _local_reset(reset_at: str | None, lang: str) -> str:
    """Local-time reset text, or an explicit unknown value."""
    if reset_at is None:
        return t("quota.reset", lang, when=t("quota.unknown", lang))
    try:
        moment = datetime.fromisoformat(reset_at.replace("Z", "+00:00"))
        when = moment.astimezone().strftime("%d/%m %H:%M")
    except (ValueError, OverflowError, OSError):
        when = reset_at
    return t("quota.reset", lang, when=when)


def format_quota_line(snapshot: object, lang: str) -> str:
    """One panel line from a ``ProviderSnapshot``; only its public facts."""
    provider = str(snapshot.provider)
    label = _PROVIDER_LABELS.get(provider, provider)
    if str(snapshot.reason).startswith("probe_error"):
        return f"{label}: {t('quota.not_available', lang)}"
    if not snapshot.quota_windows:
        return f"{label}: {t('quota.not_reported', lang)}"
    parts = []
    for window in snapshot.quota_windows:
        remaining = window.remaining
        value = f"{round(remaining * 100)} %" if remaining is not None else t("quota.unknown", lang)
        part = f"{_window_label(str(window.window_type), lang)} {value}"
        part += f" ({_local_reset(window.reset_at, lang)})"
        parts.append(part)
    return f"{label}: " + " · ".join(parts)


def format_duration(seconds: float) -> str:
    total = max(0, int(round(seconds)))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours} h {minutes:02d} min {secs:02d} s"
    if minutes:
        return f"{minutes} min {secs:02d} s"
    return f"{secs} s"


def _time_cell(seconds: float | None, executions: int | None, unknown: int, lang: str) -> str:
    if executions == 0:
        return t("times.none", lang)
    cell = t("times.unknown", lang) if seconds is None else format_duration(seconds)
    if unknown > 0:
        cell += f" ({t('times.unknown_executions', lang, count=unknown)})"
    return cell


def format_execution_times(snapshot: object, milestone: str, lang: str) -> str:
    """Table from an engine ``ExecutionTimeSnapshot``; nothing is computed here."""
    by_provider = {str(p.provider): p for p in snapshot.providers}
    order = list(_PROVIDER_LABELS)
    order += sorted(key for key in by_provider if key not in _PROVIDER_LABELS)
    rows = []
    for key in order:
        entry = by_provider.get(key)
        label = _PROVIDER_LABELS.get(key, key)
        if entry is None:
            rows.append((label, t("times.none", lang)))
        else:
            rows.append((label, _time_cell(entry.seconds, entry.executions, entry.unknown_executions, lang)))
    rows.append((t("times.total", lang), _time_cell(
        snapshot.total_seconds, None, snapshot.unknown_executions, lang)))
    head = (t("times.provider", lang), t("times.executed", lang))
    width = max(len(row[0]) for row in (head, *rows))
    lines = [t("times.title", lang, milestone=milestone), f"{head[0]:<{width}} | {head[1]}"]
    lines.append("-" * width + "-+-" + "-" * max(len(row[1]) for row in (head, *rows)))
    lines += [f"{label:<{width}} | {value}" for label, value in rows]
    return "\n".join(lines)


@dataclass
class _LogEntry:
    sequence: int
    kind: str
    detailed: str
    simplified: str | None = None
    widget: Message | None = None


def _event_kind(kind: object) -> str:
    """Display role of a live ``EngineEvent`` from its public ``kind`` only."""
    name = str(kind)
    if name == "execution.output":
        return "worker"
    if name == "execution.output_truncated":
        return "warn"
    if any(word in name for word in ("failed", "error", "blocked")):
        return "error"
    if name.startswith("qa"):
        return "qa"
    if name.startswith(("git", "merge", "commit")) or "commit" in name:
        return "git"
    if name.startswith("dev"):
        return "dev"
    return "result"


def _is_run_request(line: str) -> bool:
    command = line.strip()
    return command == "/run" or (not command.startswith("/") and interpret(command).intent is Intent.RUN)


class Message(Static):
    """One conversation entry, rendered as plain text."""

    def __init__(self, kind: str, text: str) -> None:
        prefix = "> " if kind == "user" else ""
        body = "\n".join(sanitize_for_terminal(line) for line in text.split("\n"))
        super().__init__(Text(prefix + body, style=_KINDS[kind]), markup=False, classes=f"msg-{kind}")


def _plain(kind: str, text: str) -> str:
    """The public text a ``Message`` displays, without styling."""
    prefix = "> " if kind == "user" else ""
    return prefix + "\n".join(sanitize_for_terminal(line) for line in text.split("\n"))


def _export_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    root = Path(base) if base and os.path.isabs(base) else Path.home() / ".local" / "state"
    return root / "aido" / "exports"


class AidoApp(App[None]):
    ALLOW_SELECT = False
    CSS = """
    #log { height: 1fr; }
    #header { height: auto; dock: top; }
    #status { height: 1; background: $boost; padding: 0 1; }
    #quota { height: auto; padding: 0 1; color: $text-muted; }
    #prompt { dock: bottom; }
    .msg-user { margin-top: 1; }
    .msg-worker { padding-left: 2; }
    """
    BINDINGS = [
        Binding("ctrl+c", "interrupt", "Interrupt", priority=True),
        Binding("ctrl+d", "quit_idle", "Quit", priority=True),
        Binding("f10", "quit_idle", "Quit", priority=True),
        Binding("ctrl+o", "toggle_view", "Toggle view", priority=True),
        Binding("ctrl+r", "refresh_quota", "", show=False, priority=True),
        Binding("pageup", "scroll_log(-1)", show=False),
        Binding("pagedown", "scroll_log(1)", show=False),
    ]

    def __init__(self, state: ReplState, lang: str, **dispatch_kwargs: object) -> None:
        super().__init__()
        self.state = state
        self.lang = lang
        self._dispatch_kwargs = dispatch_kwargs
        self.running = False
        self._interrupt: threading.Event | None = None
        self._quit_after = False
        self._active_worker: Worker | None = None
        self._keep_running = True
        self._heartbeat = ""
        self.view = "simplified"
        self._sequence = 0
        self._conversation: list[_LogEntry] = []
        self._event_history: deque[_LogEntry] = deque(maxlen=_EVENT_HISTORY_LIMIT)
        self._history: list[str] = []
        self._cursor = 0
        self._resume_choices: list[str] | None = None
        self._quota_in_flight = False
        self._last_idle_ctrl_c = float('-inf')
        self._evicted = 0
        self._last_times: str | None = None
        self._last_summary: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="header"):
            yield Static(Text(""), id="status", markup=False)
            yield Static(Text(""), id="quota", markup=False)
        yield VerticalScroll(id="log")
        yield Input(id="prompt", placeholder="/help")

    def on_mount(self) -> None:
        self._refresh_status()
        self.add_message("info", t("help.title", self.lang))
        self.query_one("#prompt", Input).focus()
        self.action_refresh_quota()

    # -- quota panel ----------------------------------------------------
    def _set_quota(self, lines: list[str]) -> None:
        text = "\n".join(sanitize_for_terminal(line) for line in lines)
        self.query_one("#quota", Static).update(Text(text))

    def action_refresh_quota(self) -> None:
        if self._quota_in_flight:
            return
        self._quota_in_flight = True
        self._set_quota([t("quota.refreshing", self.lang)])
        self.run_worker(self._probe_quota, thread=True, group="quota", exit_on_error=False)

    def _probe_quota(self) -> None:
        """Thread worker: one real probe; any failure renders "not available"."""
        lines: list[str] | None = None
        try:
            session = self.state.session
            if session is not None and session.project_path:
                config_path = str(project_manifest_path(session))
                _context, client = repl._open_project_command_engine(config_path)
                with client:
                    providers = client.probe_workers()
                lines = [format_quota_line(p, self.lang) for p in sorted(providers, key=lambda p: p.provider)]
        except Exception:
            lines = None
        if lines is None:
            lines = [t("quota.not_available", self.lang)]
        elif not lines:
            lines = [t("quota.not_reported", self.lang)]
        self.call_from_thread(self._finish_quota, lines)

    def _finish_quota(self, lines: list[str]) -> None:
        self._quota_in_flight = False
        self._set_quota(lines)

    # -- execution time summary ------------------------------------------
    def _load_times(self) -> str:
        """Read the engine snapshot after its run, before accepting another command."""
        try:
            session = self.state.session
            if session is not None and session.project_path:
                _context, client = repl._open_project_command_engine(str(project_manifest_path(session)))
            else:
                client = repl.EngineClient.open(self.state.config_path)
            with client:
                snapshot = client.execution_times()
            return format_execution_times(snapshot, snapshot.mvp_id, self.lang)
        except Exception:
            return t("times.unavailable", self.lang)

    # -- export -------------------------------------------------------
    def _export(self) -> None:
        session = self.state.session
        session_id = session.session_id if session is not None else "no-session"
        now = datetime.now(timezone.utc)
        stamp = now.strftime("%Y%m%dT%H%M%SZ")
        lang = self.lang
        entries = sorted((*self._conversation, *self._event_history), key=lambda entry: entry.sequence)
        lines = [t("export.header", lang, session_id=sanitize_for_terminal(session_id), timestamp=stamp)]
        if self._evicted:
            lines.append(t("export.evicted", lang, count=self._evicted))
        lines += ["", t("export.conversation", lang)]
        lines += [_plain(entry.kind, entry.detailed) for entry in entries]
        for key, value in (("export.times", self._last_times), ("export.summary", self._last_summary)):
            if value is not None:
                lines += ["", t(key, lang), _plain("result", value)]
        try:
            directory = _export_dir()
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / f"{session_id}-{stamp}.txt"
            counter = 1
            while True:
                try:
                    handle = open(path, "x", encoding="utf-8")
                    break
                except FileExistsError:
                    counter += 1
                    path = directory / f"{session_id}-{stamp}-{counter}.txt"
            with handle:
                handle.write("\n".join(lines) + "\n")
        except (OSError, ValueError) as exc:
            self.add_message("error", t("export.error", lang, error=exc))
            return
        self.add_message("info", t("export.done", lang, path=path))

    # -- status bar ---------------------------------------------------
    def _refresh_status(self) -> None:
        session = self.state.session
        project = "-"
        if session is not None and session.project_path:
            project = Path(session.project_path).name or str(session.project_path)
        session_id = session.session_id if session is not None else "-"
        mode = t("status.running" if self.running else "status.idle", self.lang)
        line = (
            f"{t('status.project', self.lang)}: {project} | "
            f"{t('status.session', self.lang)}: {session_id} | "
            f"{t('status.language', self.lang)}: {self.lang} | "
            f"{t('status.view', self.lang)}: {t(f'view.{self.view}', self.lang)} | {mode}"
        )
        if self.running and self._heartbeat:
            line += f" | {self._heartbeat}"
        self.query_one("#status", Static).update(Text(sanitize_for_terminal(line)))

    # -- conversation log ---------------------------------------------
    def add_message(self, kind: str, text: str) -> None:
        entry = _LogEntry(self._sequence, kind, text, text)
        self._sequence += 1
        self._conversation.append(entry)
        self._mount_entry(entry)

    def _mount_entry(self, entry: _LogEntry) -> None:
        text = entry.simplified if self.view == "simplified" else entry.detailed
        if text is None:
            entry.widget = None
            return
        log = self.query_one("#log", VerticalScroll)
        at_bottom = log.scroll_y >= log.max_scroll_y - 1
        entry.widget = Message(entry.kind, text)
        log.mount(entry.widget)
        if at_bottom:
            log.call_after_refresh(log.scroll_end, animate=False)

    def _add_live_event(self, kind: str, simplified: str | None, detailed: str) -> None:
        if len(self._event_history) == _EVENT_HISTORY_LIMIT:
            oldest = self._event_history.popleft()
            self._evicted += 1
            if oldest.widget is not None:
                oldest.widget.remove()
        entry = _LogEntry(self._sequence, kind, detailed, simplified)
        self._sequence += 1
        self._event_history.append(entry)
        self._mount_entry(entry)

    def action_toggle_view(self) -> None:
        log = self.query_one("#log", VerticalScroll)
        at_bottom = log.scroll_y >= log.max_scroll_y - 1
        previous_y = log.scroll_y
        self.view = "detailed" if self.view == "simplified" else "simplified"
        log.remove_children()
        entries = sorted((*self._conversation, *self._event_history), key=lambda entry: entry.sequence)
        widgets = []
        for entry in entries:
            text = entry.simplified if self.view == "simplified" else entry.detailed
            entry.widget = Message(entry.kind, text) if text is not None else None
            if entry.widget is not None:
                widgets.append(entry.widget)
        if widgets:
            log.mount(*widgets)
        if at_bottom:
            log.call_after_refresh(log.scroll_end, animate=False)
        else:
            log.call_after_refresh(log.scroll_to, y=previous_y, animate=False)
        self._refresh_status()

    def action_scroll_log(self, direction: int) -> None:
        log = self.query_one("#log", VerticalScroll)
        (log.scroll_page_down if direction > 0 else log.scroll_page_up)(animate=False)

    def _request_interrupt(self) -> None:
        if self._interrupt is not None and not self._interrupt.is_set():
            self._interrupt.set()
            self.add_message("info", t("run.interrupt_requested", self.lang))

    def action_interrupt(self) -> None:
        if self._interrupt is not None:
            self._request_interrupt()
        elif not self.running:
            prompt = self.query_one("#prompt", Input)
            now = time.monotonic()
            if prompt.value:
                prompt.value = ""
                self._last_idle_ctrl_c = float("-inf")
                self.add_message("info", t("run.idle_ctrl_c", self.lang))
            elif now - self._last_idle_ctrl_c <= _DOUBLE_CTRL_C_SECONDS:
                self.exit()
            else:
                self._last_idle_ctrl_c = now
                self.add_message("info", t("run.ctrl_c_again", self.lang))

    def action_quit_idle(self) -> None:
        if not self.running:
            self.exit()
        elif self._interrupt is not None:
            self._quit_after = True
            self._request_interrupt()

    async def action_quit(self) -> None:
        self.action_quit_idle()

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
        if not line.strip():
            return
        event.input.value = ""
        if line.strip() == "/quit":
            line = "/exit"
        if line.strip() == "/export":
            self.add_message("user", line)
            self._export()
            return
        if self.running:
            if line.strip() == "/exit" and self._interrupt is not None:
                self._quit_after = True
                self._request_interrupt()
            else:
                self.add_message("info", t("run.busy", self.lang))
            return
        self._history.append(line)
        self._cursor = len(self._history)
        self.add_message("user", line)
        if line.strip() == "/exit":
            self._resume_choices = None
        elif self._resume_choices is not None:
            choices, self._resume_choices = self._resume_choices, None
            if line.strip().isdecimal() and 1 <= int(line.strip()) <= len(choices):
                line = f"/resume {choices[int(line.strip()) - 1]}"
            else:
                self.add_message("error", t("session.invalid", self.lang))
                return
        elif line.strip() == "/resume":
            sessions = self.state.store.list()
            if not sessions:
                self.add_message("info", t("session.none_found", self.lang))
                return
            self._resume_choices = [session.session_id for session in sessions]
            lines = [t("session.list_header", self.lang)]
            for number, session in enumerate(sessions, 1):
                project = session.project_path or t("session.no_project", self.lang)
                lines.append(f"  {number}. {session.session_id}  {session.updated_at}  {project}")
            lines.append(t("session.select_prompt", self.lang))
            self.add_message("info", "\n".join(lines))
            return
        self.running = True
        kwargs = dict(self._dispatch_kwargs)
        if _is_run_request(line):
            self._interrupt = threading.Event()
            kwargs.update(interrupt=self._interrupt, event_sink=self._on_event, show_run_start=False)
            self.add_message("info", t("run.start", self.lang))
        self._refresh_status()
        self._active_worker = self.run_worker(lambda: self._dispatch(line, kwargs), thread=True, exclusive=True)

    def _on_event(self, event: object) -> None:
        """Engine-thread sink: renders public event fields and hands them to the UI loop."""
        try:
            if getattr(event, "kind", None) == "execution.output":
                payload = getattr(event, "payload", None)
                payload = payload if isinstance(payload, dict) else {}
                stream = payload.get("stream")
                label = sanitize_for_terminal(stream) if stream is not None else "output"
                output = payload.get("text")
                output = "" if output is None else str(output)
                text = f"    [{label}] {_SGR.sub('', output).replace(chr(13) + chr(10), chr(10))}"
            else:
                text = render_event(event, lang=self.lang).strip("\n")
        except Exception:
            text = "[unrenderable event]"
        kind = getattr(event, "kind", None)
        simple = simplified_event_sentence(event, lang=self.lang)
        if simple is None and _event_kind(kind) == "error":
            simple = text
        if kind == "execution.heartbeat":
            self.call_from_thread(self._set_heartbeat, text.strip())
        self.call_from_thread(self._add_live_event, _event_kind(kind), simple, text)

    def _set_heartbeat(self, text: str) -> None:
        self._heartbeat = text
        self._refresh_status()

    def _dispatch(self, line: str, kwargs: dict[str, object]) -> None:
        out = io.StringIO()
        try:
            keep = dispatch_line(line, self.state, io.StringIO(), out, lang=self.lang, **kwargs)
        except Exception as exc:  # surfaced as an error message, never a crash
            out.write(f"Error: {exc}\n")
            keep = True
        times = self._load_times() if _is_run_request(line) else None
        self.call_from_thread(self._finish, line, out.getvalue().rstrip("\n"), keep, times)

    def _finish(self, line: str, text: str, keep: bool, times: str | None) -> None:
        if line.strip() == "/help":
            text += f"\n  Ctrl+O - {t('help.toggle_view', self.lang)}"
            text += f"\n  Ctrl+R - {t('help.refresh_quota', self.lang)}"
            text += f"\n  /quit - {t('help.cmd./quit', self.lang)}"
            text += f"\n  Ctrl+D, F10 - {t('help.quit_keys', self.lang)}"
            text += f"\n  Ctrl+C - {t('help.ctrl_c', self.lang)}"
            text += f"\n  /export - {t('help.cmd./export', self.lang)}"
            text += f"\n  Shift+drag - {t('help.select', self.lang)}"
        if text:
            kind = "error" if text.startswith(("Error", "Validation failed")) else (
                "info" if line.startswith(("/help", "/new", "/resume")) else "result"
            )
            self.add_message(kind, text)
        if _is_run_request(line):
            self._last_summary = text or None
        if times is not None:
            self._last_times = times
            self.add_message("result", times)
        self._keep_running = keep

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker is not self._active_worker or event.state not in (
            WorkerState.SUCCESS, WorkerState.ERROR,
        ):
            return
        self._active_worker = None
        self.running = False
        self._interrupt = None
        self._heartbeat = ""
        self._refresh_status()
        if self._quit_after or not self._keep_running:
            self.exit()


class _TerminalGuard:
    """Owns the real terminal while the app runs; restores it exactly once."""

    def __init__(self, private_fd: int, saved: list | None, devnull: int,
                 reader: io.TextIOWrapper, previous: tuple[object, object]) -> None:
        self.private_fd = private_fd
        self.saved = saved
        self.devnull = devnull
        self.reader = reader
        self.previous = previous
        self.restored = False

    def restore(self) -> None:
        if self.restored:
            return
        self.restored = True
        if self.saved is not None:
            with contextlib.suppress(termios.error, OSError, ValueError):
                termios.tcsetattr(self.private_fd, termios.TCSANOW, self.saved)
        for stream in (sys.__stdout__, sys.__stderr__):
            try:
                stream.write(_TERMINAL_RESET)
                stream.flush()
                break
            except (AttributeError, OSError, ValueError):
                continue
        try:
            os.dup2(self.private_fd, 0)
        finally:
            sys.__stdin__, sys.stdin = self.previous
            self.reader.close()
            os.close(self.devnull)
            os.close(self.private_fd)


@contextlib.contextmanager
def isolated_terminal() -> Iterator[None]:
    """Give Textual a private copy of the terminal and point fd 0 to /dev/null,
    so worker processes inheriting stdin can never alter the terminal modes."""
    private_fd = os.dup(0)  # non-inheritable
    try:
        saved = termios.tcgetattr(private_fd)
    except (termios.error, OSError):
        saved = None
    reader = os.fdopen(private_fd, "r", closefd=False)
    previous = sys.__stdin__, sys.stdin
    devnull = os.open(os.devnull, os.O_RDONLY)
    guard = _TerminalGuard(private_fd, saved, devnull, reader, previous)
    atexit.register(guard.restore)
    try:
        os.dup2(devnull, 0)
        sys.__stdin__ = sys.stdin = reader
        yield
    finally:
        try:
            guard.restore()
        finally:
            atexit.unregister(guard.restore)


def run_tui(state: ReplState, lang: str, **dispatch_kwargs: object) -> None:
    with isolated_terminal():
        AidoApp(state, lang, **dispatch_kwargs).run()
