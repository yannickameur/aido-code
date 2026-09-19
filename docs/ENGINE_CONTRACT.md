# Engine contract

The exact public surface AIDO Code is built against:
`orchestrator.engine.OrchestratorEngine`, from the `ai-dev-orchestrator`
package (P13). This document mirrors that module's own docstrings; if the
two ever disagree, the orchestrator's source is authoritative and this
file is stale and needs updating.

This is a Python API, not a subprocess/RPC boundary: AIDO Code imports
`orchestrator.engine` directly (once it depends on the `ai-dev-
orchestrator` package). Nothing here is called over a socket or a CLI
subprocess.

## Construction

```python
from orchestrator.engine import OrchestratorEngine

engine = OrchestratorEngine.open("path/to/aido.yaml")
```

`.open()` loads and validates `aido.yaml` and its referenced worker
registry eagerly. It is read-only: no `state_dir`, no SQLite file, no
provider call. It raises `EngineConfigError` for any structural problem,
never a bare `ProjectConfigError`/`WorkerRegistryError` (those are
orchestrator-internal types AIDO Code must never import).

## Methods

| Method | Returns | Side effect |
|---|---|---|
| `.validate()` | `ProjectSnapshot` | none |
| `.workers()` | `tuple[WorkerSnapshot, ...]` | none, never a provider probe |
| `.probe_workers()` | `tuple[ProviderSnapshot, ...]` | a real, explicit provider probe (network/CLI), no SQLite |
| `.status()` | `ProjectStatusSnapshot` | none, strictly read-only, matches `aido status` |
| `.run(max_cycles=50)` | `RunResult` | the only call that writes: SQLite, Git, a real provider execution |
| `.close()` | `None` | none, a documented no-op (no persistent connection is ever held between calls) |

`OrchestratorEngine` also supports `with OrchestratorEngine.open(...) as
engine:` for symmetry, even though `.close()` does nothing today.

### `.run()` is also resume

There is no separate "resume" call at the engine level. Calling `.run()`
again against the same `aido.yaml` reopens the same persisted state and
continues via the engine's own `WAITING`/`RECOVERY_REQUIRED` handling.
AIDO Code's own session resume (M2) is a different, UX-level concept; see
`ARCHITECTURE.md`.

## Errors

- `EngineConfigError` (subclass of `EngineError`): invalid `aido.yaml`,
  invalid/unreadable worker registry, or a configured provider that could
  not be resolved (e.g. an enabled DeepSeek/Kimi worker with no API key).
- `EngineError`: a runtime composition failure surfaced by `.run()` (e.g.
  a persisted-state/config conflict).

AIDO Code must catch these two types at its own boundary and render a
clean message. It must never let a raw orchestrator traceback reach the
terminal UI unhandled.

## Snapshot types (all `@dataclass(frozen=True, slots=True)`)

Every field is a plain `str`/`int`/`bool`/`tuple`/nested-snapshot value,
JSON-serializable by construction, safe for `json`/`stream-json` output
(M5) with no adapter layer needed. AIDO Code never receives a live Store,
SQLite connection, or any dataclass from `orchestrator.project_state`/
`orchestrator.execution_store`/`orchestrator.wait` directly.

- **`ProjectSnapshot`**: `project_id`, `name`, `workspace`, `state_dir`,
  `mvp_id`, `work_item_count`, `qa_command_count`,
  `enabled_worker_count`, `providers`, `permission_mode`, `base_branch`.
- **`WorkerSnapshot`**: `worker_id`, `display_name`, `enabled`,
  `provider`, `backend`, `capabilities`, `priority`,
  `default_profile_id`, `model`.
- **`ProviderSnapshot`**: `provider`, `available`, `reason`
  (`"available"`, an `UnavailabilityReason` value, or
  `"probe_error: ..."`, never fabricated), `reset_at` (ISO timestamps,
  possibly empty).
- **`ExecutionSnapshot`**: `execution_id`, `worker_id`, `provider`,
  `status`, `permission_mode`, `started_at`, `finished_at`.
- **`WaitSnapshot`**: `wait_id`, `phase`, `eligible_at`, `providers`.
- **`WorkItemSnapshot`**: `work_item_id`, `status`, `blocked_reason`,
  `last_execution` (`ExecutionSnapshot | None`), `wait`
  (`WaitSnapshot | None`).
- **`MVPStatusSnapshot`**: `mvp_id`, `status` (`None` when the MVP is
  configured but never actually created yet).
- **`ProjectStatusSnapshot`**: `initialized`, `project_id`,
  `project_name`, `mvp` (`MVPStatusSnapshot | None`), `work_items`
  (`tuple[WorkItemSnapshot, ...]`).
- **`EngineEvent`**: `kind` (currently `"work_item.<status>"` only),
  `timestamp`, `project_id`, `mvp_id`, `work_item_id`, `payload` (a
  plain `dict`). See "Events" in `ARCHITECTURE.md` for the current
  granularity limit.
- **`RunResult`**: `cycles_run`, `all_terminal`, `reached_max_cycles`,
  `work_items` (`tuple[WorkItemSnapshot, ...]`), `events`
  (`tuple[EngineEvent, ...]`).

## What this contract does not give AIDO Code (yet)

- A per-sub-step event feed (DEV A running, DEV B completed, QA running,
  merge completed, ...). Only a coarse per-WorkItem event exists today.
- Push/streaming updates. `.run()` is a single blocking call that drives
  up to `max_cycles` WorkItems and returns; AIDO Code polls by calling it
  again, or drives its own loop around repeated `.status()` calls for a
  read-only view while a separate `.run()` is in flight elsewhere.
- Cancellation of an in-flight `.run()`.

None of these are invented here. They are real, future orchestrator-side
work, tracked as `À VOTER`/future increments in `ai-dev-orchestrator`'s
own `ROADMAP.md`, not something AIDO Code should work around by reaching
past this contract.
