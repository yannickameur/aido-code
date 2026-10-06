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
| Sessions: minimal frontend state, optional project binding, resume-by-session-id (M2; no persistent conversation history in M3.1) | QA verdicts |
| Commands (`/help`, `/status`, `/workers`, `/config`, `/validate`, `/run`, `/exit`, later `/resume`/`/new`) | Merge decisions |
| Output rendering: text today, `json`/`stream-json` later (M5), built directly from typed snapshots, never by parsing this project's own stdout | WorkItem completion, all engine state transitions |
| The delivered M3 deterministic router for a closed set of natural-language intents; never a second authority on state | SQLite / all persisted state |
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

- **Session resume** (`aido resume`, `aido resume <id>`, `aido
  --continue`/`-c`, `/resume`, `/new`; see `docs/CLI_SPEC.md`, M2) is
  about *this project's own UX state*: a minimal local session and its
  optional project binding. It touches nothing in the orchestrator's
  persisted state.
- **Project run/resume** is `OrchestratorEngine.run()` alone. The
  engine decides, from its own real persisted state
  (`READY`/`WAITING`/`RECOVERY_REQUIRED`/...), what "continuing the
  project" actually means.

**Hard invariant (M2)**:

```
Session AIDO = minimal frontend state.
Project / WorkItem / MVP / QA / provider / quota / merge
  = state owned by ai-dev-orchestrator.
```

Creating or resuming a session never automatically triggers the engine.
It never, by itself:

- calls `OrchestratorEngine.run()`;
- calls `probe_workers()`;
- selects a worker;
- causes a provider call;
- mutates any engine state.

Advancing the project always requires a separate, explicit user action:
`/run` today, or a future M3 request explicitly interpreted as a run
intent. Full M2 acceptance criteria: `ROADMAP.md`, M2.

## Events / timeline

`OrchestratorEngine.run()` returns `RunResult.events` (`EngineEvent`
tuples: `kind`/`timestamp`/`project_id`/`mvp_id`/`work_item_id`/
`payload`, plus optional metadata fields, see below) — coarse: one
`work_item.<status>` event per WorkItem processed, emitted only once
that WorkItem's whole DEV A/DEV B/QA/merge sequence has already
finished. This coarse `events` tuple is unchanged by P18/P21;
P21 separately adds `RunResult.diagnostics` for failures.

Since `ai-dev-orchestrator` P18 (`DONE`, commit `23e68b7`, confirmed
present in the sibling engine this project's `.venv` actually imports —
see `docs/ENGINE_CONTRACT.md`), `OrchestratorEngine.run()` also accepts
an optional `on_event: Callable[[EngineEvent], None]` callback,
delivered synchronously in the same thread, live, once per real
progress fact, never batched/reordered: finer `dev_a.*`/`dev_b.*`/
`dev_fix.*`/`qa.*`/`git.*`/`run.*` kinds, each optionally carrying
`execution_id`/`phase`/`status`/`worker_id`/`worker_display_name`/
`provider`/`backend`/`profile_id`/`model`/`quality_tier`/
`reasoning_effort`/`commit_sha` — exactly what the engine actually
decided, `None` when genuinely unknown, never guessed from `worker_id`.
P21 (`DONE`, verified at engine SHA `6456c93`) adds progressive
`execution.output`, bounded-output `execution.output_truncated`, neutral
`execution.heartbeat`, and typed `FailureDiagnostic` entries through
`RunResult.diagnostics` (see `docs/ENGINE_CONTRACT.md`). This project
now passes `on_event` through `EngineClient.run()` and renders these
public facts with `LiveRunRenderer`; CLI/REPL interruption handling shares
`run_interruptibly`. No Git/SQLite/`.ralph` scraping is added. The real
M3.1 acceptance exposed a remaining defect: raw backend JSON can contain
private reasoning, which terminal sanitization alone does not suppress.
See `ROADMAP.md`; the no-chain-of-thought acceptance is not yet met.
