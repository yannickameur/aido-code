"""WI-M1.4-01: AIDO's own global worker configuration resolution/loading
(``aido_code.worker_config``). See ``docs/PROJECT_CONTRACT.md`` §4.

Offline only: every case here uses a real ``tmp_path`` file or the real
packaged default — never a network/provider call.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from orchestrator.worker_registry import WorkerRegistryError

from aido_code.worker_config import load_worker_registry, resolve_workers_override_path

VALID_OVERRIDE = dedent(
    """
    workers:
      - worker_id: override-worker
        display_name: Override Worker
        provider: anthropic
        backend: claude_code
        capabilities: [development]
        profiles:
          standard: {quality_tier: STANDARD, model: sonnet}
    """
)

MALFORMED_OVERRIDE = dedent(
    """
    workers:
      - worker_id: broken
        display_name: Broken
        provider: anthropic
        backend: claude_code
        capabilities: [development]
        profiles: {}
    """
)


def test_no_override_uses_packaged_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-empty"))
    monkeypatch.setenv("HOME", str(tmp_path / "home-empty"))

    assert resolve_workers_override_path() is None

    registry = load_worker_registry()
    worker_ids = {w.worker_id for w in registry.all_workers()}
    assert "alice" in worker_ids

    # No file was ever auto-materialized to make this work.
    assert not (tmp_path / "xdg-empty").exists()
    assert not (tmp_path / "home-empty").exists()


def test_xdg_config_home_override_is_used(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    xdg_home = tmp_path / "xdg"
    aido_dir = xdg_home / "aido"
    aido_dir.mkdir(parents=True)
    (aido_dir / "workers.yaml").write_text(VALID_OVERRIDE)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))
    monkeypatch.setenv("HOME", str(tmp_path / "home-unused"))

    resolved = resolve_workers_override_path()
    assert resolved == aido_dir / "workers.yaml"

    registry = load_worker_registry()
    assert {w.worker_id for w in registry.all_workers()} == {"override-worker"}


def test_home_fallback_override_is_used_when_xdg_config_home_unset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    aido_dir = home / ".config" / "aido"
    aido_dir.mkdir(parents=True)
    (aido_dir / "workers.yaml").write_text(VALID_OVERRIDE)

    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(home))

    resolved = resolve_workers_override_path()
    assert resolved == aido_dir / "workers.yaml"

    registry = load_worker_registry()
    assert {w.worker_id for w in registry.all_workers()} == {"override-worker"}


def test_empty_xdg_config_home_falls_back_to_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    home = tmp_path / "home"
    aido_dir = home / ".config" / "aido"
    aido_dir.mkdir(parents=True)
    (aido_dir / "workers.yaml").write_text(VALID_OVERRIDE)

    monkeypatch.setenv("XDG_CONFIG_HOME", "")
    monkeypatch.setenv("HOME", str(home))

    resolved = resolve_workers_override_path()
    assert resolved == aido_dir / "workers.yaml"


def test_malformed_override_fails_closed_never_falls_back(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    xdg_home = tmp_path / "xdg"
    aido_dir = xdg_home / "aido"
    aido_dir.mkdir(parents=True)
    (aido_dir / "workers.yaml").write_text(MALFORMED_OVERRIDE)

    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg_home))
    monkeypatch.setenv("HOME", str(tmp_path / "home-unused"))

    with pytest.raises(WorkerRegistryError):
        load_worker_registry()


def test_packaged_default_loads_and_declares_an_enabled_worker(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-empty"))
    monkeypatch.setenv("HOME", str(tmp_path / "home-empty"))

    registry = load_worker_registry()
    enabled = registry.enabled_workers()
    assert len(enabled) >= 1
    assert any(w.provider for w in enabled)


def test_never_resolves_into_ai_dev_orchestrator_owned_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home = tmp_path / "home"
    aido_dir = home / ".config" / "aido"
    aido_dir.mkdir(parents=True)
    (aido_dir / "workers.yaml").write_text(VALID_OVERRIDE)
    # A sibling ai-dev-orchestrator-owned directory that must never be
    # consulted by this resolution path.
    (home / ".config" / "ai-dev-orchestrator").mkdir(parents=True)
    (home / ".config" / "ai-dev-orchestrator" / "workers.yaml").write_text("workers: []\n")

    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(home))

    resolved = resolve_workers_override_path()
    assert resolved is not None
    assert "ai-dev-orchestrator" not in str(resolved)
    assert resolved == aido_dir / "workers.yaml"


def test_clean_install_never_reads_project_or_sibling_checkout_worker_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Clean-install acceptance (docs/PROJECT_CONTRACT.md §4): a fresh,
    isolated ``HOME``/``XDG_CONFIG_HOME`` with no AIDO override present
    must resolve to the packaged default — never a project's own
    ``config/workers.yaml``, never a sibling ``ai-dev-orchestrator``
    checkout's ``config/workers.yaml``, and never ``~/.config/
    ai-dev-orchestrator/workers.yaml`` (covered by the test above). Both
    decoy files below are real, readable, validly-shaped ``workers.yaml``
    files — if either were consulted this test would silently pass by
    resolving to a decoy instead of failing to resolve at all, so it
    asserts against the decoys' own distinct worker id, not just against
    ``None``.
    """
    home = tmp_path / "home"
    home.mkdir()

    project_dir = tmp_path / "checkout" / "myproject"
    project_config = project_dir / "config"
    project_config.mkdir(parents=True)
    (project_config / "workers.yaml").write_text(VALID_OVERRIDE)

    sibling_checkout_config = tmp_path / "checkout" / "ai-dev-orchestrator" / "config"
    sibling_checkout_config.mkdir(parents=True)
    (sibling_checkout_config / "workers.yaml").write_text(VALID_OVERRIDE)

    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.chdir(project_dir)

    assert resolve_workers_override_path() is None

    registry = load_worker_registry()
    worker_ids = {w.worker_id for w in registry.all_workers()}
    assert worker_ids != {"override-worker"}
    assert "alice" in worker_ids
