"""Offline tests for the AI plan quota panel (``App.run_test()``), fake engine."""

from __future__ import annotations

import asyncio
import threading
import time

import pytest
from orchestrator.engine import ProviderSnapshot, QuotaWindowSnapshot

from aido_code import repl
from aido_code.i18n import t
from aido_code.repl import ReplState
from aido_code.session import SessionStore
from aido_code.tui import AidoApp, Message


def _win(kind, remaining, reset="2030-01-02T03:04:00+00:00"):
    return QuotaWindowSnapshot(kind, None if remaining is None else 1 - remaining, remaining, reset, "test")


PROVIDERS = (
    ProviderSnapshot("anthropic", True, "available", quota_windows=(
        _win("five_hour", 0.724), _win("seven_day", None, None))),
    ProviderSnapshot("openai", True, "available", quota_windows=(
        _win("primary_5h", 0.5), _win("secondary_7d", 0.25))),
    ProviderSnapshot("gravity", True, "available", quota_windows=(_win("Gemini Pro", 0.9),)),
    ProviderSnapshot("mistral", True, "available"),
    ProviderSnapshot("acme", False, "probe_error: boom"),
)


class FakeClient:
    def __init__(self, owner):
        self.owner = owner

    def probe_workers(self):
        self.owner.calls += 1
        self.owner.started.set()
        self.owner.release.wait(5)
        if self.owner.error:
            raise RuntimeError("down")
        return PROVIDERS

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


class Owner:
    def __init__(self, release=True, error=False):
        self.calls = 0
        self.error = error
        self.started = threading.Event()
        self.release = threading.Event()
        if release:
            self.release.set()


def _app(tmp_path, monkeypatch, owner, lang="fr", project=True):
    monkeypatch.setattr(repl, "_open_project_command_engine", lambda *a, **k: (None, FakeClient(owner)))
    store = SessionStore(tmp_path / "sessions")
    state = ReplState(store=store)
    if project:
        (tmp_path / "proj").mkdir()
        state.session = store.create(str(tmp_path / "proj"))
    return AidoApp(state, lang)


def _quota(app):
    return str(app.query_one("#quota").render())


async def _settle(pilot):
    await pilot.pause()
    await pilot.app.workers.wait_for_complete()
    await pilot.pause()


def test_probe_on_mount_fr_windows(tmp_path, monkeypatch):
    owner = Owner()

    async def go():
        app = _app(tmp_path, monkeypatch, owner)
        async with app.run_test() as pilot:
            await _settle(pilot)
            text = _quota(app)
            assert "Claude: 5 h 72 %" in text and "7 j inconnu" in text
            assert "Codex: 5 h 50 % (réinitialisation" in text and "7 j 25 %" in text
            assert "Gravity: Gemini Pro 90 %" in text
            assert "Mistral: Non communiqué" in text
            assert "acme: Non disponible" in text
            assert owner.calls == 1
            assert app.query_one("#quota").region.y == 1
    asyncio.run(go())


def test_english_labels(tmp_path, monkeypatch):
    owner = Owner()

    async def go():
        app = _app(tmp_path, monkeypatch, owner, "en")
        async with app.run_test() as pilot:
            await _settle(pilot)
            text = _quota(app)
            assert "7 d unknown" in text and "Mistral: Not reported" in text
            assert "acme: Not available" in text and "resets" in text
    asyncio.run(go())


def test_mount_not_blocked_refreshing_and_inflight_ignored(tmp_path, monkeypatch):
    owner = Owner(release=False)

    async def go():
        app = _app(tmp_path, monkeypatch, owner)
        async with app.run_test() as pilot:
            await pilot.pause()
            assert _quota(app) == t("quota.refreshing", "fr")
            await pilot.press("a")
            assert app.query_one("#prompt").value == "a"
            await pilot.press("ctrl+r")
            await pilot.press("ctrl+r")
            owner.release.set()
            await _settle(pilot)
            assert owner.calls == 1
            await pilot.press("ctrl+r")
            await _settle(pilot)
            assert owner.calls == 2
            await pilot.pause(0.3)
            assert owner.calls == 2
    asyncio.run(go())


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_probe_error_and_no_project(tmp_path, monkeypatch, lang):
    async def go(**kw):
        owner = Owner(error=kw.pop("error", False))
        app = _app(tmp_path, monkeypatch, owner, lang, **kw)
        async with app.run_test() as pilot:
            await _settle(pilot)
            return _quota(app), owner.calls
    expected = t("quota.not_available", lang)
    assert asyncio.run(go(error=True)) == (expected, 1)
    assert asyncio.run(go(project=False)) == (expected, 0)


@pytest.mark.parametrize("lang", ["fr", "en"])
def test_help_lists_ctrl_r(tmp_path, monkeypatch, lang):
    async def go():
        app = _app(tmp_path, monkeypatch, Owner(), lang)
        async with app.run_test() as pilot:
            for ch in "/help":
                await pilot.press("slash" if ch == "/" else ch)
            await pilot.press("enter")
            await _settle(pilot)
            assert any("Ctrl+R" in str(m.render()) and t("help.refresh_quota", lang) in str(m.render())
                       for m in app.query(Message))
    asyncio.run(go())
