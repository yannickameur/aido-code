"""Tests for terminal rendering safety (F-02, WI-M1.3-02): every dynamic
value the REPL prints that originates from an OrchestratorEngine snapshot
must pass through the one shared `sanitize_for_terminal()` before printing,
so a worker/project name or blocked_reason can never smuggle a terminal
control sequence into the REPL's output. Offline only; see
tests/conftest.py and CONTRIBUTING.md.

Deliberately a separate file from tests/test_repl.py (a qa_protected_paths
entry, see aido.m1_3.example.yaml) so this new coverage never touches a
protected file's content.
"""

from __future__ import annotations

import io
from contextlib import nullcontext
from typing import Any

import pytest

from orchestrator.engine import ProjectSnapshot, ProjectStatusSnapshot, WorkerSnapshot, WorkItemSnapshot

from aido_code.engine_client import EngineClient
from aido_code.repl import DEFAULT_CONFIG_PATH, format_status, format_workers, run, sanitize_for_terminal


def _run(
    commands: str,
    *,
    config_path: str = DEFAULT_CONFIG_PATH,
    provider_adapters: dict[str, Any] | None = None,
    subprocess_runner: object | None = None,
) -> str:
    output = io.StringIO()
    run(
        io.StringIO(commands),
        output,
        config_path=config_path,
        provider_adapters=provider_adapters,
        subprocess_runner=subprocess_runner,
    )
    return output.getvalue()


class TestTerminalRenderingSafety:
    """F-terminal-safety: every dynamic value rendered from an
    OrchestratorEngine snapshot must pass through the one shared
    `sanitize_for_terminal()` before printing, so a worker/project name or
    blocked_reason can never smuggle a terminal control sequence into the
    REPL's output."""

    def test_sanitize_neutralizes_ansi_escape_sequence(self) -> None:
        malicious = "Alice\x1b[31mDANGER\x1b[0m"
        safe = sanitize_for_terminal(malicious)
        assert "\x1b" not in safe
        assert "\\x1b" in safe
        assert "DANGER" in safe

    def test_sanitize_neutralizes_bare_cr(self) -> None:
        malicious = "before\rafter"
        safe = sanitize_for_terminal(malicious)
        assert "\r" not in safe
        assert "before\\rafter" == safe

    def test_sanitize_neutralizes_injected_lf(self) -> None:
        malicious = "before\nafter"
        safe = sanitize_for_terminal(malicious)
        assert "\n" not in safe
        assert "before\\nafter" == safe

    def test_sanitize_leaves_ordinary_unicode_text_unchanged(self) -> None:
        text = "Café Wörker あいう \U0001f600"
        assert sanitize_for_terminal(text) == text

    def test_sanitize_never_mutates_the_input_string(self) -> None:
        malicious = "before\x1b[31mafter"
        sanitize_for_terminal(malicious)
        assert malicious == "before\x1b[31mafter"

    def test_format_workers_neutralizes_ansi_in_display_name(self) -> None:
        worker = WorkerSnapshot(
            worker_id="alice",
            display_name="Alice\x1b[31mDANGER\x1b[0m",
            enabled=True,
            provider="anthropic",
            backend="cli",
            capabilities=(),
            priority=1,
            default_profile_id=None,
            model=None,
        )
        rendered = format_workers((worker,))
        assert "\x1b" not in rendered
        assert "\\x1b" in rendered

    def test_format_workers_neutralizes_bare_cr_in_display_name(self) -> None:
        worker = WorkerSnapshot(
            worker_id="alice",
            display_name="Alice\rOverwritten",
            enabled=True,
            provider="anthropic",
            backend="cli",
            capabilities=(),
            priority=1,
            default_profile_id=None,
            model=None,
        )
        rendered = format_workers((worker,))
        assert "\r" not in rendered
        assert "Alice\\rOverwritten" in rendered

    def test_format_workers_neutralizes_injected_lf_in_display_name(self) -> None:
        worker = WorkerSnapshot(
            worker_id="alice",
            display_name="Alice\nfake: line",
            enabled=True,
            provider="anthropic",
            backend="cli",
            capabilities=(),
            priority=1,
            default_profile_id=None,
            model=None,
        )
        rendered = format_workers((worker,))
        assert "Alice\\nfake: line" in rendered
        # The only real newlines are the ones this formatter itself inserts
        # between lines; none are smuggled in from the display_name.
        assert rendered.count("\n") == 1

    def test_format_workers_leaves_ordinary_unicode_display_name_unchanged(self) -> None:
        worker = WorkerSnapshot(
            worker_id="alice",
            display_name="Alice éè \U0001f600",
            enabled=True,
            provider="anthropic",
            backend="cli",
            capabilities=(),
            priority=1,
            default_profile_id=None,
            model=None,
        )
        rendered = format_workers((worker,))
        assert "Alice éè \U0001f600" in rendered

    def test_format_status_neutralizes_ansi_in_project_name(self) -> None:
        snapshot = ProjectStatusSnapshot(
            initialized=True,
            project_id="demo",
            project_name="Demo\x1b[31mDANGER\x1b[0m",
            mvp=None,
        )
        rendered = format_status(snapshot)
        assert "\x1b" not in rendered
        assert "\\x1b" in rendered

    def test_format_status_neutralizes_bare_cr_in_blocked_reason(self) -> None:
        work_item = WorkItemSnapshot(
            work_item_id="wi-1", status="blocked", blocked_reason="bad\rreason",
        )
        snapshot = ProjectStatusSnapshot(
            initialized=True, project_id="demo", project_name="Demo", mvp=None,
            work_items=(work_item,),
        )
        rendered = format_status(snapshot)
        assert "\r" not in rendered
        assert "bad\\rreason" in rendered

    def test_format_status_neutralizes_injected_lf_in_blocked_reason(self) -> None:
        work_item = WorkItemSnapshot(
            work_item_id="wi-1", status="blocked", blocked_reason="bad\nfake: line",
        )
        snapshot = ProjectStatusSnapshot(
            initialized=True, project_id="demo", project_name="Demo", mvp=None,
            work_items=(work_item,),
        )
        rendered = format_status(snapshot)
        assert "bad\\nfake: line" in rendered
        assert "fake: line\n" not in rendered

    def test_format_status_leaves_ordinary_unicode_blocked_reason_unchanged(self) -> None:
        work_item = WorkItemSnapshot(
            work_item_id="wi-1", status="blocked", blocked_reason="café \U0001f600",
        )
        snapshot = ProjectStatusSnapshot(
            initialized=True, project_id="demo", project_name="Demo", mvp=None,
            work_items=(work_item,),
        )
        rendered = format_status(snapshot)
        assert "café \U0001f600" in rendered

    def test_repl_output_neutralizes_snapshot_text_without_mutating_snapshots(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        payload = "label\x1b[31mred\rreplace\nfake: line"
        project = ProjectSnapshot(
            project_id="café あいう \U0001f600", name=payload, workspace="/tmp",
            state_dir="/tmp/state", mvp_id="mvp-1", work_item_count=1,
            qa_command_count=0, enabled_worker_count=1, providers=("anthropic",),
            permission_mode="safe", base_branch="main",
        )
        worker = WorkerSnapshot(
            worker_id="alice", display_name=payload, enabled=True,
            provider="anthropic", backend="cli", capabilities=(), priority=1,
            default_profile_id=None, model=None,
        )
        item = WorkItemSnapshot(
            work_item_id="wi-1", status="blocked", blocked_reason=payload,
        )
        status = ProjectStatusSnapshot(
            initialized=True, project_id=project.project_id,
            project_name=payload, mvp=None, work_items=(item,),
        )

        class FakeClient:
            def validate(self) -> ProjectSnapshot:
                return project

            def status(self) -> ProjectStatusSnapshot:
                return status

            def workers(self) -> tuple[WorkerSnapshot, ...]:
                return (worker,)

        monkeypatch.setattr(EngineClient, "open", lambda *args, **kwargs: nullcontext(FakeClient()))
        transcript = _run("/config\n/status\n/workers\n/exit\n")

        safe = "label\\x1b[31mred\\rreplace\\nfake: line"
        assert transcript.count(safe) == 5
        assert "\x1b" not in transcript
        assert "\r" not in transcript
        assert "replace\nfake: line" not in transcript
        assert project.project_id in transcript
        assert project.name == worker.display_name == item.blocked_reason == payload
