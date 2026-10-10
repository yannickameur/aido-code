"""Offline tests for /export and honest text selection."""

from __future__ import annotations

import asyncio

import pytest

from aido_code import tui
from aido_code.i18n import t
from aido_code.repl import ReplState
from aido_code.session import SessionStore
from aido_code.tui import AidoApp


def _app(tmp_path, monkeypatch, lang="en"):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    store = SessionStore(tmp_path / "sessions")
    state = ReplState(store=store)
    project = tmp_path / "proj"
    project.mkdir()
    state.session = store.create(str(project))
    return AidoApp(state, lang)


async def _submit(app, pilot, text):
    app.query_one("#prompt").value = text
    await pilot.press("enter")
    await pilot.pause()


def _exports(tmp_path):
    return sorted((tmp_path / "state" / "aido" / "exports").glob("*.txt"))


def test_select_disabled():
    assert AidoApp.ALLOW_SELECT is False


def test_export_order_and_completeness(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)

    async def go():
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            app.add_message("result", "first answer")
            app._add_live_event("dev", "simple one", "detailed one [bold]x[/bold]")
            app.add_message("result", "second answer")
            app._last_times = "TABLE"
            app._last_summary = "SUMMARY"
            await _submit(app, pilot, "/export")
            return [str(m.render()) for m in app.query(tui.Message)]

    shown = asyncio.run(go())
    (path,) = _exports(tmp_path)
    assert path.name.startswith(app.state.session.session_id + "-")
    assert str(path) in shown[-1]
    text = path.read_text(encoding="utf-8")
    pos = [text.index(s) for s in ("first answer", "detailed one [bold]x[/bold]", "second answer", "TABLE", "SUMMARY")]
    assert pos == sorted(pos)
    assert "simple one" not in text
    assert not list((tmp_path / "proj").iterdir())


def test_export_during_run(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)

    async def go():
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            app.running = True
            app._add_live_event("dev", None, "live detail")
            await _submit(app, pilot, "/export")

    asyncio.run(go())
    (path,) = _exports(tmp_path)
    assert "live detail" in path.read_text(encoding="utf-8")


def test_eviction_notice(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)

    async def go():
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            for i in range(tui._EVENT_HISTORY_LIMIT + 3):
                app._add_live_event("dev", None, f"event-{i}")
            await _submit(app, pilot, "/export")

    asyncio.run(go())
    text = _exports(tmp_path)[0].read_text(encoding="utf-8")
    assert "3 older event(s) were evicted" in text
    assert "event-2\n" not in text
    assert "event-3\n" in text


def test_no_notice_without_eviction(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch)

    async def go():
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            await _submit(app, pilot, "/export")

    asyncio.run(go())
    assert "evicted" not in _exports(tmp_path)[0].read_text(encoding="utf-8")


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_export_only_labels_real_run_summary_and_time_table(tmp_path, monkeypatch, lang):
    app = _app(tmp_path, monkeypatch, lang)
    summary = "cycles_run: 1" if lang == "en" else t("run.summary", lang) + "\ncycles_run (cycles_run): 1"
    table = "AI execution time - m1" if lang == "en" else "Temps d'exécution IA - m1"

    async def go():
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            app._finish("/run", "Error: engine unavailable", True, t("times.unavailable", lang))
            await _submit(app, pilot, "/export")
            first_text = _exports(tmp_path)[0].read_text(encoding="utf-8")
            app._finish("/run", summary, True, table)
            app._finish("/run", t("interrupted", lang), True, t("times.unavailable", lang))
            await _submit(app, pilot, "/export")
            second = next(path for path in _exports(tmp_path) if path.read_text(encoding="utf-8") != first_text)
            return first_text, second.read_text(encoding="utf-8")

    first_text, second_text = asyncio.run(go())
    assert t("export.summary", lang) not in first_text
    assert t("export.times", lang) not in first_text
    assert t("export.summary", lang) + "\n" + summary in second_text
    assert t("export.times", lang) + "\n" + table in second_text


def test_export_error_translated_fr(tmp_path, monkeypatch):
    app = _app(tmp_path, monkeypatch, "fr")
    blocker = tmp_path / "state"
    blocker.write_text("not a directory")

    async def go():
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            await _submit(app, pilot, "/export")
            return [str(m.render()) for m in app.query(tui.Message)]

    shown = asyncio.run(go())
    assert shown[-1].startswith("Échec de l'export")


@pytest.mark.parametrize("lang, error", [
    ("en", "The export directory is inside the project."),
    ("fr", "Le dossier d'export se trouve dans le projet."),
])
def test_export_rejects_state_directory_inside_project(tmp_path, monkeypatch, lang, error):
    app = _app(tmp_path, monkeypatch, lang)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "proj" / "state"))

    async def go():
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            await _submit(app, pilot, "/export")
            return [str(m.render()) for m in app.query(tui.Message)]

    shown = asyncio.run(go())
    assert error in shown[-1]
    assert not list((tmp_path / "proj").iterdir())


@pytest.mark.parametrize("lang,marker,shift", [("en", "Exported to", "Shift"), ("fr", "Exporté vers", "Maj")])
def test_languages_and_help(tmp_path, monkeypatch, lang, marker, shift):
    app = _app(tmp_path, monkeypatch, lang)

    async def go():
        async with app.run_test(size=(100, 40)) as pilot:
            await pilot.pause()
            await _submit(app, pilot, "/export")
            await app.workers.wait_for_complete()
            await _submit(app, pilot, "/help")
            for _ in range(100):
                await pilot.pause(0.02)
                if any("/export" in str(m.render()) for m in app.query(tui.Message)):
                    break
            return [str(m.render()) for m in app.query(tui.Message)]

    shown = asyncio.run(go())
    assert any(marker in m for m in shown)
    help_text = next(m for m in shown if "/quit" in m)
    for item in ("/export", "/quit", "F10", "Shift+drag", shift):
        assert item in help_text
    header = "Export AIDO" if lang == "fr" else "AIDO export"
    assert header in _exports(tmp_path)[0].read_text(encoding="utf-8")
