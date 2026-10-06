"""Graceful Ctrl+C for the shared ``aido run`` / ``/run`` path. Offline:
KeyboardInterrupt is simulated; no provider is ever called."""

from __future__ import annotations

import io
from types import SimpleNamespace

from aido_code import __main__ as entrypoint
from aido_code import repl
from aido_code.live_run import INTERRUPTED_NOTICE, LiveRunRenderer, run_interruptibly


class _InterruptedClient:
    def __init__(self, events=()):
        self.events = events

    def run(self, *, on_event=None, **_):
        for event in self.events:
            on_event(event)
        raise KeyboardInterrupt

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _events():
    return [
        SimpleNamespace(kind="execution.output", work_item_id="WI-1", payload={"stream": "stdout", "text": "partial"}),
        SimpleNamespace(kind="run.interruption_requested", work_item_id=None, payload={}),
        SimpleNamespace(kind="qa.interrupted", work_item_id="WI-1", payload={}),
        SimpleNamespace(kind="run.interrupted", work_item_id=None, payload={}),
    ]


def test_run_interruptibly_returns_none_and_keeps_rendered_output():
    out = io.StringIO()
    assert run_interruptibly(_InterruptedClient(_events()), LiveRunRenderer(out)) is None
    text = out.getvalue()
    for needle in ("[stdout] partial", "[run.interruption_requested]", "[qa.interrupted] WI-1", "[run.interrupted]"):
        assert needle in text


def test_notice_states_engine_recovery_and_session_only_resume():
    assert "next `aido run`" in INTERRUPTED_NOTICE
    assert "engine state" in INTERRUPTED_NOTICE
    assert "only reopen a session" in INTERRUPTED_NOTICE


def test_repl_session_run_reports_notice_without_traceback(monkeypatch):
    monkeypatch.setattr(repl, "load_project_command_context", lambda path: SimpleNamespace(
        roadmap=SimpleNamespace(milestone=SimpleNamespace(is_executable=True)),
        manifest=None, resources=None, worker_registry=None))
    monkeypatch.setattr(repl, "build_engine_plan", lambda *a: None)
    monkeypatch.setattr(repl.EngineClient, "from_config", classmethod(lambda cls, *a, **k: _InterruptedClient(_events())))
    out = io.StringIO()
    result = repl._run_session_project("aido.yaml", output_stream=out)
    assert result == INTERRUPTED_NOTICE
    assert "[stdout] partial" in out.getvalue()
    assert "Traceback" not in result


def test_repl_legacy_run_reports_notice(monkeypatch):
    monkeypatch.setattr(repl.EngineClient, "open", classmethod(lambda cls, *a, **k: _InterruptedClient()))
    assert repl._run_run("aido.yaml", output_stream=io.StringIO()) == INTERRUPTED_NOTICE


def test_cli_run_exits_130_with_notice(monkeypatch, capsys):
    monkeypatch.setattr(entrypoint, "load_project_command_context", lambda path: SimpleNamespace(
        roadmap=SimpleNamespace(milestone=SimpleNamespace(is_executable=True)),
        manifest=None, resources=None, worker_registry=None))
    monkeypatch.setattr(entrypoint, "build_engine_plan", lambda *a: None)
    monkeypatch.setattr(entrypoint.EngineClient, "from_config", classmethod(lambda cls, *a, **k: _InterruptedClient(_events())))
    assert entrypoint._project_command("run") == 130
    captured = capsys.readouterr()
    assert "[run.interrupted]" in captured.out
    assert INTERRUPTED_NOTICE in captured.err
    assert "Traceback" not in captured.err
