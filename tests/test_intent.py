"""Tests for the deterministic intent router (`aido_code.intent`) and its
REPL wiring. Offline only: interpretation never touches an engine or a
provider."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from aido_code import intent as intent_module
from aido_code.engine_client import EngineClient
from aido_code.intent import Intent, interpret
from aido_code.repl import NOT_UNDERSTOOD, _format_why_waiting
from tests.conftest import REGISTRY_ENABLED_AND_DISABLED, FakeAdapter
from tests.test_repl import _init_m14_project, _pin_fake_home, _run, _set_worker_registry_override


@pytest.mark.parametrize(
    "text, expected",
    [
        ("what's the status?", Intent.STATUS),
        ("show me the project state", Intent.STATUS),
        ("how is progress", Intent.STATUS),
        ("status", Intent.STATUS),
        ("why is WI-03 waiting?", Intent.WHY_WAITING),
        ("Why is work item WI-03 blocked", Intent.WHY_WAITING),
        ("why are we stuck", Intent.WHY_WAITING),
        ("which workers are available?", Intent.WORKERS),
        ("list the providers", Intent.WORKERS),
        ("what workers are configured", Intent.WORKERS),
        ("run the project", Intent.RUN),
        ("please continue", Intent.RUN),
        ("continue the work", Intent.RUN),
        ("go ahead and start", Intent.RUN),
    ],
)
def test_each_intent_recognised_in_several_phrasings(text: str, expected: Intent) -> None:
    assert interpret(text).intent is expected


def test_why_extracts_work_item_id() -> None:
    assert interpret("why is WI-03 waiting?").work_item_id == "WI-03"
    assert interpret("Why is work item alpha blocked").work_item_id == "alpha"
    assert interpret("why are we stuck").work_item_id is None


@pytest.mark.parametrize(
    "text",
    [
        "",
        "hello",
        "write me a poem",
        "don't run the project",
        "delete everything",
        "what is the weather",
        "please run the workers",
    ],
)
def test_ambiguous_or_unrecognised_input_is_unknown(text: str) -> None:
    assert interpret(text).intent is Intent.UNKNOWN


def test_matcher_has_no_engine_or_provider_dependency() -> None:
    source = Path(intent_module.__file__).read_text()
    for forbidden in ("engine_client", "orchestrator", "provider_adapters", "subprocess"):
        assert forbidden not in source.replace("providers", "")


def test_repl_unrecognised_input_replies_not_understood_without_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(*_a: object, **_k: object) -> None:
        raise AssertionError("engine must not be touched")

    monkeypatch.setattr(EngineClient, "from_config", boom)
    monkeypatch.setattr(EngineClient, "open", boom)
    transcript = _run("tell me a joke\ndelete everything\n/exit\n")
    assert transcript.count(NOT_UNDERSTOOD) == 2


def test_repl_workers_question_uses_workers_command_with_zero_probes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _init_m14_project(tmp_path)
    _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
    _pin_fake_home(tmp_path, monkeypatch)
    adapter = FakeAdapter(available=True)
    nl = _run("which workers are available?\n/exit\n", config_path=str(config_path),
              provider_adapters={"anthropic": adapter})
    cmd = _run("/workers\n/exit\n", config_path=str(config_path), provider_adapters={"anthropic": adapter})
    assert nl == cmd
    assert adapter.calls == 0


def test_repl_status_question_matches_status_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _init_m14_project(tmp_path)
    _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
    _pin_fake_home(tmp_path, monkeypatch)
    adapter = FakeAdapter(available=True)
    nl = _run("what's the status?\n/exit\n", config_path=str(config_path), provider_adapters={"anthropic": adapter})
    cmd = _run("/status\n/exit\n", config_path=str(config_path), provider_adapters={"anthropic": adapter})
    assert nl == cmd and "NOT_INITIALIZED" in nl
    assert adapter.calls == 0


def test_repl_run_phrase_invokes_exactly_the_run_action(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr("aido_code.repl._run_run", lambda *a, **k: calls.append("run") or "RAN")
    transcript = _run("please continue\nrun the project\n/exit\n")
    assert calls == ["run", "run"]
    assert transcript.count("RAN") == 2


def test_repl_why_waiting_answers_from_engine_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = _init_m14_project(tmp_path)
    _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
    _pin_fake_home(tmp_path, monkeypatch)
    adapter = FakeAdapter(available=True)
    transcript = _run("why is WI-01 waiting?\n/exit\n", config_path=str(config_path),
                      provider_adapters={"anthropic": adapter})
    assert "NOT_INITIALIZED" in transcript
    assert adapter.calls == 0


def test_format_why_waiting_reports_only_snapshot_facts() -> None:
    item = SimpleNamespace(work_item_id="WI-01", status="BLOCKED", blocked_reason="qa failed", wait=None)
    snap = SimpleNamespace(initialized=True, work_items=(item,))
    assert "blocked_reason=qa failed" in _format_why_waiting(snap, "wi-01")
    assert "no WorkItem WI-9" in _format_why_waiting(snap, "WI-9")
    assert "WI-01" in _format_why_waiting(snap, None)
