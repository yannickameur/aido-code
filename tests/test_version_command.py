"""Read-only version/v command parity across CLI, REPL and Textual."""

from __future__ import annotations

import asyncio
import io
import sys
from importlib.metadata import PackageNotFoundError

import pytest
from textual.widgets import Input

from aido_code import __main__ as entrypoint
from aido_code import repl, version_info
from aido_code.session import SessionStore
from aido_code.tui import AidoApp, Message


@pytest.fixture
def expected_versions(monkeypatch):
    versions = {"aido-code": "0.2.3", "ai-dev-orchestrator": "0.2.2"}
    monkeypatch.setattr(version_info, "version", lambda name: versions[name])
    return (
        "AIDO Code           : 0.2.3\n"
        "AI Dev Orchestrator : 0.2.2\n"
        f"Python              : {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )


@pytest.mark.parametrize("command", ["version", "v"])
def test_cli_version_aliases_are_read_only(command, tmp_path, monkeypatch, capsys, expected_versions):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AIDO_LANG", raising=False)
    monkeypatch.setattr(entrypoint, "load_project_command_context", lambda *a, **k: pytest.fail("project access"))
    monkeypatch.setattr(entrypoint, "SessionStore", lambda *a, **k: pytest.fail("session access"))
    assert entrypoint.main([command]) == 0
    captured = capsys.readouterr()
    assert captured.out == expected_versions + "\n"
    assert captured.err == ""
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("command", ["version", "v"])
def test_cli_version_rejects_extra_args(command, capsys, monkeypatch):
    monkeypatch.delenv("AIDO_LANG", raising=False)
    assert entrypoint.main([command, "extra"]) == 2
    assert f"usage: " in capsys.readouterr().err


@pytest.mark.parametrize("command", ["/version", "/v"])
def test_repl_version_aliases_do_not_need_project(command, tmp_path, expected_versions):
    state = repl.ReplState(config_path=str(tmp_path / "absent.yaml"), store=SessionStore(tmp_path / "sessions"))
    out = io.StringIO()
    assert repl.dispatch_line(command, state, io.StringIO(), out, lang="fr") is True
    assert out.getvalue() == expected_versions + "\n"
    assert state.config_path.endswith("absent.yaml")


def test_repl_help_lists_version_aliases_bilingually():
    for lang in ("en", "fr"):
        help_text = repl.format_help(lang)
        assert "/version" in help_text and "/v" in help_text


def test_missing_distribution_is_not_fabricated(monkeypatch):
    def missing(name):
        raise PackageNotFoundError(name)
    monkeypatch.setattr(version_info, "version", missing)
    result = version_info.format_versions()
    assert "AIDO Code           : not installed" in result
    assert "AI Dev Orchestrator : not installed" in result


def test_tui_v_command_displays_same_versions(tmp_path, expected_versions):
    async def run_tui_test():
        app = AidoApp(repl.ReplState(store=SessionStore(tmp_path / "sessions")), "fr")
        async with app.run_test() as pilot:
            app.query_one("#prompt", Input).value = "/v"
            await pilot.press("enter")
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()
            rendered = "\n".join(str(m.render()) for m in app.query(Message))
            assert "AIDO Code           : 0.2.3" in rendered
            assert "AI Dev Orchestrator : 0.2.2" in rendered
    asyncio.run(run_tui_test())
