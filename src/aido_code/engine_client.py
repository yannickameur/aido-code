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
    RunResult,
    WorkerSnapshot,
)

__all__ = [
    "EngineClient",
    "EngineConfigError",
    "EngineError",
    "ProjectSnapshot",
    "ProjectStatusSnapshot",
    "RunResult",
    "WorkerSnapshot",
]


class EngineClient:
    """Wraps one ``OrchestratorEngine`` for the rest of this package,
    surfacing exactly its ``.validate()``/``.status()``/``.workers()``/
    ``.run()`` calls. Construct via ``.open()``."""

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

    def validate(self) -> ProjectSnapshot:
        return self._engine.validate()

    def status(self) -> ProjectStatusSnapshot:
        return self._engine.status()

    def workers(self) -> tuple[WorkerSnapshot, ...]:
        return self._engine.workers()

    def run(self, *, max_cycles: int = DEFAULT_MAX_CYCLES) -> RunResult:
        return self._engine.run(max_cycles=max_cycles)

    def close(self) -> None:
        self._engine.close()

    def __enter__(self) -> "EngineClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
