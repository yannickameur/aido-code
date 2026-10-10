"""Offline tests for the execution time summary shown after a run
(``App.run_test()``), fake engine client."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from orchestrator.engine import ExecutionTimeSnapshot, ProviderExecutionTime

from aido_code import repl
from aido_code.engine_client import EngineClient
from aido_code.repl import ReplState
from aido_code.session import SessionStore
from aido_code.tui import AidoApp, Message, format_duration, format_execution_times


def _snap(providers, total, unknown=0):
    return ExecutionTimeSnapshot("m3.4", tuple(providers), total, unknown)


SNAPSHOT = _snap([
    ProviderExecutionTime("gravity", 38.0, 1, 0),
    ProviderExecutionTime("acme", None, 2, 2),
    ProviderExecutionTime("openai", 252.0, 3, 1),
    ProviderExecutionTime("anthropic", 3725.0, 4, 0),
], 4015.0, 3)


class FakeClient:
    def __init__(self, owner):
        self.owner = owner

    def probe_workers(self):
        return ()

    def execution_times(self):
        self.owner.reads += 1
        if self.owner.snapshot is None:
            raise AttributeError("execution_times")
        return self.owner.snapshot

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass


class Owner:
    def __init__(self, snapshot=SNAPSHOT):
        self.snapshot = snapshot
        self.reads = 0


def _app(tmp_path, monkeypatch, owner, lang, run_result):
    context = SimpleNamespace(roadmap=SimpleNamespace(milestone=SimpleNamespace(id="m3.4")))
    monkeypatch.setattr(repl, "_open_project_command_engine", lambda *a, **k: (context, FakeClient(owner)))
    monkeypatch.setattr(repl, "_run_session_project", lambda *a, **k: run_result)
    store = SessionStore(tmp_path / "sessions")
    state = ReplState(store=store)
    (tmp_path / "proj").mkdir()
    state.session = store.create(str(tmp_path / "proj"))
    return AidoApp(state, lang)


async def _run(app):
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        await app.workers.wait_for_complete()
        for ch in "/run":
            await pilot.press("slash" if ch == "/" else ch)
        await pilot.press("enter")
        for _ in range(200):
            await pilot.pause(0.02)
            if not app.running and any("m3.4" in str(m.render()) for m in app.query(Message)):
                break
        await app.workers.wait_for_complete()
        await pilot.pause()
        texts = [str(m.render()) for m in app.query(Message)]
        await pilot.press("ctrl+o")
        await pilot.pause()
        other = [str(m.render()) for m in app.query(Message)]
        return texts, other


@pytest.mark.parametrize("result", ["All done.", "Error: boom", "Interruption requested"])
def test_table_after_every_run_in_both_views_fr(tmp_path, monkeypatch, result):
    owner = Owner()
    texts, other = asyncio.run(_run(_app(tmp_path, monkeypatch, owner, "fr", result)))
    for shown in (texts, other):
        table = [m for m in shown if m.startswith("Temps d'exécution IA - m3.4")]
        assert len(table) == 1
        lines = table[0].splitlines()
        assert lines[1].startswith("Fournisseur")
        assert "Temps exécuté" in lines[1]
        labels = [line.split(" | ")[0].strip() for line in lines[3:]]
        assert labels == ["Claude", "Codex", "Mistral", "Gravity", "acme", "Total IA"]
        assert "1 h 02 min 05 s" in lines[3]
        assert "4 min 12 s (1 sans durée connue)" in lines[4]
        assert "Aucune exécution" in lines[5]
        assert "38 s" in lines[6]
        assert "Inconnu (2 sans durée connue)" in lines[7]
        assert "1 h 06 min 55 s (3 sans durée connue)" in lines[8]
    assert owner.reads == 1


def test_english_table(tmp_path, monkeypatch):
    texts, _ = asyncio.run(_run(_app(tmp_path, monkeypatch, Owner(_snap([], None)), "en", "done")))
    table = next(m for m in texts if m.startswith("AI execution time - m3.4"))
    assert "Provider" in table and "Execution time" in table
    assert table.count("No execution") == 4
    assert "Total AI | Unknown" in table


def test_engine_without_execution_times(tmp_path, monkeypatch):
    owner = Owner(None)
    texts, other = asyncio.run(_run(_app(tmp_path, monkeypatch, owner, "fr", "done")))
    assert "Bilan des temps non disponible" in texts and "Bilan des temps non disponible" in other


def test_format_duration():
    assert format_duration(3725) == "1 h 02 min 05 s"
    assert format_duration(252) == "4 min 12 s"
    assert format_duration(38) == "38 s"
    assert format_duration(0) == "0 s"


def test_no_table_without_run(tmp_path, monkeypatch):
    owner = Owner()

    async def go():
        app = _app(tmp_path, monkeypatch, owner, "fr", "x")
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.workers.wait_for_complete()
    asyncio.run(go())
    assert owner.reads == 0


def test_format_is_pure_display():
    text = format_execution_times(_snap([], 0.0), "m1", "en")
    assert "Total AI | 0 s" in text


def test_client_passthrough():
    sentinel = object()
    client = EngineClient(SimpleNamespace(execution_times=lambda: sentinel))
    assert client.execution_times() is sentinel
