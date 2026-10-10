"""Offline tests for the fr/en catalog, language selection and the shared dispatcher."""

import io
from types import SimpleNamespace

import pytest

from aido_code import i18n, repl
from aido_code.__main__ import main
from aido_code.live_run import INTERRUPTED_NOTICE
from aido_code.live_run import format_diagnostics, render_event
from aido_code.session import SessionStore


def test_catalogs_define_same_keys():
    assert set(i18n.FR) == set(i18n.EN)


def test_every_command_has_help_text_in_both_languages():
    for name in repl.COMMANDS:
        assert f"help.cmd.{name}" in i18n.EN and f"help.cmd.{name}" in i18n.FR


def test_english_catalog_matches_classic_texts():
    assert i18n.t("interrupted", "en") == INTERRUPTED_NOTICE
    assert repl.format_help("en").splitlines()[1:] == [
        f"  {name} - {description}" for name, description in repl.COMMANDS.items()
    ]


def test_specified_translations():
    assert i18n.event_label("work_item.completed", "fr") == "Tâche terminée"
    assert i18n.event_label("qa.pass", "fr") == "Tests validés"
    assert i18n.t("event.waiting_for_provider", "fr") == "En attente d'une IA disponible"
    assert i18n.event_label("something.unknown", "fr") is None


def test_missing_key_falls_back_to_english_then_key(monkeypatch):
    monkeypatch.setitem(i18n.EN, "only.en", "English only")
    assert i18n.t("only.en", "fr") == "English only"
    assert i18n.t("absent.everywhere", "fr") == "absent.everywhere"
    assert i18n.t("session.created", "xx", session_id="s") == "Created session s"


def test_identifiers_and_raw_text_are_substituted_verbatim():
    sid = "20260101-abc{x}"
    assert sid in i18n.t("session.created", "fr", session_id=sid)
    assert "/tmp/p{a}th" in i18n.t("unknown_command", "fr", command="/tmp/p{a}th")


def test_french_not_understood_lists_capabilities_without_overclaiming():
    text = i18n.t("not_understood", "fr")
    for word in ("status", "workers", "waiting/blocked", "run/continue", "/help", "/status", "/run"):
        assert word in text
    assert "assistant" not in text.lower()


def test_resolve_lang_precedence():
    assert i18n.resolve_lang(None, {}) == "fr"
    assert i18n.resolve_lang(None, {"AIDO_LANG": "en"}) == "en"
    assert i18n.resolve_lang("fr", {"AIDO_LANG": "en"}) == "fr"
    with pytest.raises(i18n.LanguageError):
        i18n.resolve_lang("de", {})
    with pytest.raises(i18n.LanguageError):
        i18n.resolve_lang(None, {"AIDO_LANG": "de"})
    with pytest.raises(i18n.LanguageError):
        i18n.resolve_lang(None, {"AIDO_LANG": ""})


def test_main_rejects_invalid_lang(capsys, monkeypatch):
    monkeypatch.delenv("AIDO_LANG", raising=False)
    assert main(["--lang", "de"]) == 2
    assert "unsupported language" in capsys.readouterr().err
    assert main(["status", "--lang=xx"]) == 2
    assert main(["--lang"]) == 2
    monkeypatch.setenv("AIDO_LANG", "zz")
    assert main(["status"]) == 2
    assert main(["status", "--lang", "en"]) != 2


def _dispatch(lines, lang, tmp_path):
    state = repl.ReplState(config_path=str(tmp_path / "missing.yaml"), store=SessionStore(tmp_path / "s"))
    out = io.StringIO()
    for line in lines:
        if not repl.dispatch_line(line, state, io.StringIO(""), out, lang=lang):
            break
    return out.getvalue()


@pytest.mark.parametrize("lines", [["/help"], ["bonjour ?"], ["/bogus"], ["/exit", "/help"], ["", "/help"]])
def test_dispatcher_parity_with_run(lines, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    expected_in = io.StringIO("".join(f"{line}\n" for line in lines))
    expected_out = io.StringIO()
    repl.run(expected_in, expected_out, prompt="", session_store=SessionStore(tmp_path / "r"))
    assert expected_out.getvalue() == _dispatch_run_style(lines, tmp_path)


def _dispatch_run_style(lines, tmp_path):
    state = repl.ReplState(store=SessionStore(tmp_path / "d"))
    out = io.StringIO()
    for line in lines:
        if not repl.dispatch_line(line, state, io.StringIO(""), out):
            break
    return out.getvalue()


def test_dispatcher_french_help_and_not_understood(tmp_path):
    out = _dispatch(["/help", "blabla"], "fr", tmp_path)
    assert "Commandes disponibles :" in out
    assert "/status" in out and "Je n'ai pas compris" in out


def test_dispatcher_exit_returns_false(tmp_path):
    state = repl.ReplState(store=SessionStore(tmp_path / "s"))
    assert repl.dispatch_line("/exit", state, io.StringIO(), io.StringIO()) is False
    assert repl.dispatch_line("   ", state, io.StringIO(), io.StringIO()) is True


def test_cli_language_reaches_repl_and_cli_wins(tmp_path, monkeypatch):
    from aido_code import __main__ as entrypoint

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("AIDO_LANG", "en")
    output = io.StringIO()
    monkeypatch.setattr(entrypoint.sys, "stdin", io.StringIO("/help\nblabla\n/exit\n"))
    monkeypatch.setattr(entrypoint.sys, "stdout", output)
    assert entrypoint.main(["--lang", "fr"]) == 0
    assert "Commandes disponibles :" in output.getvalue()
    assert "Je n'ai pas compris" in output.getvalue()


def test_env_language_reaches_repl_and_empty_value_is_invalid(tmp_path, monkeypatch):
    from aido_code import __main__ as entrypoint

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("AIDO_LANG", "fr")
    output = io.StringIO()
    monkeypatch.setattr(entrypoint.sys, "stdin", io.StringIO("/help\n/exit\n"))
    monkeypatch.setattr(entrypoint.sys, "stdout", output)
    assert entrypoint.main([]) == 0
    assert "Commandes disponibles :" in output.getvalue()
    monkeypatch.setenv("AIDO_LANG", "")
    assert entrypoint.main([]) == 2


def test_french_live_labels_keep_ids_and_raw_worker_output():
    event = SimpleNamespace(kind="work_item.completed", work_item_id="WI-01", payload={"sha": "abc123"})
    line = render_event(event, lang="fr")
    assert "work_item.completed" in line and "Tâche terminée" in line
    assert "WI-01" in line and "abc123" in line
    raw = "worker says: Tests passed; WI-01"
    output = SimpleNamespace(kind="execution.output", payload={"stream": "stdout", "text": raw})
    assert raw in render_event(output, lang="fr")
    assert "Tests validés" not in render_event(output, lang="fr")
    assert "Tests validés" in render_event(SimpleNamespace(kind="qa.pass", payload={}), lang="fr")


def test_french_diagnostics_translate_labels_only():
    diag = SimpleNamespace(work_item_id="WI-01", phase="qa", summary="raw summary", next_action="run /run",
                           last_output="worker stdout", last_output_stream="stderr")
    text = format_diagnostics([diag], lang="fr")
    for value in ("WI-01", "qa", "raw summary", "run /run", "worker stdout", "stderr"):
        assert value in text
    assert "diagnostics :" in text and "action suivante:" in text
