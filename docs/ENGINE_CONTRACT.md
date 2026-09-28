# Engine contract

**TL;DR: AIDO Code imports one public facade:
`orchestrator.engine.OrchestratorEngine`.**

This is the exact public surface AIDO Code is built against, from the
`ai-dev-orchestrator` package (P13). This document mirrors that
module's own docstrings; if the two ever disagree, the orchestrator's
source is authoritative and this file is stale and needs updating.

A Python API, not a subprocess/RPC boundary: AIDO Code imports
`orchestrator.engine` directly. Nothing here is called over a socket or
a CLI subprocess.

## Construction

```python
from orchestrator.engine import OrchestratorEngine

engine = OrchestratorEngine.open("path/to/aido.yaml")
```

`.open()` loads and validates `aido.yaml` eagerly. It is read-only: no
`state_dir`, no SQLite file, no provider call. It raises
`EngineConfigError` for any structural problem, never a bare
`ProjectConfigError`/`WorkerRegistryError` (orchestrator-internal types
AIDO Code must never import). This `config_path` shape is the engine's
own legacy, file-based path (`ai-dev-orchestrator` P13.5) — **AIDO
Code's own M1.4 product path never uses it** (see below).

### `worker_registry=` injection (P13.5) — the path M1.4 uses

Since `ai-dev-orchestrator`'s own P13.5, `workers:` is optional in a
legacy `aido.yaml`, and both the constructor and `.open()` accept an
already-built `orchestrator.worker_registry.WorkerRegistry` directly:

```python
from orchestrator.project_config import ProjectConfig
from orchestrator.worker_registry import WorkerRegistry

config: ProjectConfig = ...      # AIDO Code's own typed plan (M1.4, docs/PROJECT_CONTRACT.md §6)
registry: WorkerRegistry = ...   # AIDO Code's own global worker configuration (M1.4, §4)

engine = OrchestratorEngine(config, worker_registry=registry)
```

`config` here is a `ProjectConfig` built through its own **plain Python
constructor** (`ProjectIdentity`/`ExecutionConfig`/`GitConfig`/
`MVPConfig`/`WorkItemConfig`/`ValidationCommand`, all exported from
`orchestrator.project_config`/`orchestrator.validation` unchanged) —
never `ProjectConfig.load(path)` (there is no `ProjectConfig`-shaped
YAML file in the M1.4 product path), and never a second, parallel
"engine plan" type (REUSE FIRST). `config.workers_registry_path` stays
`None`; `WorkerSelector` remains the engine's own, sole owner of *which*
worker is picked — this seam only supplies *what's available*, from
whatever source AIDO Code resolved it (its own global config, §4),
never a caller-side selection decision. `.open(config_path,
worker_registry=...)` accepts the same keyword for the legacy,
file-based construction path too, but M1.4 never uses `.open()` at all.

## Methods

| Method | Returns | Side effect |
|---|---|---|
| `.validate()` | `ProjectSnapshot` | none |
| `.workers()` | `tuple[WorkerSnapshot, ...]` | none, never a provider probe |
| `.probe_workers()` | `tuple[ProviderSnapshot, ...]` | a real, explicit provider probe (network/CLI), no SQLite |
| `.status()` | `ProjectStatusSnapshot` | none, strictly read-only, matches `aido status` |
| `.run(max_cycles=50)` | `RunResult` | the only call that writes: SQLite, Git, a real provider execution |
| `.close()` | `None` | none, a documented no-op (no persistent connection is ever held) |

`OrchestratorEngine` also supports `with OrchestratorEngine.open(...)
as engine:` for symmetry, even though `.close()` does nothing today.

### AIDO Code's own `EngineClient` wrapper

`aido_code.engine_client.EngineClient` is the only place the rest of
this package is allowed to import `orchestrator.engine` from. It is a
thin, 1:1 wrapper: `.validate()`/`.status()`/`.workers()`/
`.probe_workers()`/`.run()`/`.close()` on `EngineClient` each delegate
directly to the identically-named method above, with no local
provider/quota/network logic, extra caching, or fabricated data of its
own. `EngineClient.probe_workers()` is the only thing `/status --probe`
and `/workers --probe` (see `docs/CLI_SPEC.md`) ever call to reach
`OrchestratorEngine.probe_workers()`.

M1.4 (WI-M1.4-05) extends `EngineClient`'s own construction to accept
the already-built `ProjectConfig`/`WorkerRegistry` pair (the
`worker_registry=` injection above) alongside its existing
`provider_adapters`/`subprocess_runner` test seams — still a thin,
1:1 wrapper, never local orchestration logic.

### `.run()` is also resume

There is no separate "resume" call at the engine level. Calling
`.run()` again against the same `aido.yaml` reopens the same persisted
state and continues via the engine's own `WAITING`/`RECOVERY_REQUIRED`
handling. AIDO Code's own session resume (M2) is a different, UX-level
concept; see `ARCHITECTURE.md`.

## Errors

- `EngineConfigError` (subclass of `EngineError`): invalid `aido.yaml`,
  invalid/unreadable worker registry, or a configured provider that
  could not be resolved (e.g. an enabled DeepSeek/Kimi worker with no
  API key).
- `EngineError`: a runtime composition failure surfaced by `.run()`
  (e.g. a persisted-state/config conflict).

AIDO Code must catch these two types at its own boundary and render a
clean message. It must never let a raw orchestrator traceback reach
the terminal UI unhandled.

## Snapshot types (all `@dataclass(frozen=True, slots=True)`)

Every field is a plain `str`/`int`/`bool`/`tuple`/nested-snapshot
value, JSON-serializable by construction, safe for `json`/`stream-json`
output (M5) with no adapter layer needed. AIDO Code never receives a
live Store, SQLite connection, or any dataclass from
`orchestrator.project_state`/`orchestrator.execution_store`/
`orchestrator.wait` directly.

- **`ProjectSnapshot`**: `project_id`, `name`, `workspace`,
  `state_dir`, `mvp_id`, `work_item_count`, `qa_command_count`,
  `enabled_worker_count`, `providers`, `permission_mode`,
  `base_branch`.
- **`WorkerSnapshot`**: `worker_id`, `display_name`, `enabled`,
  `provider`, `backend`, `capabilities`, `priority`,
  `default_profile_id`, `model`.
- **`ProviderSnapshot`**: `provider`, `available`, `reason`
  (`"available"`, an `UnavailabilityReason` value, or
  `"probe_error: ..."`, never fabricated), `reset_at` (ISO timestamps,
  possibly empty), `quota_windows` (`tuple[QuotaWindowSnapshot, ...]`,
  possibly empty), `reset_credits` (`tuple[ResetCreditSnapshot, ...]`,
  possibly empty). The latter two (P13.3) are what `/status --probe`
  and `/workers --probe` render as of M1.2; `EngineClient` re-exports
  both nested types unchanged, with no provider-specific logic of its
  own.
- **`QuotaWindowSnapshot`**: `window_type`, `utilization` (`float |
  None`, a 0-1 fraction, never fabricated when unknown), `remaining`
  (`float | None`, also 0-1), `reset_at` (`str | None`, ISO
  timestamp), `source`.
- **`ResetCreditSnapshot`**: `title`, `status`, `available_count`
  (`int | None`, never fabricated when unknown). Purely descriptive —
  this contract never consumes or proposes consuming a reset credit.
- **`ExecutionSnapshot`**: `execution_id`, `worker_id`,
  `worker_display_name` (`str | None`, the worker's `display_name`
  resolved from the *current* worker registry — `None` if that
  `worker_id` no longer exists there or the registry cannot be loaded,
  never fabricated/guessed),
  `provider`, `status`, `permission_mode`, `started_at`, `finished_at`.
- **`WaitSnapshot`**: `wait_id`, `phase`, `eligible_at`, `providers`.
- **`WorkItemSnapshot`**: `work_item_id`, `status`, `blocked_reason`,
  `last_execution` (`ExecutionSnapshot | None`), `wait`
  (`WaitSnapshot | None`).
- **`MVPStatusSnapshot`**: `mvp_id`, `status` (`None` when the MVP is
  configured but never actually created yet).
- **`ProjectStatusSnapshot`**: `initialized`, `project_id`,
  `project_name`, `mvp` (`MVPStatusSnapshot | None`), `work_items`
  (`tuple[WorkItemSnapshot, ...]`).
- **`EngineEvent`** (P18, `DONE`): `kind` — either the original coarse
  `"work_item.<status>"` (still the only thing `RunResult.events` ever
  contains) or, delivered live via `on_event` only (see below), a finer
  `"dev_a.<status>"`/`"dev_b.<status>"`/`"dev_fix.<status>"`/
  `"qa.<status>"`/`"git.<status>"`/`"run.<status>"` value — plus
  `timestamp`, `project_id`, `mvp_id`, `work_item_id`, `payload` (a
  plain `dict`), and optional metadata (`None` when genuinely unknown,
  never fabricated/guessed from `worker_id`): `execution_id`, `phase`,
  `status`, `worker_id`, `worker_display_name`, `provider`, `backend`,
  `profile_id`, `model`, `quality_tier`, `reasoning_effort`,
  `commit_sha`. See "Events" in `ARCHITECTURE.md`.
- **`RunResult`**: `cycles_run`, `all_terminal`, `reached_max_cycles`,
  `work_items` (`tuple[WorkItemSnapshot, ...]`), `events`
  (`tuple[EngineEvent, ...]`) — unchanged by P18: always the coarse
  per-WorkItem tuple, regardless of whether `on_event` is used.

## Live events and graceful interruption (P18, `DONE`)

Confirmed by direct introspection of the sibling engine this project's
own `.venv` actually imports (editable install of
`~/projects/ai-dev-orchestrator`, `main` at commit `23e68b7`,
2026-09-28):

- `OrchestratorEngine.run(*, max_cycles=..., on_event=None)` — an
  optional `on_event: Callable[[EngineEvent], None]` callback, called
  synchronously in the same thread, once per real live progress fact,
  in the exact order those facts occur, never batched/reordered/from a
  separate thread. Omitting it (the default) leaves every behavior,
  including `RunResult`, exactly as before P18 — this is a pure
  addition, never a breaking change to this contract's existing
  surface. An exception raised by `on_event` itself propagates
  immediately to `.run()`'s own caller, never swallowed.
- Graceful interruption: a `Ctrl+C`/`asyncio.CancelledError` during
  `.run()` is now handled explicitly inside the engine (POSIX
  process-group cleanup for Ralph and QA subprocess trees; no orphaned
  OS processes). `RecoveryCoordinator` was **extended** (never a second
  recovery mechanism) to also reconcile an interrupted/orphaned QA run
  (via the engine's own existing `QARunStore`), not just an interrupted
  DEV execution as before — the next `.run()` call resumes exactly
  where it left off (QA-only resume when DEV already succeeded; DEV is
  never replayed).

**Not yet true of this project's own code**: `EngineClient.run()`
(`src/aido_code/engine_client.py`) still calls
`self._engine.run(max_cycles=max_cycles)` with no `on_event` — wiring a
live timeline and interruption UX on top of this now-available engine
capability is M3's own unbuilt work (`ROADMAP.md`, M3, `WI-M3-01`/
`WI-M3-02`), never something to build by parsing subprocess/Git/SQLite
output instead of this contract.

## What this contract does not give AIDO Code (yet)

- A public `.init()` method. This contract's methods today are exactly
  `.validate()`/`.status()`/`.workers()`/`.probe_workers()`/`.run()`/
  `.close()` — there is no engine-level equivalent of the
  orchestrator's own `aido init`. This turned out not to block M8
  (`aido` command cutover, `DONE`): `aido init` is entirely AIDO Code's
  own logic (`aido_code.project_init`), never a call into the engine —
  see `ROADMAP.md`, M8. AIDO Code must still never import
  `orchestrator.cli`'s private helpers to work around this gap.
- Push/streaming updates over a socket/RPC boundary. `.run()` remains a
  single blocking Python call (with the new optional in-process
  `on_event` callback above); AIDO Code polls by calling it again, or
  drives its own loop around repeated `.status()` calls for a read-only
  view while a separate `.run()` is in flight elsewhere.

None of these are invented here. They are real, still-open
orchestrator-side gaps; AIDO Code must never work around them by
reaching past this contract (parsing stdout/Git/SQLite, guessing a
value). The live-timeline/execution-detail/interrupt gaps that used to
be listed here were the engine-side prerequisite for M3 — they are
resolved (`ai-dev-orchestrator` P18, `DONE`, commit `23e68b7`); only
this project's own consumption of that capability (M3's WorkItems)
remains unbuilt.
