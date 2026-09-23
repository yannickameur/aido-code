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

AIDO Code talks to exactly one thing:
`orchestrator.engine.OrchestratorEngine`. See `docs/ENGINE_CONTRACT.md`
for its full method surface and the snapshot types it returns.

## Who owns what

| AIDO Code owns | AI Dev Orchestrator owns |
|---|---|
| The terminal/REPL: prompt, rendering, colors, layout | Worker selection |
| Sessions: conversation history, project binding, resume-by-session-id | QA verdicts |
| Commands (`/help`, `/status`, `/workers`, `/config`, `/validate`, `/run`, `/exit`, later `/resume`/`/new`) | Merge decisions |
| Output rendering: text today, `json`/`stream-json` later (M5), built directly from typed snapshots, never by parsing this project's own stdout | WorkItem completion, all engine state transitions |
| Natural-language interpretation of engine facts (M3): may explain, never a second authority on state (`LLM IS NOT ORACLE`, the same invariant the engine itself is built on) | SQLite / all persisted state |

AIDO Code never crosses these lines:

- never reads SQLite directly;
- never constructs `MVPManager`, `WorkerSelector`, or `QuotaManager`;
- never knows the internal structure of any orchestrator Store;
- never chooses a worker itself;
- never decides whether a WorkItem is done.

Every one of those decisions belongs to the engine. AIDO Code's own job
is presentation, session/history management, and translating a user's
request ("what's the status?", "continue the project", "run it") into
one `OrchestratorEngine` call.

## Session resume vs. project run/resume

Two different concepts share the word "resume" in this ecosystem, on
purpose (matching Claude Code/Codex CLI conventions the user already
knows) — they are never the same operation:

- **Session resume** (`aido-code resume`, `aido-code resume <id>`,
  `--resume`/`-r`, `--continue`/`-c`, `/resume`, `/new`; see
  `docs/CLI_SPEC.md`, M2, and `docs/SESSION_CONTRACT.md`) is about
  *this project's own UX state*: which conversation, which directory,
  which history. It touches nothing in the orchestrator's persisted
  state.
- **Project run/resume** is `OrchestratorEngine.run()` alone. The
  engine decides, from its own real persisted state
  (`READY`/`WAITING`/`RECOVERY_REQUIRED`/...), what "continuing the
  project" actually means.

**Hard invariant (M2): session resume never automatically triggers the
engine.** Selecting, resuming, or creating a session only ever
restores/creates AIDO Code's own UX state — it loads the session,
restores its interaction history and project/config binding, and
restores display context. It never, by itself:

- calls `OrchestratorEngine.run()`;
- starts or resumes a WorkItem;
- selects a worker;
- causes a provider call (including `.probe_workers()`);
- mutates any engine state.

Advancing the project always requires a separate, explicit user action:
`/run` today, or a future M3 request explicitly interpreted as a run
intent.

## Events / timeline

`OrchestratorEngine.run()` returns `RunResult.events` (`EngineEvent`
tuples: `kind`/`timestamp`/`project_id`/`mvp_id`/`work_item_id`/
`payload`). Today this is coarse: one `work_item.<status>` event per
WorkItem processed, because that is the granularity the orchestrator
itself currently exposes (`MVPManager` runs DEV A/DEV B/QA/merge
synchronously within one call, with no internal event bus yet). A
richer per-step timeline (M7) depends on that engine-side
instrumentation landing first; this project must never fabricate
finer-grained progress by guessing or by parsing subprocess output.
