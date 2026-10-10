"""Offline tests for the Textual interface (``App.run_test()``), fake engine."""

from __future__ import annotations

import asyncio
import io
import subprocess
import sys
from pathlib import Path

import pytest

from aido_code import __main__ as entry
from aido_code import repl
from aido_code.i18n import t
from aido_code.repl import ReplState
from aido_code.session import SessionStore
from aido_code.tui import AidoApp, Message


def _app(tmp_path, lang="fr") -> AidoApp:
    return AidoApp(ReplState(store=SessionStore(tmp_path / "sessions")), lang)


def _texts(app: AidoApp) -> list[str]:
    return [str(m.render()) for m in app.query(Message)]


async def _submit(pilot, text: str) -> None:
    for ch in text:
        await pilot.press("slash" if ch == "/" else "space" if ch == " " else ch)
    await pilot.press("enter")
    await pilot.pause()
    await pilot.app.workers.wait_for_complete()
    await pilot.pause()


def test_input_docked_and_scroll_reaches_earlier_messages(tmp_path):
    async def go():
        app = _app(tmp_path)
        async with app.run_test(size=(80, 20)) as pilot:
            for i in range(60):
                app.add_message("result", f"line {i}")
            await pilot.pause()
            prompt = app.query_one("#prompt")
            log = app.query_one("#log")
            assert prompt.region.bottom == 20 and prompt.region.height >= 1
            assert log.region.bottom <= prompt.region.y
            assert log.scroll_y >= log.max_scroll_y - 1  # followed new output
            for _ in range(10):
                await pilot.press("pageup")
            await pilot.pause()
            assert log.scroll_y < log.max_scroll_y
            at = log.scroll_y
            app.add_message("result", "late")  # not at bottom: no auto-follow
            await pilot.pause()
            assert log.scroll_y == at
            for _ in range(30):
                await pilot.press("pageup")
            await pilot.pause()
            assert log.scroll_y == 0
            assert prompt.region.bottom == 20
    asyncio.run(go())


def test_history_recall(tmp_path):
    async def go():
        app = _app(tmp_path)
        async with app.run_test() as pilot:
            await _submit(pilot, "/help")
            await _submit(pilot, "/new")
            prompt = app.query_one("#prompt")
            await pilot.press("up")
            assert prompt.value == "/new"
            await pilot.press("up")
            assert prompt.value == "/help"
            await pilot.press("down")
            assert prompt.value == "/new"
            await pilot.press("down")
            assert prompt.value == ""
    asyncio.run(go())


def test_help_status_with_fake_engine_and_markup_is_plain(tmp_path, monkeypatch):
    monkeypatch.setattr(repl, "_run_status", lambda *a, **k: "status [bold]FAKE[/bold] \x1b[31mred")

    async def go():
        app = _app(tmp_path, "en")
        async with app.run_test() as pilot:
            await _submit(pilot, "/help")
            assert any("/status" in m for m in _texts(app))
            await _submit(pilot, "/status")
            assert any("[bold]FAKE[/bold] \\x1b[31mred" in m for m in _texts(app))
            assert "running" not in str(app.query_one("#status").render())
            assert "lang: en" in str(app.query_one("#status").render())
    asyncio.run(go())


def test_french_not_understood_and_english(tmp_path):
    async def go(lang):
        app = _app(tmp_path, lang)
        async with app.run_test() as pilot:
            await _submit(pilot, "zzqx blorf")
            return _texts(app)
    fr = asyncio.run(go("fr"))
    en = asyncio.run(go("en"))
    assert t("not_understood", "fr") in fr and t("not_understood", "en") in en
    assert t("not_understood", "fr") != t("not_understood", "en")


def test_exit_command_and_ctrl_d(tmp_path):
    async def go(key):
        app = _app(tmp_path)
        async with app.run_test() as pilot:
            if key == "exit":
                await _submit(pilot, "/exit")
            else:
                await pilot.press("ctrl+d")
            await pilot.pause()
            return app._exit
    assert asyncio.run(go("exit")) and asyncio.run(go("ctrl+d"))


def test_non_tty_runs_classic_loop_without_textual(tmp_path):
    code = (
        "import sys, io; sys.stdin = io.StringIO('/help\\n/exit\\n');"
        "from aido_code.__main__ import main; "
        "rc = main(['--lang','en']); print('textual' in sys.modules, rc, file=sys.stderr)"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          cwd=tmp_path,
                          env={"PYTHONPATH": str(Path("src").resolve()), "HOME": str(tmp_path),
                               "XDG_STATE_HOME": str(tmp_path)})
    assert "aido> " in proc.stdout and "/help" in proc.stdout
    assert proc.stderr.strip().endswith("False 0")


def test_tty_selects_textual_app(monkeypatch, tmp_path):
    called = {}
    monkeypatch.setattr(entry, "_interactive", lambda: True)
    import aido_code.tui as tui
    monkeypatch.setattr(tui, "run_tui", lambda state, lang: called.update(lang=lang))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert entry.main(["--lang", "en"]) == 0
    assert called == {"lang": "en"}
