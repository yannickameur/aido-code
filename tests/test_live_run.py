"""Offline tests for the shared live-run path (``aido run`` / ``/run``):
``aido_code.live_run`` plus ``EngineClient.run(on_event=...)``. Fake
engines only; zero real provider or Ralph calls."""

from __future__ import annotations

import io
from types import SimpleNamespace

import pytest

from orchestrator.engine import EngineEvent, RunResult
from orchestrator.engine_events import FailureDiagnostic

from aido_code.engine_client import EngineClient, EngineCompatibilityError
from aido_code.live_run import LiveRunRenderer, format_diagnostics, render_event
from aido_code.repl import format_run


def _event(kind: str, payload: dict | None = None, **fields: object) -> EngineEvent:
    return EngineEvent(
        kind=kind, timestamp="2026-01-01T00:00:00+00:00", project_id="p", mvp_id="m",
        work_item_id="wi-1", payload=payload or {}, **fields,
    )


def _diag(**overrides: object) -> FailureDiagnostic:
    values = dict(
        work_item_id="wi-1", phase="dev_a", execution_id="e1", worker_id="alice",
        worker_display_name="Alice", provider="anthropic", backend="claude", profile_id="default",
        model="m-1", execution_status="failed", exit_code=3, business_verdict="absent",
        ralph_termination_reason="max_iterations", ralph_iterations=5, last_output="boom",
        last_output_stream="stderr", summary="DEV A did not finish", next_action="inspect and rerun",
    )
    values.update(overrides)
    return FailureDiagnostic(**values)


class _FakeEngine:
    def __init__(self, events, result=None) -> None:
        self.events, self.result = events, result or RunResult(1, True, False, ())

    def run(self, *, max_cycles: int = 1, on_event=None) -> RunResult:
        for event in self.events:
            on_event(event)
        return self.result

    def close(self) -> None:
        pass


class TestSharedPath:
    def test_events_render_progressively_before_run_returns(self) -> None:
        out = io.StringIO()
        seen_mid_run: list[str] = []

        class Engine(_FakeEngine):
            def run(self, *, max_cycles=1, on_event=None):
                on_event(_event("work_item.started"))
                seen_mid_run.append(out.getvalue())
                on_event(_event("dev_a.started"))
                seen_mid_run.append(out.getvalue())
                return RunResult(1, True, False, ())

        EngineClient(Engine([])).run(on_event=LiveRunRenderer(out))
        assert "[work_item.started] wi-1" in seen_mid_run[0]
        assert "dev_a.started" not in seen_mid_run[0]
        assert "[dev_a.started]" in seen_mid_run[1]

    def test_client_passes_on_event_through(self) -> None:
        sink = lambda event: None  # noqa: E731
        received = {}

        class Engine(_FakeEngine):
            def run(self, *, max_cycles=1, on_event=None):
                received["on_event"] = on_event
                return RunResult(0, True, False, ())

        EngineClient(Engine([])).run(on_event=sink)
        assert received["on_event"] is sink


class TestRendering:
    def test_metadata_only_from_real_fields(self) -> None:
        line = render_event(_event(
            "dev_a.selected", worker_display_name="Alice", provider="anthropic", backend="claude",
            profile_id="default", model="m-1", quality_tier="HIGH", reasoning_effort="low",
        ))
        for text in ("worker=Alice", "provider=anthropic", "backend=claude", "profile=default",
                     "model=m-1", "tier=HIGH", "effort=low"):
            assert text in line
        assert "commit=" not in line and "worker_id" not in line
        assert "commit=abc123" in render_event(_event("git.merge_completed", commit_sha="abc123"))

    def test_stdout_and_stderr_are_distinguished_without_semantic_labels(self) -> None:
        out = render_event(_event("execution.output", {"stream": "stdout", "text": "running pytest\n"}))
        err = render_event(_event("execution.output", {"stream": "stderr", "text": "oops\n"}))
        assert out == "    [stdout] running pytest"
        assert err == "    [stderr] oops"

    def test_heartbeat_is_only_still_running_with_elapsed(self) -> None:
        line = render_event(_event("execution.heartbeat", {"elapsed_seconds": 12.5}))
        assert line == "    still running (elapsed 12.5s)"

    def test_truncation_shows_reason_and_counts(self) -> None:
        line = render_event(_event("execution.output_truncated", {
            "reason": "max_chars", "delivered_events": 7, "delivered_chars": 4096}))
        assert "reason=max_chars" in line and "delivered_events=7" in line and "delivered_chars=4096" in line

    def test_all_dynamic_values_are_sanitized(self) -> None:
        esc = "\x1b[31mX\x1b]0;t\x07\r"
        out = io.StringIO()
        renderer = LiveRunRenderer(out)
        renderer(_event("execution.output", {"stream": "std\x1bout", "text": esc}))
        renderer(_event("dev_a.selected", {"k\x1b": esc}, worker_display_name=esc, model=esc))
        renderer(_event("execution.output_truncated", {"reason": esc}))
        assert "\x1b" not in out.getvalue() and "\x07" not in out.getvalue() and "\r" not in out.getvalue()

    def test_unknown_malformed_and_partial_events_do_not_raise(self) -> None:
        out = io.StringIO()
        renderer = LiveRunRenderer(out)
        renderer(_event("future.thing", {"a": 1}))
        renderer(_event("execution.output", {}))
        renderer(_event("execution.heartbeat", {}))
        renderer(_event("execution.output_truncated", None))
        renderer(SimpleNamespace(kind="partial"))
        renderer(object())
        renderer(_event("execution.output", {"text": object(), "stream": None}))
        assert "[future.thing] wi-1 a=1" in out.getvalue()
        assert renderer.render_errors == 0

    def test_broken_stream_never_kills_the_run(self) -> None:
        class Broken:
            def write(self, _text):
                raise BrokenPipeError

            def flush(self) -> None:
                raise BrokenPipeError

        renderer = LiveRunRenderer(Broken())
        EngineClient(_FakeEngine([_event("work_item.started")])).run(on_event=renderer)
        assert renderer.render_errors >= 1

    def test_summary_survives_after_stream(self) -> None:
        result = RunResult(1, True, False, (), events=(_event("work_item.completed"),))
        assert "cycles_run: 1" in format_run(result, include_events=False)
        assert "events:" not in format_run(result, include_events=False)
        assert "events:" in format_run(result)


class TestDiagnostics:
    def test_every_diagnostic_is_rendered_with_all_facts(self) -> None:
        text = format_diagnostics((_diag(), _diag(work_item_id="wi-2", exit_code=None, last_output=None,
                                                  ralph_termination_reason=None, ralph_iterations=None)))
        for fragment in ("wi-1: failed in dev_a", "worker=Alice", "provider=anthropic", "backend=claude",
                         "model=m-1", "execution_status=failed", "exit_code=3", "business_verdict=absent",
                         "ralph_termination_reason=max_iterations", "ralph_iterations=5",
                         "last output [stderr]: boom", "summary: DEV A did not finish",
                         "next action: inspect and rerun", "wi-2: failed in dev_a", "exit_code=unknown"):
            assert fragment in text
        assert text.count("failed in") == 2
        assert "provider failed" not in text

    def test_diagnostics_are_sanitized_and_appear_in_summary(self) -> None:
        result = RunResult(1, False, False, (), diagnostics=(_diag(summary="\x1b[2Jbad", last_output="a\rb"),))
        text = format_run(result, include_events=False)
        assert "\x1b" not in text and "\r" not in text
        assert "summary: \\x1b[2Jbad" in text


class TestMissingP21Api:
    def test_engine_without_on_event_fails_closed_before_running(self) -> None:
        ran = []

        class Old:
            def run(self, *, max_cycles=1):
                ran.append(True)

        with pytest.raises(EngineCompatibilityError, match="on_event"):
            EngineClient(Old()).run(on_event=lambda e: None)
        assert not ran

    def test_missing_result_diagnostics_or_event_fields_fail_closed(self, monkeypatch) -> None:
        import dataclasses

        import aido_code.engine_client as module

        @dataclasses.dataclass
        class NoDiagnostics:
            cycles_run: int = 0

        monkeypatch.setattr(module, "RunResult", NoDiagnostics)
        with pytest.raises(EngineCompatibilityError, match="RunResult.diagnostics"):
            EngineClient(_FakeEngine([])).run()

    def test_missing_event_field_fails_closed(self, monkeypatch) -> None:
        monkeypatch.setattr(module_events(), "EngineEvent", type("EngineEvent", (), {}))
        with pytest.raises(EngineCompatibilityError, match="EngineEvent fields"):
            EngineClient(_FakeEngine([])).run()


def module_events():
    from orchestrator import engine_events

    return engine_events
