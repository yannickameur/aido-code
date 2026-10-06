"""Live rendering of one governed run: the single path shared by
``aido run`` and the REPL's ``/run``.

``LiveRunRenderer`` is the ``on_event`` callback handed to
``OrchestratorEngine.run()`` (via ``EngineClient.run``). It renders only
public ``EngineEvent`` fields as they arrive, and ``format_diagnostics``
renders every ``RunResult.diagnostics`` entry. Nothing here reads Git,
SQLite, ``.ralph`` or subprocess output, classifies backend text, or
infers a cause the engine did not report. Every dynamic value goes
through ``sanitize_for_terminal()``.
"""

from __future__ import annotations

from typing import Any, TextIO

from aido_code.repl import sanitize_for_terminal as _clean

_METADATA_FIELDS = (
    ("worker", "worker_display_name"),
    ("worker_id", "worker_id"),
    ("provider", "provider"),
    ("backend", "backend"),
    ("profile", "profile_id"),
    ("model", "model"),
    ("tier", "quality_tier"),
    ("effort", "reasoning_effort"),
    ("commit", "commit_sha"),
)


def _get(obj: object, name: str) -> Any:
    return getattr(obj, name, None)


def _metadata(event: object) -> str:
    parts = []
    for label, attr in _METADATA_FIELDS:
        value = _get(event, attr)
        if value is not None:
            parts.append(f"{label}={_clean(value)}")
    return " ".join(parts)


def _payload_items(event: object) -> str:
    payload = _get(event, "payload")
    if not isinstance(payload, dict):
        return ""
    return " ".join(f"{_clean(key)}={_clean(value)}" for key, value in sorted(payload.items(), key=lambda kv: str(kv[0])))


def _output_line(event: object) -> str:
    payload = _get(event, "payload")
    payload = payload if isinstance(payload, dict) else {}
    text = payload.get("text")
    stream = payload.get("stream")
    text = "" if text is None else (text if isinstance(text, str) else str(text))
    label = _clean(stream) if stream is not None else "output"
    return f"    [{label}] {_clean(text)}"


def render_event(event: object) -> str:
    """One display block for one ``EngineEvent``; never raises for a
    well-formed event and tolerates missing/odd fields on a future one."""
    kind = _get(event, "kind")
    work_item = _get(event, "work_item_id")
    if kind == "execution.output":
        return _output_line(event)
    if kind == "execution.heartbeat":
        payload = _get(event, "payload")
        elapsed = payload.get("elapsed_seconds") if isinstance(payload, dict) else None
        suffix = f" (elapsed {_clean(elapsed)}s)" if elapsed is not None else ""
        return f"    still running{suffix}"
    if kind == "execution.output_truncated":
        payload = _get(event, "payload")
        payload = payload if isinstance(payload, dict) else {}
        return (
            f"    output truncated: reason={_clean(payload.get('reason'))} "
            f"delivered_events={_clean(payload.get('delivered_events'))} "
            f"delivered_chars={_clean(payload.get('delivered_chars'))}"
        )
    head = f"[{_clean(kind)}]"
    if work_item is not None:
        head += f" {_clean(work_item)}"
    tail = " ".join(part for part in (_metadata(event), _payload_items(event)) if part)
    return f"{head} {tail}" if tail else head


class LiveRunRenderer:
    """Callable ``on_event`` sink that writes one flushed block per event.

    A presentation failure is swallowed (after one plain-text fallback
    attempt) so it can never abort a governed run."""

    def __init__(self, stream: TextIO) -> None:
        self._stream = stream
        self.render_errors = 0

    def __call__(self, event: object) -> None:
        try:
            text = render_event(event)
        except Exception:
            self.render_errors += 1
            text = f"[unrenderable event: {_clean(type(event).__name__)}]"
        try:
            self._stream.write(text + "\n")
            self._stream.flush()
        except Exception:
            self.render_errors += 1


def format_diagnostics(diagnostics: object) -> str:
    """Render every ``FailureDiagnostic``; ``""`` when there are none."""
    entries = list(diagnostics or ())
    if not entries:
        return ""
    lines = ["diagnostics:"]
    for diag in entries:
        try:
            lines.extend(_format_diagnostic(diag))
        except Exception:
            lines.append(f"  {_clean(_get(diag, 'work_item_id'))}: (diagnostic could not be rendered)")
    return "\n".join(lines)


def _format_diagnostic(diag: object) -> list[str]:
    def opt(label: str, attr: str) -> str:
        value = _get(diag, attr)
        return f"{label}={_clean(value)}" if value is not None else ""

    def row(*parts: str) -> str:
        return "    " + " ".join(part for part in parts if part)

    lines = [
        f"  {_clean(_get(diag, 'work_item_id'))}: failed in {_clean(_get(diag, 'phase'))}",
        row(opt("worker", "worker_display_name"), opt("worker_id", "worker_id"), opt("provider", "provider"),
            opt("backend", "backend"), opt("profile", "profile_id"), opt("model", "model")),
        row(opt("execution_status", "execution_status"),
            f"exit_code={_clean(_get(diag, 'exit_code'))}" if _get(diag, "exit_code") is not None else "exit_code=unknown",
            opt("business_verdict", "business_verdict")),
    ]
    if _get(diag, "ralph_termination_reason") is not None or _get(diag, "ralph_iterations") is not None:
        lines.append(row(opt("ralph_termination_reason", "ralph_termination_reason"),
                         opt("ralph_iterations", "ralph_iterations")))
    last_output = _get(diag, "last_output")
    if last_output:
        stream = _get(diag, "last_output_stream")
        label = _clean(stream) if stream is not None else "output"
        lines.append(f"    last output [{label}]: {_clean(last_output)}")
    lines.append(f"    summary: {_clean(_get(diag, 'summary'))}")
    lines.append(f"    next action: {_clean(_get(diag, 'next_action'))}")
    failures = _get(diag, "output_delivery_failures")
    if failures:
        lines.append(
            f"    output display failures: {_clean(failures)} "
            f"(last: {_clean(_get(diag, 'last_output_delivery_error'))})"
        )
    return [line for line in lines if line.strip()]
