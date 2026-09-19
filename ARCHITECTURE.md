# Architecture

## Target shape

```
USER
  |
  v
AIDO CODE                     (this project)
  |
  | orchestrator.engine.OrchestratorEngine
  | a public Python API, not a subprocess/RPC boundary
  | typed, frozen, serializable snapshots in; typed calls out
  v
AI DEV ORCHESTRATOR            (the engine, a separate project/dependency)
  |
  +-- ProjectConfig
  +-- OrchestratorEngine (facade)
  +-- ProjectStatusReader
  +-- WorkerRegistry
  +-- WorkerSelector
  +-- QuotaManager
  +-- ProviderAdapters
  +-- MVPManager
  +-- RalphExecutionEngine
  +-- InternalQAEngine
  +-- GitGovernanceService
  +-- SQLite / persistence
```

AIDO Code talks to exactly one thing: `orchestrator.engine.
OrchestratorEngine`. See `docs/ENGINE_CONTRACT.md` for its full method
surface and the snapshot types it returns.

## Rules this project never crosses

- AIDO Code never reads SQLite directly.
- AIDO Code never constructs `MVPManager`.
- AIDO Code never constructs `WorkerSelector`.
- AIDO Code never constructs `QuotaManager`.
- AIDO Code never knows the internal structure of any orchestrator Store.
- AIDO Code never chooses a worker itself.
- AIDO Code never decides whether a WorkItem is done.

Every one of those decisions belongs to the engine. AIDO Code's own job
is presentation, session/history management, and translating a user's
request ("what's the status?", "continue the project", "run it") into
one `OrchestratorEngine` call.

## What AIDO Code owns

- The terminal/REPL itself: prompt, rendering, colors, layout.
- Sessions: conversation history, which project/directory a session is
  attached to, resume-by-session-id. A UX concept; see "Session resume
  vs. project run" below.
- Commands (`/help`, `/status`, `/workers`, `/config`, `/validate`,
  `/run`, `/exit`, and later `/resume`, `/new`).
- Output rendering: human-readable text today; `json`/`stream-json`
  later (M5), built directly from `OrchestratorEngine`'s typed snapshots,
  never by parsing this project's own human-readable stdout.
- Natural-language interpretation of engine facts (M3). The engine
  supplies the facts; a conversational layer here may explain them, but
  never becomes a second authority on project state (`LLM IS NOT
  ORACLE`, the same invariant the engine itself is built on).

## Session resume vs. project run/resume: do not conflate these

Two entirely different concepts share the word "resume" in this
ecosystem, on purpose (matching Claude Code/Codex CLI conventions the
user already knows). They are never the same operation.

- **Session resume** (`aido resume`, `aido resume <id>`, `--resume`/`-r`,
  `--continue`/`-c`, `/resume`, `/new`; see `docs/CLI_SPEC.md`, M2) is
  about *this project's own UX state*: which conversation, which
  directory, which history. It is AIDO Code's own concern and touches
  nothing in the orchestrator's persisted state.
- **Project run/resume** is `OrchestratorEngine.run()` alone. The engine
  decides, from its own real persisted state (`READY`/`WAITING`/
  `RECOVERY_REQUIRED`/...), what "continuing the project" actually means.
  AIDO Code never re-implements that decision, and a session resume never
  substitutes for calling `.run()`.

Selecting or resuming a session may, as a UX convenience, immediately
also call `.run()` against the project that session is attached to, but
these remain two separate steps, never merged into one undifferentiated
"resume".

## Events / timeline

`OrchestratorEngine.run()` returns `RunResult.events` (`EngineEvent`
tuples: `kind`/`timestamp`/`project_id`/`mvp_id`/`work_item_id`/
`payload`). Today this is coarse: one `work_item.<status>` event per
WorkItem processed, because that is the granularity the orchestrator
itself currently exposes (`MVPManager` runs DEV A/DEV B/QA/merge
synchronously within one call, with no internal event bus yet). A richer
per-step timeline (M7) depends on that engine-side instrumentation
landing first; this project must never fabricate finer-grained progress
by guessing or by parsing subprocess output.
