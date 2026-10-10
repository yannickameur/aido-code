"""Offline tests for the fr/en catalog, language selection and the shared dispatcher."""

import io

import pytest

from aido_code import i18n, repl
from aido_code.__main__ import main
from aido_code.live_run import INTERRUPTED_NOTICE
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
