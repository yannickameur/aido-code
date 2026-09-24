"""Tests for aido_code.repl: the minimal REPL loop, `/help`/`/exit` (WI-03)
plus the engine-backed `/status`, `/config`, `/validate`, `/workers`,
`/run` commands (WI-04, WI-05, WI-06). Offline only; see tests/conftest.py
and CONTRIBUTING.md.

`TestConfig`/`TestWorkers`/`TestStatus` (WI-M1.4-07C/07D, see `docs/
PROJECT_CONTRACT.md` §7) exercise the modern M1.4 project layout
(`aido_code.project_init.run_init` + AIDO's own global
`WorkerRegistry`) rather than the legacy `write_config()` fixture:
`aido.yaml` no longer carries a `workers:` section, so the legacy
fixture's `ProjectConfig`-shaped file is no longer valid input for any
of the three. `TestRun` still uses `write_config()`/`EngineClient.open()`
— `/run`'s own REPL path is untouched by WI-M1.4-07D.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from orchestrator.providers.contracts import QuotaWindow, ResetCredit, ResetCreditStatus, UnavailabilityReason

from aido_code import project_init
from aido_code.engine_client import EngineClient
from aido_code.engine_plan import build_engine_plan
from aido_code.project_command import load_project_command_context
from aido_code.repl import DEFAULT_CONFIG_PATH, format_help, run
from tests.conftest import (
    REGISTRY_ENABLED_AND_DISABLED,
    REGISTRY_TWO_WORKERS,
    UTC_T0,
    FakeAdapter,
    ScriptedRalphRunner,
    UnavailableAdapter,
    commit_action,
    write_config,
)


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


def _init_m14_project(tmp_path: Path, name: str = "roadmaplab") -> Path:
    """Scaffolds a fresh M1.4 project (manifest + `ROADMAP.md` DRAFT +
    `resources/` + a real Git repo, `aido_code.project_init.run_init`)
    and returns its `aido.yaml` path — the same scaffold
    `tests/test_project_command.py` uses for `aido-code validate`/`run`.
    """
    assert project_init.run_init(str(tmp_path), name) == 0
    return tmp_path / name / "aido.yaml"


def _set_worker_registry_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, registry: str) -> None:
    xdg_home = tmp_path / "xdg"
    aido_dir = xdg_home / "aido"
    aido_dir.mkdir(parents=True, exist_ok=True)
    (aido_dir / "workers.yaml").write_text(registry)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))


def _pin_fake_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "fake-home"
    fake_home.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(fake_home))


def _use_packaged_default_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No override anywhere: ``aido_code.worker_config.
    load_worker_registry()`` falls back to AIDO Code's own packaged
    ``default_workers.yaml`` (WI-M1.4-01)."""
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    _pin_fake_home(tmp_path, monkeypatch)


def _commit_all(project_dir: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=str(project_dir), check=True)
    subprocess.run(
        ["git", "-c", "user.email=e2e@example.invalid", "-c", "user.name=E2E", "commit", "-q", "-m", message],
        cwd=str(project_dir), check=True,
    )


def _approve_milestone(project_dir: Path) -> None:
    """Flips a freshly-scaffolded project's DRAFT milestone to APPROVED —
    same edit ``tests/test_project_command.py``'s own ``_approve()``
    makes, reproduced here since that module is a separate test file —
    then commits it: `/run`'s own governance (``GitGovernanceService``)
    requires a clean tracked worktree before it will start a WorkItem."""
    roadmap_path = project_dir / "ROADMAP.md"
    roadmap_path.write_text(
        roadmap_path.read_text().replace("Status: DRAFT", "Status: APPROVED"), encoding="utf-8",
    )
    _commit_all(project_dir, "Approve milestone")


def _approve_milestone_with_passing_qa(project_dir: Path) -> None:
    """Same as ``_approve_milestone()``, plus a trivially-passing QA
    command: the bare ``aido-code init`` scaffold has no ``### QA``
    section at all, and an offline persisted ``.run()`` needs one so
    ``DEV A -> DEV B -> QA`` genuinely reaches ``completed`` rather than
    exhausting rework attempts on a QA misconfiguration. Also drops a
    ``pyproject.toml`` stack marker (``InternalQAEngine.stack_supported()``
    requires one) — same marker ``tests/conftest.py``'s own
    ``init_git_repo()`` writes for every other offline `.run()` fixture."""
    roadmap_path = project_dir / "ROADMAP.md"
    text = roadmap_path.read_text().replace("Status: DRAFT", "Status: APPROVED")
    text += (
        "\n### QA\n\n"
        "#### QA-01 — Tests\n\n"
        "Kind: unit_test\n"
        "Required: true\n"
        "Timeout: 300\n"
        f'Argv: ["{sys.executable}", "-c", "pass"]\n'
    )
    roadmap_path.write_text(text, encoding="utf-8")
    (project_dir / "pyproject.toml").write_text("[tool.pytest.ini_options]\n", encoding="utf-8")
    _commit_all(project_dir, "Approve milestone with passing QA")


def _build_status_engine_client(
    config_path: Path,
    *,
    provider_adapters: dict[str, Any] | None = None,
    subprocess_runner: object | None = None,
) -> EngineClient:
    """Builds the exact modern engine plan `/status` itself now uses
    (`_open_project_command_engine()` in `aido_code.repl`), so a test can
    drive an offline, fake-engine `.run()` against the very same
    persisted `state_dir` a later `/status` call will read from."""
    context = load_project_command_context(config_path)
    plan = build_engine_plan(context.manifest, context.roadmap, context.resources)
    return EngineClient.from_config(
        plan, worker_registry=context.worker_registry,
        provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
    )


class TestHelp:
    def test_help_lists_available_commands(self) -> None:
        transcript = _run("/help\n/exit\n")
        assert "/help" in transcript
        assert "/exit" in transcript
        assert format_help() in transcript


class TestExit:
    def test_exit_cleanly_terminates_the_loop(self) -> None:
        transcript = _run("/exit\n")
        assert "Unknown command" not in transcript

    def test_eof_terminates_the_loop_without_error(self) -> None:
        # No trailing /exit: readline() hits EOF immediately.
        transcript = _run("")
        assert "Unknown command" not in transcript


class TestUnrecognizedCommand:
    def test_unrecognized_command_prints_clear_message_not_a_traceback(self) -> None:
        transcript = _run("/bogus\n/exit\n")
        assert "Unknown command: '/bogus'" in transcript
        assert "Traceback" not in transcript

    def test_blank_lines_are_ignored(self) -> None:
        transcript = _run("\n\n/exit\n")
        assert "Unknown command" not in transcript


class TestNoProjectLevelResumeCommand:
    """M1.1 adds no project-level `/resume` command, and M2's own
    session-level `/resume`/`/new` remain entirely unimplemented and
    unaffected by this milestone: `/run` alone is still how a project
    starts/resumes (see M1_1_SPEC.yaml)."""

    def test_slash_resume_is_not_a_recognized_command(self) -> None:
        transcript = _run("/resume\n/exit\n")
        assert "Unknown command: '/resume'" in transcript
        assert "Traceback" not in transcript

    def test_slash_new_is_not_a_recognized_command(self) -> None:
        transcript = _run("/new\n/exit\n")
        assert "Unknown command: '/new'" in transcript
        assert "Traceback" not in transcript

    def test_help_never_advertises_resume_or_new(self) -> None:
        transcript = _run("/help\n/exit\n")
        assert "/resume" not in transcript
        assert "/new" not in transcript


class TestEntryPoints:
    def test_python_dash_m_aido_code_starts_repl_and_accepts_commands(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _use_packaged_default_registry(tmp_path, monkeypatch)
        # Pinning HOME above isolates the packaged-default-registry lookup
        # from the real developer machine, but it can also hide this
        # interpreter's editable-install site-packages (resolved against
        # the *real* HOME at process startup) from the subprocess. Carry
        # the parent's already-resolved sys.path across explicitly so the
        # subprocess can still import aido_code/orchestrator.
        child_env = {**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)}
        result = subprocess.run(
            [sys.executable, "-m", "aido_code"],
            input="/help\n/workers\n/config\n/bogus\n/exit\n",
            cwd=config_path.parent,
            capture_output=True,
            text=True,
            timeout=10,
            env=child_env,
        )
        assert result.returncode == 0
        assert "/help" in result.stdout
        assert "current_milestone_status: DRAFT" in result.stdout
        assert "victor" in result.stdout
        assert "Unknown command: '/bogus'" in result.stdout
        assert "Traceback" not in result.stderr

    def test_python_dash_m_aido_code_reports_missing_config_cleanly(self, tmp_path: Path) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "aido_code"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 1
        assert "Error:" in result.stderr
        assert "Traceback" not in result.stderr


class TestStatus:
    """`/status` (WI-M1.4-07D, `docs/PROJECT_CONTRACT.md` §7) combines
    `ROADMAP.md`'s own current-milestone facts (DRAFT/APPROVED) with the
    real, unchanged `OrchestratorEngine.status()` snapshot — never a
    WorkItem/MVP status invented from `ROADMAP.md` itself. Uses the same
    modern M1.4 project layout as `TestConfig`/`TestWorkers`."""

    def test_uninitialized_draft_project_reports_not_initialized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _use_packaged_default_registry(tmp_path, monkeypatch)

        transcript = _run("/status\n/exit\n", config_path=str(config_path))

        assert "current_milestone_id: m1" in transcript
        assert "current_milestone_status: DRAFT" in transcript
        assert "NOT_INITIALIZED" in transcript
        assert "Traceback" not in transcript

    def test_approved_project_before_first_run_still_reports_not_initialized(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The APPROVED/DRAFT gate is `/run`'s own concern (§3.2): an
        APPROVED milestone with no persisted engine state yet must still
        report `NOT_INITIALIZED` honestly, never a fabricated PENDING/
        COMPLETED WorkItem list read out of `ROADMAP.md`."""
        config_path = _init_m14_project(tmp_path)
        _approve_milestone(config_path.parent)
        _use_packaged_default_registry(tmp_path, monkeypatch)

        transcript = _run("/status\n/exit\n", config_path=str(config_path))

        assert "current_milestone_id: m1" in transcript
        assert "current_milestone_status: APPROVED" in transcript
        assert "NOT_INITIALIZED" in transcript
        assert "Traceback" not in transcript

    def test_initialized_project_reports_real_persisted_status_never_from_roadmap(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _approve_milestone_with_passing_qa(config_path.parent)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_TWO_WORKERS)
        _pin_fake_home(tmp_path, monkeypatch)
        runner = ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )
        client = _build_status_engine_client(
            config_path, provider_adapters={"anthropic": FakeAdapter(available=True)}, subprocess_runner=runner,
        )
        client.run()

        transcript = _run("/status\n/exit\n", config_path=str(config_path))

        assert "current_milestone_id: m1" in transcript
        assert "current_milestone_status: APPROVED" in transcript
        assert "NOT_INITIALIZED" not in transcript
        assert "project: roadmaplab (roadmaplab)" in transcript
        assert "wi-1: completed" in transcript
        assert "Traceback" not in transcript

    def test_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/status\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript

    def test_renders_full_worker_list_with_zero_provider_probes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
        _pin_fake_home(tmp_path, monkeypatch)

        transcript = _run("/status\n/exit\n", config_path=str(config_path))

        assert "workers:" in transcript
        assert "alice" in transcript
        assert "enabled" in transcript
        assert "bob" in transcript
        assert "disabled" in transcript
        assert "probe=" not in transcript
        assert "Traceback" not in transcript

    def test_no_provider_adapter_is_ever_instantiated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import orchestrator.engine as engine_module

        def _fail_resolve(providers: object) -> None:
            raise AssertionError("provider adapters must never be resolved by plain /status")

        monkeypatch.setattr(engine_module, "resolve_provider_adapters", _fail_resolve)

        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
        _pin_fake_home(tmp_path, monkeypatch)

        transcript = _run("/status\n/exit\n", config_path=str(config_path))
        assert "alice" in transcript
        assert "Traceback" not in transcript

    def test_probe_renders_same_status_plus_real_worker_states(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
        _pin_fake_home(tmp_path, monkeypatch)
        adapter = FakeAdapter(available=True)

        transcript = _run(
            "/status --probe\n/exit\n",
            config_path=str(config_path),
            provider_adapters={"anthropic": adapter},
        )

        assert "NOT_INITIALIZED" in transcript
        assert "alice" in transcript
        assert "probe=available" in transcript
        assert "bob" in transcript
        assert "probe=disabled" in transcript
        assert adapter.calls == 1
        assert "Traceback" not in transcript

    def test_probe_reports_quota_exhaustion_honestly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_TWO_WORKERS)
        _pin_fake_home(tmp_path, monkeypatch)
        adapter = UnavailableAdapter(UnavailabilityReason.QUOTA_EXHAUSTED)

        transcript = _run(
            "/status --probe\n/exit\n",
            config_path=str(config_path),
            provider_adapters={"anthropic": adapter},
        )

        assert "alice" in transcript
        assert "bob" in transcript
        assert transcript.count("probe=quota") == 2

    def test_probe_renders_real_quota_windows_and_reset_credits_never_fabricated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_TWO_WORKERS)
        _pin_fake_home(tmp_path, monkeypatch)
        reset_at = datetime(2026, 9, 21, 15, 0, tzinfo=timezone.utc)
        adapter = FakeAdapter(
            available=True,
            quota_windows=(
                QuotaWindow(
                    window_type="five_hour", source="claude_code", observed_at=UTC_T0,
                    utilization=0.25, reset_at=reset_at,
                ),
                QuotaWindow(
                    window_type="seven_day", source="claude_code", observed_at=UTC_T0,
                    utilization=None, reset_at=None,
                ),
            ),
            reset_credits=(
                ResetCredit(title="weekly bonus", status=ResetCreditStatus.AVAILABLE, available_count=2),
                ResetCredit(title="mystery credit", status=ResetCreditStatus.UNKNOWN, available_count=None),
            ),
        )

        transcript = _run(
            "/status --probe\n/exit\n", config_path=str(config_path), provider_adapters={"anthropic": adapter},
        )

        assert "provider quotas:" in transcript
        assert "  anthropic:" in transcript
        assert "five_hour: utilization=25% remaining=75%" in transcript
        assert reset_at.isoformat() in transcript
        assert "seven_day: utilization=unknown remaining=unknown reset_at=unknown" in transcript
        assert "reset credit weekly bonus: available (available=2)" in transcript
        assert "reset credit mystery credit: unknown (available=unknown)" in transcript

    def test_probe_renders_quota_once_per_provider_not_per_worker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_TWO_WORKERS)
        _pin_fake_home(tmp_path, monkeypatch)
        adapter = FakeAdapter(
            available=True,
            quota_windows=(
                QuotaWindow(
                    window_type="five_hour", source="claude_code", observed_at=UTC_T0,
                    utilization=0.5, reset_at=None,
                ),
            ),
        )

        transcript = _run(
            "/status --probe\n/exit\n", config_path=str(config_path), provider_adapters={"anthropic": adapter},
        )

        assert transcript.count("  anthropic:") == 1
        assert transcript.count("five_hour") == 1

    def test_plain_status_never_renders_a_quota_section(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _use_packaged_default_registry(tmp_path, monkeypatch)

        transcript = _run("/status\n/exit\n", config_path=str(config_path))

        assert "provider quotas:" not in transcript

    def test_probe_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/status --probe\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript


class TestConfig:
    def test_config_renders_manifest_roadmap_and_engine_facts_never_a_raw_file_dump(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_TWO_WORKERS)
        _pin_fake_home(tmp_path, monkeypatch)
        project_dir = (tmp_path / "roadmaplab").resolve()

        transcript = _run("/config\n/exit\n", config_path=str(config_path))

        assert "project: roadmaplab (roadmaplab)" in transcript
        assert f"workspace: {project_dir}" in transcript
        assert f"roadmap: {project_dir / 'ROADMAP.md'}" in transcript
        assert f"resources: {project_dir / 'resources'}" in transcript
        assert "initial_prompt: Read ROADMAP.md and the project resources referenced by it" in transcript
        assert "current_milestone_id: m1" in transcript
        assert "current_milestone_status: DRAFT" in transcript
        assert "enabled_workers: 2" in transcript
        assert "providers: anthropic" in transcript
        assert "permission_mode: STANDARD" in transcript
        assert "base_branch: main" in transcript
        assert "qa_commands: 0" in transcript
        assert "schema_version" not in transcript
        assert "Traceback" not in transcript

    def test_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/config\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript


class TestValidate:
    def test_valid_configuration_reports_success_with_no_side_effect(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path)
        transcript = _run("/validate\n/exit\n", config_path=str(config_path))
        assert "Configuration is valid." in transcript
        assert not (tmp_path / "state").exists()

    def test_invalid_worker_registry_reports_failure_not_a_traceback(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path, registry="workers:\n  - worker_id: alice\n")
        transcript = _run("/validate\n/exit\n", config_path=str(config_path))
        assert "Validation failed" in transcript
        assert "Traceback" not in transcript

    def test_missing_aido_yaml_reports_failure_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/validate\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Validation failed" in transcript


class TestRun:
    def test_run_calls_the_real_engine_and_renders_the_run_result(self, tmp_path: Path) -> None:
        config_path = write_config(tmp_path)
        runner = ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )
        transcript = _run(
            "/run\n/exit\n",
            config_path=str(config_path),
            provider_adapters={"anthropic": FakeAdapter(available=True)},
            subprocess_runner=runner,
        )
        assert "Traceback" not in transcript
        assert "cycles_run: 1" in transcript
        assert "all_terminal: True" in transcript
        assert "wi-1: completed" in transcript
        assert "work_item.completed: work_item=wi-1" in transcript
        assert len(runner.calls) == 2

    def test_rerunning_an_already_completed_project_does_nothing_and_never_re_executes(
        self, tmp_path: Path
    ) -> None:
        config_path = write_config(tmp_path)
        first_runner = ScriptedRalphRunner(
            [
                {"topic": "work.completed", "mutate": commit_action("feature.py", "x = 1\n", "DEV A")},
                {"topic": "work.completed"},
            ]
        )
        client = EngineClient.open(
            str(config_path),
            provider_adapters={"anthropic": FakeAdapter(available=True)},
            subprocess_runner=first_runner,
        )
        first_result = client.run()
        assert first_result.all_terminal is True

        async def never_called_runner(*args: object, **kwargs: object) -> tuple[int, bytes, bytes]:
            raise AssertionError("completed projects must not invoke the subprocess runner")

        transcript = _run(
            "/run\n/exit\n",
            config_path=str(config_path),
            provider_adapters={"anthropic": FakeAdapter(available=True)},
            subprocess_runner=never_called_runner,
        )
        assert "Traceback" not in transcript
        assert "all_terminal: True" in transcript
        assert "wi-1: completed" in transcript

    def test_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/run\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript


class TestWorkers:
    def test_lists_enabled_and_disabled_workers_from_a_user_override_registry(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
        _pin_fake_home(tmp_path, monkeypatch)

        transcript = _run("/workers\n/exit\n", config_path=str(config_path))

        assert "alice" in transcript
        assert "enabled" in transcript
        assert "bob" in transcript
        assert "disabled" in transcript
        assert "Traceback" not in transcript

    def test_lists_workers_from_the_packaged_default_registry_when_no_override_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _use_packaged_default_registry(tmp_path, monkeypatch)

        transcript = _run("/workers\n/exit\n", config_path=str(config_path))

        assert "alice" in transcript
        assert "victor" in transcript
        assert "Traceback" not in transcript

    def test_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/workers\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript

    def test_no_provider_adapter_is_ever_instantiated(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import orchestrator.engine as engine_module

        def _fail_resolve(providers: object) -> None:
            raise AssertionError("provider adapters must never be resolved by /workers")

        monkeypatch.setattr(engine_module, "resolve_provider_adapters", _fail_resolve)

        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
        _pin_fake_home(tmp_path, monkeypatch)

        transcript = _run("/workers\n/exit\n", config_path=str(config_path))
        assert "alice" in transcript
        assert "Traceback" not in transcript

    def test_probe_renders_the_same_worker_states_as_status_probe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
        _pin_fake_home(tmp_path, monkeypatch)
        adapter = FakeAdapter(available=True)
        transcript = _run(
            "/workers --probe\n/exit\n",
            config_path=str(config_path),
            provider_adapters={"anthropic": adapter},
        )
        assert "alice" in transcript
        assert "probe=available" in transcript
        assert "bob" in transcript
        assert "probe=disabled" in transcript
        assert adapter.calls == 1
        assert "project:" not in transcript
        assert "Traceback" not in transcript

    def test_probe_renders_the_same_quota_section_as_status_probe(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        status_config_path = _init_m14_project(tmp_path / "status-proj")
        workers_config_path = _init_m14_project(tmp_path / "workers-proj")
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_TWO_WORKERS)
        _pin_fake_home(tmp_path, monkeypatch)
        quota_windows = (
            QuotaWindow(
                window_type="five_hour", source="claude_code", observed_at=UTC_T0,
                utilization=0.4, reset_at=None,
            ),
        )
        status_transcript = _run(
            "/status --probe\n/exit\n",
            config_path=str(status_config_path),
            provider_adapters={"anthropic": FakeAdapter(available=True, quota_windows=quota_windows)},
        )
        workers_transcript = _run(
            "/workers --probe\n/exit\n",
            config_path=str(workers_config_path),
            provider_adapters={"anthropic": FakeAdapter(available=True, quota_windows=quota_windows)},
        )
        status_quota_section = status_transcript.split("provider quotas:", 1)[1]
        workers_quota_section = workers_transcript.split("provider quotas:", 1)[1]
        assert status_quota_section == workers_quota_section

    def test_plain_workers_never_renders_a_quota_section(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        config_path = _init_m14_project(tmp_path)
        _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_TWO_WORKERS)
        _pin_fake_home(tmp_path, monkeypatch)
        transcript = _run("/workers\n/exit\n", config_path=str(config_path))
        assert "provider quotas:" not in transcript

    def test_probe_missing_aido_yaml_prints_clear_error_not_a_traceback(self, tmp_path: Path) -> None:
        transcript = _run("/workers --probe\n/exit\n", config_path=str(tmp_path / "does-not-exist.yaml"))
        assert "Error:" in transcript
        assert "Traceback" not in transcript


def test_status_probe_calls_engine_probe_workers_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the M1.1 opt-in boundary structural: `/status --probe` must
    use the engine's real snapshot tuple exactly once, rather than merely
    making an equivalent-looking provider call or fabricating displayed
    states."""
    config_path = _init_m14_project(tmp_path)
    _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
    _pin_fake_home(tmp_path, monkeypatch)
    adapter = FakeAdapter(available=True)
    original_probe_workers = EngineClient.probe_workers
    calls = 0

    def count_and_delegate(client: EngineClient):
        nonlocal calls
        calls += 1
        return original_probe_workers(client)

    monkeypatch.setattr(EngineClient, "probe_workers", count_and_delegate)
    transcript = _run(
        "/status --probe\n/exit\n",
        config_path=str(config_path),
        provider_adapters={"anthropic": adapter},
    )

    assert calls == 1
    assert adapter.calls == 1
    assert "probe=available" in transcript
    assert "probe=disabled" in transcript
    assert "NOT_INITIALIZED" in transcript


def test_workers_probe_calls_engine_probe_workers_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same structural guarantee as `test_status_probe_calls_engine_probe_workers_exactly_once`,
    for `/workers --probe` on the modern M1.4 project layout."""
    config_path = _init_m14_project(tmp_path)
    _set_worker_registry_override(tmp_path, monkeypatch, registry=REGISTRY_ENABLED_AND_DISABLED)
    _pin_fake_home(tmp_path, monkeypatch)
    adapter = FakeAdapter(available=True)
    original_probe_workers = EngineClient.probe_workers
    calls = 0

    def count_and_delegate(client: EngineClient):
        nonlocal calls
        calls += 1
        return original_probe_workers(client)

    monkeypatch.setattr(EngineClient, "probe_workers", count_and_delegate)
    transcript = _run(
        "/workers --probe\n/exit\n",
        config_path=str(config_path),
        provider_adapters={"anthropic": adapter},
    )

    assert calls == 1
    assert adapter.calls == 1
    assert "probe=available" in transcript
    assert "probe=disabled" in transcript
    assert "NOT_INITIALIZED" not in transcript
