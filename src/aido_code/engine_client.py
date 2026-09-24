"""The only orchestrator import the rest of this package is allowed to
use: a thin wrapper around ``orchestrator.engine.OrchestratorEngine``
(see ``docs/ENGINE_CONTRACT.md``).

This module never constructs ``MVPManager``/``WorkerSelector``/
``QuotaManager``/a ``ProviderAdapter`` and never reads a Store/SQLite file
directly; every fact returned here comes straight from
``OrchestratorEngine``'s own typed, frozen snapshots.
"""

from __future__ import annotations

from typing import Any

from orchestrator.engine import (
    DEFAULT_MAX_CYCLES,
    EngineConfigError,
    EngineError,
    OrchestratorEngine,
    ProjectSnapshot,
    ProjectStatusSnapshot,
    ProviderSnapshot,
    QuotaWindowSnapshot,
    ResetCreditSnapshot,
    RunResult,
    WorkerSnapshot,
)
from orchestrator.project_config import ProjectConfig
from orchestrator.worker_registry import WorkerRegistry

__all__ = [
    "EngineClient",
    "EngineConfigError",
    "EngineError",
    "ProjectSnapshot",
    "ProjectStatusSnapshot",
    "ProviderSnapshot",
    "QuotaWindowSnapshot",
    "ResetCreditSnapshot",
    "RunResult",
    "WorkerSnapshot",
]


class EngineClient:
    """Wraps one ``OrchestratorEngine`` for the rest of this package,
    surfacing exactly its ``.validate()``/``.status()``/``.workers()``/
    ``.probe_workers()``/``.run()`` calls. Construct via ``.open()``."""

    def __init__(self, engine: OrchestratorEngine) -> None:
        self._engine = engine

    @classmethod
    def open(
        cls,
        config_path: str,
        *,
        provider_adapters: dict[str, Any] | None = None,
        subprocess_runner: object | None = None,
    ) -> "EngineClient":
        """Same contract as ``OrchestratorEngine.open()``: read-only, eager
        config/worker-registry validation, raises ``EngineConfigError`` on
        any structural problem. ``provider_adapters``/``subprocess_runner``
        are the engine's own test-only seams; production callers never set
        them."""
        engine = OrchestratorEngine.open(
            config_path, provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
        )
        return cls(engine)

    @classmethod
    def from_config(
        cls,
        config: ProjectConfig,
        *,
        worker_registry: WorkerRegistry,
        provider_adapters: dict[str, Any] | None = None,
        subprocess_runner: object | None = None,
    ) -> "EngineClient":
        """M1.4's own construction path (``docs/PROJECT_CONTRACT.md`` §6):
        an already-built typed engine plan
        (``aido_code.engine_plan.build_engine_plan``) and AIDO's own
        global ``WorkerRegistry``
        (``aido_code.worker_config.load_worker_registry``), injected
        directly into ``OrchestratorEngine``'s own plain constructor —
        never ``.open(config_path)``, since there is no
        ``ProjectConfig``-shaped YAML file anywhere in this product
        path. ``provider_adapters``/``subprocess_runner`` are the same
        test-only seams ``.open()`` accepts; production callers never
        set them."""
        engine = OrchestratorEngine(
            config, worker_registry=worker_registry,
            provider_adapters=provider_adapters, subprocess_runner=subprocess_runner,
        )
        return cls(engine)

    def validate(self) -> ProjectSnapshot:
        return self._engine.validate()

    def status(self) -> ProjectStatusSnapshot:
        return self._engine.status()

    def workers(self) -> tuple[WorkerSnapshot, ...]:
        return self._engine.workers()

    def probe_workers(self) -> tuple[ProviderSnapshot, ...]:
        return self._engine.probe_workers()

    def run(self, *, max_cycles: int = DEFAULT_MAX_CYCLES) -> RunResult:
        return self._engine.run(max_cycles=max_cycles)

    def close(self) -> None:
        self._engine.close()

    def __enter__(self) -> "EngineClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
