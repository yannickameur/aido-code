"""Offline tests for live runs in the Textual interface: fake engine
client, no provider is ever called."""

from __future__ import annotations

import asyncio
import threading
from types import SimpleNamespace

from orchestrator.engine import RunResult

from aido_code import repl
from aido_code.engine_client import EngineClient, EngineCompatibilityError
from aido_code.i18n import t
from aido_code.live_run import INTERRUPTED_NOTICE
from aido_code.repl import ReplState
from aido_code.session import SessionStore
from aido_code.tui import AidoApp, Message

SENTINEL = "PRIVATE-REASONING-SENTINEL"


def _ev(kind, **payload):
    return SimpleNamespace(
        kind=kind, work_item_id="WI-1", payload=payload, worker_display_name="Worker A",
        private_reasoning=SENTINEL,
    )


class FakeClient:
    """Streams events, then blocks until released or interrupted."""

    instances: list["FakeClient"] = []

    def __init__(self, release: threading.Event) -> None:
        self.release = release
        self.first_event = threading.Event()
        self.interrupt = None
        self.calls = 0
        FakeClient.instances.append(self)

    def run(self, *, on_event=None, interrupt=None, **_):
        self.calls += 1
        self.interrupt = interrupt
        on_event(_ev("dev_a.started"))
        on_event(_ev("execution.output", stream="stdout", text="hello from worker"))
        on_event(_ev("execution.heartbeat", elapsed_seconds=7))
        on_event(_ev("execution.output_truncated", reason="limit", delivered_events=1, delivered_chars=5))
        self.first_event.set()
        while not self.release.is_set():
            if interrupt is not None and interrupt.is_set():
                on_event(_ev("run.interrupted"))
                raise KeyboardInterrupt
            self.release.wait(0.01)
        on_event(_ev("qa.passed"))
        return RunResult(1, True, False, ())

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


def _app(tmp_path, monkeypatch, release):
    FakeClient.instances.clear()
    monkeypatch.setattr(repl.EngineClient, "open", classmethod(lambda cls, *a, **k: FakeClient(release)))
    return AidoApp(ReplState(store=SessionStore(tmp_path / "sessions")), "en")


def _texts(app):
    return [str(m.render()) for m in app.query(Message)]


async def _type(pilot, text):
    for ch in text:
        await pilot.press("slash" if ch == "/" else "space" if ch == " " else ch)
    await pilot.press("enter")
    await pilot.pause()


async def _until(pilot, cond, tries=200):
    for _ in range(tries):
        if cond():
            return
        await pilot.pause(0.02)
    raise AssertionError("condition not reached")


def test_progressive_display_responsive_and_busy_refusal(tmp_path, monkeypatch):
    release = threading.Event()

    async def go():
        app = _app(tmp_path, monkeypatch, release)
        async with app.run_test(size=(100, 30)) as pilot:
            await _type(pilot, "/run")
            await _until(pilot, lambda: any("hello from worker" in m for m in _texts(app)))
            assert app.running and not release.is_set()  # shown before the run completes
            texts = _texts(app)
            assert any("dev_a.started" in m and "Worker A" in m for m in texts)
            assert any("output truncated" in m for m in texts)
            assert not any("still running" in m for m in texts)  # heartbeat is not a line
            assert "still running" in str(app.query_one("#status").render())
            worker = [m for m in app.query(Message) if "hello from worker" in str(m.render())][0]
            assert worker.has_class("msg-worker")
            # responsive: history and other commands refused, no concurrent engine work
            await _type(pilot, "/status")
            assert t("run.busy", "en") in _texts(app)
            assert len(FakeClient.instances) == 1
            await pilot.press("pageup")
            release.set()
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert not app.running
            assert any("qa.passed" in m for m in _texts(app))
            assert not any(SENTINEL in m for m in _texts(app))
            assert not any(SENTINEL in str(app.query_one("#status").render()) for _ in (0,))
    try:
        asyncio.run(go())
    finally:
        release.set()


def test_ctrl_c_interrupts_once_waits_then_next_run_unchanged(tmp_path, monkeypatch):
    release = threading.Event()

    async def go():
        app = _app(tmp_path, monkeypatch, release)
        async with app.run_test(size=(100, 30)) as pilot:
            await _type(pilot, "/run")
            await _until(pilot, lambda: FakeClient.instances and FakeClient.instances[0].first_event.is_set())
            await pilot.press("ctrl+c")
            await pilot.press("ctrl+c")
            await app.workers.wait_for_complete()
            await pilot.pause()
            texts = _texts(app)
            assert texts.count(t("run.interrupt_requested", "en")) == 1
            assert FakeClient.instances[0].interrupt.is_set()
            assert any("run.interrupted" in m for m in texts)
            assert INTERRUPTED_NOTICE in texts and not app.running
            assert texts.index(INTERRUPTED_NOTICE) > max(i for i, m in enumerate(texts) if "run.interrupted" in m)
            # next run delegated unchanged: fresh client and fresh, unset interrupt
            release.set()
            await _type(pilot, "run the project")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert len(FakeClient.instances) == 2
            assert FakeClient.instances[1].interrupt is not FakeClient.instances[0].interrupt
            assert not FakeClient.instances[1].interrupt.is_set()
            assert not any(SENTINEL in m for m in _texts(app))
    try:
        asyncio.run(go())
    finally:
        release.set()


def test_quit_during_run_requests_interruption_and_waits(tmp_path, monkeypatch):
    release = threading.Event()

    async def go():
        app = _app(tmp_path, monkeypatch, release)
        async with app.run_test() as pilot:
            await _type(pilot, "/run")
            await _until(pilot, lambda: FakeClient.instances and FakeClient.instances[0].first_event.is_set())
            await pilot.press("ctrl+d")
            assert FakeClient.instances[0].interrupt.is_set()
            await app.workers.wait_for_complete()
            await pilot.pause()
            await pilot.pause()
            assert app._exit
    try:
        asyncio.run(go())
    finally:
        release.set()


def test_ctrl_c_idle_clears_input_and_reminds(tmp_path, monkeypatch):
    async def go():
        app = _app(tmp_path, monkeypatch, threading.Event())
        async with app.run_test() as pilot:
            await pilot.press("a", "b")
            await pilot.press("ctrl+c")
            await pilot.pause()
            assert app.query_one("#prompt").value == ""
            assert t("run.idle_ctrl_c", "en") in _texts(app) and not app._exit
    asyncio.run(go())


def test_incompatible_engine_fails_closed_in_interface(tmp_path, monkeypatch):
    class OldEngine:
        def run(self, *, max_cycles=1, on_event=None):  # no ``interrupt``
            raise AssertionError("must not run")

        def close(self):
            pass

    monkeypatch.setattr("aido_code.engine_client.check_live_run_api", lambda engine: None)
    monkeypatch.setattr(
        repl.EngineClient, "open", classmethod(lambda cls, *a, **k: EngineClient(OldEngine())),
    )

    async def go():
        app = AidoApp(ReplState(store=SessionStore(tmp_path / "sessions")), "en")
        async with app.run_test() as pilot:
            await _type(pilot, "/run")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert any("interrupt=" in m and m.startswith("Error") for m in _texts(app)), _texts(app)
    asyncio.run(go())


def test_engine_client_interrupt_forwarding_and_classic_path(monkeypatch):
    monkeypatch.setattr("aido_code.engine_client.check_live_run_api", lambda engine: None)
    seen = {}

    class NewEngine:
        def run(self, *, max_cycles=1, on_event=None, interrupt=None):
            seen["interrupt"] = interrupt
            return RunResult(0, True, False, ())

    class OldEngine:
        def run(self, *, max_cycles=1, on_event=None):
            seen["old"] = True
            return RunResult(0, True, False, ())

    flag = threading.Event()
    EngineClient(NewEngine()).run(interrupt=flag)
    assert seen["interrupt"] is flag
    EngineClient(OldEngine()).run()  # classic path does not need it
    assert seen["old"]
    try:
        EngineClient(OldEngine()).run(interrupt=flag)
    except EngineCompatibilityError as exc:
        assert "interrupt" in str(exc)
    else:
        raise AssertionError("expected EngineCompatibilityError")
