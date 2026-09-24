# Architecture

## Target shape

```
USER
  |
  v
AIDO CODE                     (this project — the product)
  |
  +-- AIDO global worker configuration (docs/PROJECT_CONTRACT.md §4)
  +-- aido.yaml manifest parser (§2)
  +-- ROADMAP.md deterministic parser (§3)
  +-- resources/ resolution + initial_prompt (§5)
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
  +-- WorkerRegistry (type/runtime; instantiation now caller-supplied, P13.5)
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

## Product boundary (M1.4)

**AIDO is the user product; `ai-dev-orchestrator` is its internal
engine.** A user project governed by AIDO never knows a worker, a
provider, a model, a `workers.yaml` path, or any path into
`ai-dev-orchestrator` — it knows exactly four things: which project,
which roadmap, which resources, which first instruction
(`aido.yaml`'s manifest shape, `docs/PROJECT_CONTRACT.md` §2). AIDO
resolves everything else:

- its own global worker pool (`docs/PROJECT_CONTRACT.md` §4), never a
  project-level concern, mirroring how `ai-dev-orchestrator`'s own
  P13.5 (that project's `ROADMAP.md` §13) stopped requiring the engine
  itself to own a project's worker configuration;
- a project's own `ROADMAP.md`, parsed deterministically (no LLM, no
  heuristic reading, fail closed — `docs/PROJECT_CONTRACT.md` §3) into
  the typed engine plan the engine actually consumes.

This is never a second orchestrator: the manifest/roadmap/resources
parsing built here produces exactly one thing —
`orchestrator.project_config.ProjectConfig`, constructed through its
own plain Python constructor and handed to `OrchestratorEngine` with an
AIDO-built `WorkerRegistry` injected
(`OrchestratorEngine(config, worker_registry=registry)`). See
`docs/PROJECT_CONTRACT.md` for the full contract.

## Who owns what

| AIDO Code owns | AI Dev Orchestrator owns |
|---|---|
| The terminal/REPL: prompt, rendering, colors, layout | Worker selection |
| Sessions: conversation history, project binding, resume-by-session-id | QA verdicts |
| Commands (`/help`, `/status`, `/workers`, `/config`, `/validate`, `/run`, `/exit`, later `/resume`/`/new`) | Merge decisions |
| Output rendering: text today, `json`/`stream-json` later (M5), built directly from typed snapshots, never by parsing this project's own stdout | WorkItem completion, all engine state transitions |
| Natural-language interpretation of engine facts (M3): may explain, never a second authority on state (`LLM IS NOT ORACLE`, the same invariant the engine itself is built on) | SQLite / all persisted state |
| AIDO's own global worker configuration/defaults, the `aido.yaml` manifest parser, the `ROADMAP.md` deterministic parser, `resources/` resolution (M1.4, `docs/PROJECT_CONTRACT.md`) | The `WorkerRegistry`/`WorkerSelector` *types/runtime* themselves, and every decision made from a `WorkerRegistry` once AIDO Code hands one in |

AIDO Code never crosses these lines:

- never reads SQLite directly;
- never constructs `MVPManager`, `WorkerSelector`, or `QuotaManager`;
- never knows the internal structure of any orchestrator Store;
- never chooses a worker itself;
- never decides whether a WorkItem is done;
- never re-implements worker selection just because it now builds the
  `WorkerRegistry` object itself (M1.4) — that object is still handed to
  the engine, which still owns every decision made from it.

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
