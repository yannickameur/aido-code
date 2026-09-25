# ROADMAP — AIDO Code

Functional roadmap for AIDO Code, the interactive terminal frontend for
AI Dev Orchestrator. See `README.md` for what this project is,
`ARCHITECTURE.md` for the hard rules it never crosses, and
`docs/ENGINE_CONTRACT.md` for the exact engine API it is built against.

No M0: the engine/frontend decoupling that made this project possible
is P13 of `ai-dev-orchestrator`'s own `ROADMAP.md`, already `DONE`
there. This roadmap starts at M1.

## Where we stand

DONE: M1, M1.1, M1.2, M1.3, M1.4, M8
NEXT: M2, entirely not started (unaffected/unblocked by M1.4/M8)
FUTURE: M3-M7

M8 completed **out of numeric order**, right after M1.4: M1.4 itself
delivered the functional parity (`init`/`validate`/`run`/`status`) M8
was gated on, so the binary-name cutover became a small, immediate
packaging follow-up rather than a separately-scheduled future milestone
— see M8 below.

| Milestone | Status |
|---|---|
| M1 — Minimal interactive shell | `DONE` (see `docs/M1_REFERENCE_RUN.md`) |
| M1.1 — CLI conventions and standalone install | `DONE` (see `docs/M1_1_REFERENCE_RUN.md`) |
| M1.2 — Rich provider quota status | `DONE` (see `M1_2_SPEC.yaml`) |
| M1.3 — Audit hardening | `DONE` (see `M1_3_SPEC.yaml`) |
| M1.4 — Autonomous AIDO project contract | `DONE` (see `docs/PROJECT_CONTRACT.md`; real WI-M1.4-07 failure + recovery split, see M1.4 below) |
| M2 — Sessions and resume | `SPECIFIED`, not started, entirely unaffected by M1.4/M8 (see `M2_SPEC.yaml`, `docs/SESSION_CONTRACT.md`) |
| M3 — Natural-language piloting | `À VOTER` |
| M4 — Non-interactive mode | `À VOTER` |
| M5 — Structured output | `À VOTER` |
| M6 — Doctor/diagnostics | `À VOTER` |
| M7 — Real-time timeline | `À VOTER` |
| M8 — `aido` command cutover | `DONE` (2026-09-25) — completed right after M1.4, see M8 below |
| M9+ | `À VOTER`, only per real, demonstrated need |

**`MVP_SPEC.yaml`/`M1_1_SPEC.yaml`/`M1_2_SPEC.yaml`/`M1_3_SPEC.yaml` are
historical acceptance records of M1/M1.1/M1.2/M1.3 as they were actually
built — kept as proof, never deleted, but no longer the model for how a
future milestone's contract is authored.** Starting at M1.4,
`ROADMAP.md` is the single functional source of truth for a *project*
this product governs (see M1.4 below and `docs/PROJECT_CONTRACT.md`);
this file (AIDO Code's own roadmap) stays free-form prose by convention,
not an instance of the deterministic grammar M1.4 defines for the
projects AIDO governs.

## M1 — Minimal interactive shell (`DONE`)

Objective: ship the first usable frontend. Commands: `/help`, `/status`,
`/workers`, `/config`, `/validate`, `/run`, `/exit`; see
`docs/CLI_SPEC.md`.

WI-01 through WI-07 (`aido.example.yaml`) were completed by AI Dev
Orchestrator's real WorkItem Flow. Acceptance contract: `MVP_SPEC.yaml`.
Full factual record, including a real engine defect it found and its
fix: `docs/M1_REFERENCE_RUN.md`.

Acceptance criteria (also `MVP_SPEC.yaml`):

- detects an `aido.yaml` in the current/a given directory;
- connects to the real public engine (`orchestrator.engine.
  OrchestratorEngine`), never a mock, via the engine's own injection
  seams in tests (`provider_adapters`/`subprocess_runner`; see
  `docs/ENGINE_CONTRACT.md`);
- `/status` reflects real persisted project state; `/workers` the real
  configured registry; `/validate` real config validation;
- `/run` drives the real engine and is also how a project resumes;
- no orchestration logic (worker selection, QA verdicts, merge
  decisions) is ever duplicated here;
- tests are offline (fake provider adapters, fake Ralph subprocess).

## M1.1 — CLI conventions and standalone install (`DONE`)

A small technical increment between M1 and M2; not part of M2.
WI-M1.1-01 through WI-M1.1-04 (`aido.m1_1.example.yaml`) were completed
by AI Dev Orchestrator's real, governed WorkItem Flow. Acceptance
contract: `M1_1_SPEC.yaml`. Full factual record, including a real
Git-commit-identity engine defect it found:
`docs/M1_1_REFERENCE_RUN.md`.

Covers:

- the engine dependency's PyPI rename, reflected in `pyproject.toml`
  (`ai-dev-orchestrator>=0.1.2`), import path unchanged;
- `EngineClient.probe_workers()`, delegating to
  `OrchestratorEngine.probe_workers()`;
- `/status` showing the full worker list with zero provider probes;
  `/status --probe` adding one real `probe_workers()` call;
- `/workers` staying static, gaining `/workers --probe` sharing the
  same probe/rendering path as `/status --probe` (no duplicated
  logic);
- `/run` unchanged: project start/resume only; no new project-level
  `/resume` command;
- regression proof that M1's existing commands/criteria are not
  broken.

### WorkItems

Drafted, portable template only (`aido.m1_1.example.yaml`); not created
in any orchestrator runtime state.

1. **WI-M1.1-01** — Correct AIDO Code engine dependency metadata.
2. **WI-M1.1-02** — Extend `EngineClient` with `probe_workers()`.
3. **WI-M1.1-03** — Improve `/status` and `/workers` UX.
4. **WI-M1.1-04** — Regression/acceptance tests, plus docs.

Full criteria: `aido.m1_1.example.yaml`. Full contract:
`M1_1_SPEC.yaml`.

## M1.2 — Rich provider quota status (`DONE`)

A small technical increment after M1.1 and before M2; not part of M2.
WI-M1.2-01/02 (`aido.m1_2.example.yaml`) were completed by AI Dev
Orchestrator's real, governed WorkItem Flow. Acceptance contract:
`M1_2_SPEC.yaml`.

Covers:

- engine dependency minimum raised to `ai-dev-orchestrator>=0.1.3`
  (introduces `ProviderSnapshot.quota_windows`/`reset_credits`);
- `EngineClient` exposing what `/status --probe`/`/workers --probe`
  need directly from `OrchestratorEngine.probe_workers()`, no
  provider-specific logic of its own;
- `/status --probe` rendering utilization/remaining/reset_at/reset
  credits per quota window, never fabricated when unknown;
- `/workers --probe` sharing the same rendering path (no duplicated
  logic);
- quota rendered once per provider actually probed, never once per
  worker;
- `/status`/`/workers` (no flags) and `/run` entirely unregressed.

### WorkItems

1. **WI-M1.2-01** — Consume richer `ProviderSnapshot`.
2. **WI-M1.2-02** — Regression and clean-install UX.

Full criteria: `aido.m1_2.example.yaml`. Full contract:
`M1_2_SPEC.yaml`.

## M1.3 — Audit hardening (`DONE`)

A small technical increment after M1.2 and before M2; not part of M2.
Prepared in response to a real technical audit (external review,
2026-09-23) of AIDO Code at SHA `e916cfa8a247bc9ac848e59729dc9da4b5f25e7e`,
which found:

| ID | Severity | Finding |
|---|---|---|
| F-01 | LOW | Unknown CLI launch arguments are silently ignored instead of rejected. |
| F-02 | MEDIUM | ANSI/control characters from engine snapshot values reach the terminal unneutralized. |
| F-03 | LOW | `docs/ENGINE_CONTRACT.md` omits `worker_display_name` (a real `ExecutionSnapshot` field, P13.3). |

The audit also raised six M2 design risks (DR-1 through DR-6) —
resolved directly in `docs/SESSION_CONTRACT.md`, `M2_SPEC.yaml`, and
`aido.m2.example.yaml` as documentation/spec work (see M2's own section
below); no code changes were needed for that part, since M2 has no code
yet.

**Not manually coded**: per `CONTRIBUTING.md`, F-01/F-02 require real
functional code (`src/aido_code/*`) and must be produced by AI Dev
Orchestrator's own governed WorkItem Flow, never written directly here.
F-03 is documentation-only and may be fixed directly by the maintainer,
but is instead folded into WI-M1.3-03's own acceptance criteria below
to avoid two contradictory commits touching the same file.

Must cover:

- unknown CLI launch arguments rejected with a clear message and a
  non-zero exit code, never silently ignored; normal, no-argument
  launch stays unchanged; no M2 flags (`--resume`/`-r`/`--continue`/
  `-c`) implemented yet — only the validation groundwork for them;
- every dynamic value rendered to the terminal that originates from an
  engine snapshot is sanitized against ESC/ANSI sequences, bare CR, and
  injected LF/other control characters, through one shared
  sanitization function reused everywhere — never a package if the
  standard library suffices; engine DTOs themselves are never mutated,
  only the rendering layer;
- `docs/ENGINE_CONTRACT.md` corrected to document `worker_display_name`
  (F-03), as part of this milestone's own QA rather than a separate
  maintainer commit;
- M1/M1.1/M1.2 entirely unregressed, tests entirely offline, no real
  provider call anywhere in this milestone's own QA.

### Real run (2026-09-23)

A human GO was given, then `aido run` was executed against a local
config copied from `aido.m1_3.example.yaml` (preserved as
`aido.m1_3.local.yaml`, same `project.id`/`state_dir` as every prior
milestone, `mvp.id: mvp-0.1.3`, `qa_protected_paths` covering
`tests/test_e2e.py`/`tests/test_repl.py`), letting AI Dev Orchestrator
govern WI-M1.3-01 through WI-M1.3-03 itself. All 3 WorkItems reached
`completed` in 4 cycles (`cycles_run=4 all_terminal=True`):

| WorkItem | DEV A | DEV B | Final SHA |
|---|---|---|---|
| WI-M1.3-01 | Alice (anthropic) | Victor (openai) | `288bdde` |
| WI-M1.3-02 | Alice (anthropic) | Victor (openai), then a real DEV FIX by Alice after a real QA FAIL | `51e9e32` |
| WI-M1.3-03 | Alice (anthropic) | Victor (openai) | `4040976` |

**`qa_protected_paths` (AUD-1, `ai-dev-orchestrator` P13.4) fired for
real, for the first time, on WI-M1.3-02**: DEV A's first attempt added
the new terminal-safety tests directly into the protected
`tests/test_repl.py`. QA correctly recorded `FAIL` — `"a protected test
changed without a versioned authorization"` — never a silent `PASS`.
The resulting DEV FIX (commit `51e9e32`, "Move terminal-safety tests
out of protected test_repl.py") moved the new tests to their own file
instead of touching the protected one, and QA then passed. This is the
governance invariant this repository's own `docs/PROJECT_CONFIG.md`
describes working exactly as designed, on a real WorkItem, not a test
fixture.

Every commit above is correctly attributed to its real worker identity
(`git log`; P13.2 attribution — verified, no
`WorkerCommitIdentityMismatchError`). Final result: unknown CLI launch
arguments now rejected explicitly (F-01); a shared sanitizer neutralizes
ESC/ANSI/control characters from every engine-snapshot-derived terminal
value (F-02); `docs/ENGINE_CONTRACT.md` documents
`ExecutionSnapshot.worker_display_name` (F-03); 70 offline tests passing
(was 53). No manual code correction was made by any human/assistant at
any point.

### WorkItems

1. **WI-M1.3-01** — CLI launch argument validation (F-01). `completed`.
2. **WI-M1.3-02** — Terminal rendering safety (F-02). `completed`
   (real rework cycle: protected-test violation caught, corrected).
3. **WI-M1.3-03** — Regression + engine contract fix (F-03). `completed`.

Full acceptance criteria per WorkItem: `aido.m1_3.example.yaml`. Full
functional contract these WorkItems build toward: `M1_3_SPEC.yaml`.

## M1.4 — Autonomous AIDO project contract (`DONE`)

**Decision**: AIDO is the user product; `ai-dev-orchestrator` is its
internal engine. Before this milestone, a user project's `aido.yaml`
duplicated the engine's own schema v1 — worker registry path,
hand-written WorkItems in YAML, execution/git policy — the exact
coupling that project's own P13.5 closed on the engine side (see
`ai-dev-orchestrator`'s `ROADMAP.md` §13: `workers:` optional,
`OrchestratorEngine`/`ProjectRuntime` accept an injected
`WorkerRegistry`). M1.4 is AIDO Code's own side of that boundary:

```
AIDO
├── CLI / UX
├── AIDO global configuration (workers)
├── aido.yaml parser (manifest)
├── ROADMAP.md parser (deterministic)
├── resources/
│
└── OrchestratorEngine
       ↓
   ai-dev-orchestrator
```

A user project knows **no worker, no provider, no model, no
`workers.yaml`, no path into `ai-dev-orchestrator`.** It knows exactly
four things: which project, which roadmap, which resources, which first
instruction.

**Full grammar/schema, authoritative**: `docs/PROJECT_CONTRACT.md`
(manifest schema, `ROADMAP.md`'s deterministic Markdown grammar and
APPROVED/DRAFT gate, resources confinement, `initial_prompt`
combination, AIDO's own global worker configuration, and exactly how
`validate`/`run`/`status`/`workers`/`config` behave). This section stays
short and points there, the same way M2's own section points to
`docs/SESSION_CONTRACT.md`.

**New manifest shape** (`aido.yaml`, replacing the schema every prior
milestone used):

```yaml
schema_version: 1

project:
  id: myproject
  name: MyProject
  workspace: "."

roadmap: "./ROADMAP.md"

resources: "./resources"

initial_prompt: >
  Read ROADMAP.md and the project resources referenced by it before doing
  any work. Execute only the currently approved milestone. Respect its
  scope, dependencies, acceptance criteria and explicit out-of-scope
  decisions. Apply REUSE FIRST, KISS and YAGNI.
```

No `workers:`/`providers:`/`models:`/`mvp:`/`work_items:`/`qa:`, and no
AIDO-global policy of any kind, ever belongs in this file — see
`docs/PROJECT_CONTRACT.md` §2 for the exhaustive allowed-key list and
where `execution.permission_mode`/`git.base_branch` now come from
instead (explicit, documented defaults; no per-project override yet,
`À VOTER` if a real need is ever established).

**`ROADMAP.md` replaces `MVP_SPEC.yaml`'s future role**: one
deterministic Markdown grammar (`docs/PROJECT_CONTRACT.md` §3) carries
vision, sources, the current milestone (status/objective/acceptance
criteria/WorkItems/dependencies/capabilities/QA/out-of-scope), and
future milestones — fail-closed, no LLM parsing, no heuristic reading,
exactly one `Current milestone`, unique WorkItem ids, validated
dependencies, cycle detection (mirroring `ai-dev-orchestrator`'s own
`project_config._validate_work_items` DFS), deterministic QA. A
milestone only runs when `Status: APPROVED`; `DRAFT` validates but is
refused cleanly by `run`.

**AIDO's own worker configuration** (`docs/PROJECT_CONTRACT.md` §4):
`$XDG_CONFIG_HOME/aido/workers.yaml`, falling back to
`~/.config/aido/workers.yaml`, falling back — with no file ever
auto-materialized — to AIDO Code's own packaged default workers (a
self-contained copy, never a read of `ai-dev-orchestrator`'s own
packaged `default_workers.yaml`, which stays legacy/CLI-only per
P13.5). No project ever references a worker/provider/model/`workers.yaml`
path again.

**Typed engine plan** (`docs/PROJECT_CONTRACT.md` §6): the manifest +
current milestone + resources/`initial_prompt` are transformed into a
real `orchestrator.project_config.ProjectConfig`, built through its own
plain Python constructor (never `.load()`, never a second, parallel
"plan" type — REUSE FIRST) with `workers_registry_path=None` always, and
the AIDO global `WorkerRegistry` injected directly:
`OrchestratorEngine(config, worker_registry=registry)`. Exactly the
engine seam `ai-dev-orchestrator`'s P13.5 built for this — never
`.open(config_path)` (there is no more `ProjectConfig`-shaped YAML
file). `WorkerSelector` remains the sole owner of selection
(`ARCHITECTURE.md`, unchanged); nothing here re-implements it.

**Commands** (`docs/PROJECT_CONTRACT.md` §7): `aido-code init . name`
now scaffolds the new manifest shape plus a `DRAFT` `ROADMAP.md` and an
empty `resources/`, same Git behavior as `ai-dev-orchestrator`'s own
P1.1 guided bootstrap (Git absent/failed → scaffold kept, non-zero exit,
manual instructions, nothing auto-installed). `validate` stays
provider-free and validates manifest + roadmap structure + resources
confinement + that the AIDO registry itself resolves. `run` requires
`Status: APPROVED`, refused cleanly otherwise, before any provider call.
`/workers`/`/workers --probe` need no new code path — the engine is
always constructed with the AIDO registry injected, so they already show
AIDO's own workers for free. `/config` shows manifest + roadmap facts
alongside the existing engine-derived facts. `/status` combines
roadmap-level facts with the real, unchanged `OrchestratorEngine.
status()`.

**Out of scope for M1.4, explicitly**: M2 sessions (untouched,
unstarted, unblocked); `qa_protected_paths` authored from `ROADMAP.md`;
a per-project `execution`/`git` override; any migration of
`M2_SPEC.yaml`/`aido.m2.example.yaml`'s own content into this grammar.

**SPEC migration debt, noted, not started**: `M2_SPEC.yaml` and
`aido.m2.example.yaml` still describe a real, unimplemented future
(M2). Once M1.4 lands, they are the last documents in this repository
still shaped like the pre-M1.4 model. Their relevant content must be
migrated into `ROADMAP.md`'s own deterministic grammar (`docs/
PROJECT_CONTRACT.md` §3) **before** a future GO M2, so this project
never maintains two sources of functional truth at once — that
migration is real, separate work, not started by M1.4, and never a
reason to delay or reshape M1.4 itself.

### WorkItems

Drafted for AI Dev Orchestrator's real, governed WorkItem Flow
(`CONTRIBUTING.md`). Full acceptance criteria per WorkItem below; the
local, untracked config that reproduces them for a real governed run is
never committed (`CONTRIBUTING.md`, "Local configuration").

1. **WI-M1.4-01** — AIDO global worker configuration + packaged
   defaults.

   Dependencies: none. Capabilities: development.

   Acceptance criteria:
   - A new module resolves, in order: `$XDG_CONFIG_HOME/aido/
     workers.yaml`; else `~/.config/aido/workers.yaml`; else AIDO
     Code's own packaged default workers (a real file bundled inside
     this package's own distribution, resolved through
     `importlib.resources`, never a read of `ai-dev-orchestrator`'s own
     packaged `default_workers.yaml`).
   - The resolved file (override or packaged default) is loaded with
     `orchestrator.worker_registry.WorkerRegistry.load(path)` — no new
     worker-parsing logic of AIDO Code's own.
   - No file is ever auto-materialized on disk just to make this work;
     the packaged default is used directly, in memory, when no override
     exists.
   - Never references `ai-dev-orchestrator`'s own `config/workers.yaml`,
     `../ai-dev-orchestrator/config/workers.yaml`, or
     `~/.config/ai-dev-orchestrator/workers.yaml` anywhere in this path.
   - A malformed override file fails closed with a clear message
     (reusing `WorkerRegistryError`'s existing taxonomy), never a silent
     fallback to the packaged default.
   - Offline tests cover: no override present (packaged default used);
     `XDG_CONFIG_HOME` set with a real override file (used); `HOME`
     fallback with a real override file (used); a malformed override
     (fails closed); the packaged default itself loads successfully and
     declares at least one enabled worker on at least one provider.

2. **WI-M1.4-02** — Project manifest (`aido.yaml`) parser.

   Dependencies: none. Capabilities: development.

   Acceptance criteria:
   - A new module parses the manifest shape in `docs/PROJECT_CONTRACT.md`
     §2: `schema_version` (must be `1`), `project.id`/`name`/`workspace`,
     `roadmap`, `resources`, `initial_prompt` — exhaustively, no other
     top-level key accepted.
   - `project.id` validated with the same character-safety pattern
     `ai-dev-orchestrator`'s own `project_config._PROJECT_ID_PATTERN`
     uses.
   - `roadmap`/`resources`/`workspace` resolve relative to the directory
     containing `aido.yaml` (never the caller's cwd), `~` expanded;
     `roadmap`/`resources` must resolve to a location inside `workspace`
     (no `..` traversal, no symlink escape) — fail closed otherwise.
   - The same secret-substring guard-rail `ai-dev-orchestrator`'s own
     `project_config`/`worker_registry` modules use is reproduced here.
   - `workers`/`providers`/`models`/`mvp`/`work_items`/`qa`/`execution`/
     `git`, or any other unknown top-level key, is rejected, fail
     closed, before any field is trusted.
   - Offline tests cover: a valid minimal manifest; each excluded key
     present (rejected); a secret-like field (rejected); a `roadmap`/
     `resources` path escaping `workspace` via `..` (rejected); a
     symlink escaping `workspace` (rejected); a missing/non-directory
     `workspace` (rejected); relative-path resolution proven relative to
     the manifest's own directory, not the caller's cwd.

3. **WI-M1.4-03** — Deterministic `ROADMAP.md` parser + APPROVED/DRAFT
   gate.

   Dependencies: none. Capabilities: development.

   Acceptance criteria:
   - A new module parses exactly the grammar in `docs/PROJECT_CONTRACT.md`
     §3: exactly one `## Current milestone`; `Status: APPROVED` or
     `Status: DRAFT` (byte-exact, any other value rejected); `### ID`/
     `### Objective` required; `### Acceptance criteria` optional;
     `### WorkItems` required, one or more `#### <id> — <title>` entries
     (exact em-dash separator), each with `Dependencies:`/
     `Capabilities:` lines and a non-empty `Acceptance criteria:` bullet
     list; `### QA` optional, same `<id> — <title>` shape, each with
     `Kind:`/`Required:`/`Timeout:`/`Argv:` (JSON array of non-empty
     strings, parsed via the stdlib `json` module); `### Out of scope`
     optional bullets; `## Sources` optional top-level bullets.
   - WorkItem ids are unique within the document; a dependency
     referencing an id not declared in the same `WorkItems` section
     fails closed; a dependency cycle is detected and fails closed,
     using the same fail-closed DFS (white/gray/black) algorithm shape
     `ai-dev-orchestrator`'s own `project_config._validate_work_items`
     already implements — mirrored here, not imported, and never a
     different algorithm.
   - Returns a typed, structured result (milestone status/id/objective/
     acceptance criteria, WorkItems, QA commands, out-of-scope bullets,
     sources) — never a raw dict, never re-parsed downstream.
   - `validate` succeeds for both `DRAFT` and `APPROVED` as long as the
     document is structurally valid; reports which one and whether it
     is executable. `run`'s own APPROVED requirement is a separate,
     later gate (WI-M1.4-07), not this WorkItem's own concern beyond
     exposing the parsed `status` field.
   - Offline tests cover: a valid `DRAFT` roadmap; a valid `APPROVED`
     roadmap; zero/two `## Current milestone` sections (both rejected);
     an unrecognized `Status:` value (rejected); a duplicate WorkItem id
     (rejected); an unknown dependency (rejected); a dependency cycle
     (rejected, 2-node and 3-node cases); a WorkItem with zero
     acceptance criteria (rejected); a malformed `Argv:` (not JSON, not
     an array, a non-string element — each rejected); a well-formed
     `### Out of scope`/`## Sources` section (parsed, never dropped).

4. **WI-M1.4-04** — Resources resolution/confinement + `initial_prompt`.

   Dependencies: WI-M1.4-02, WI-M1.4-03. Capabilities: development.

   Acceptance criteria:
   - Each `## Sources` entry (WI-M1.4-03's parsed output) is resolved
     relative to `workspace` (the manifest's own `resources` base, per
     `docs/PROJECT_CONTRACT.md` §5), confined inside `workspace` (no
     `..`, no symlink escape), and must exist on disk — a missing
     declared source fails closed.
   - No file under `resources/` is ever treated as normative unless
     `## Sources` explicitly names it — an unreferenced file there is
     inert, never auto-discovered/auto-included.
   - Nothing in this path ever writes to a resource file.
   - `initial_prompt` + the current milestone's own `### Objective` +
     the resolved `## Sources` list are combined into one MVP objective
     string via the exact, fixed, `---`-delimited template in
     `docs/PROJECT_CONTRACT.md` §5 — never a second template, never a
     per-WorkItem duplication of `initial_prompt`, provenance of each
     section stays explicit in the resulting string.
   - Offline tests cover: a missing `resources/` directory (rejected); a
     missing declared `## Sources` file (rejected); a `..`-traversal
     attempt in a `## Sources` entry (rejected); a symlink escaping
     `workspace` (rejected); the combined objective string proven to
     contain all three sections in order, for two different fixtures
     (proving no hardcoding).

5. **WI-M1.4-05** — Transform the AIDO project contract into a typed
   engine plan + inject `WorkerRegistry`.

   Dependencies: WI-M1.4-01, WI-M1.4-02, WI-M1.4-03, WI-M1.4-04.
   Capabilities: development.

   Acceptance criteria:
   - Builds a real `orchestrator.project_config.ProjectConfig` via its
     own plain Python constructor (`ProjectIdentity`/`ExecutionConfig`/
     `GitConfig`/`MVPConfig`/`WorkItemConfig`/`ValidationCommand`,
     imported from `ai-dev-orchestrator` unchanged) exactly per the
     field-by-field mapping in `docs/PROJECT_CONTRACT.md` §6 —
     `workers_registry_path` always `None`; `state_dir` computed with
     the identical formula `ai-dev-orchestrator`'s own
     `project_config._default_state_dir(project_id)` uses;
     `permission_mode=ExecutionPermissionMode.STANDARD`;
     `git.base_branch="main"`.
   - `workspace` is confirmed to be inside a real Git work tree before
     the plan is ever handed to the engine (the same fail-closed check
     `ProjectConfig.load()` already performs, reproduced here since this
     path never calls `.load()`).
   - The plan is handed to `OrchestratorEngine(config,
     worker_registry=registry, ...)` — the plain constructor, never
     `.open(config_path)`.
   - Offline tests cover: a full manifest+roadmap+resources fixture
     produces a `ProjectConfig` with `workers_registry_path is None`;
     the injected `WorkerRegistry` is proven to reach
     `OrchestratorEngine.workers()`/`.validate()` (real engine call,
     fake provider adapters/subprocess runner); two different project
     fixtures (different `project.id`) sharing one injected
     `WorkerRegistry` instance both work independently; the computed
     `state_dir` for `project.id="aido-code"` equals the exact path
     every prior milestone's own persisted state already uses (non-
     regression: M1.4 must never orphan or duplicate M1-M1.3's own
     persisted WorkItems); a non-Git `workspace` is rejected before any
     engine call.

6. **WI-M1.4-06** — Project bootstrap `init`.

   Dependencies: WI-M1.4-02, WI-M1.4-03. Capabilities: development.

   Acceptance criteria:
   - `aido-code init <parent-path> <project-name>` (current, pre-M8
     binary name) creates: `.git/`, `.gitignore`, `README.md`,
     `ROADMAP.md` (one placeholder milestone, `Status: DRAFT`,
     structurally valid per WI-M1.4-03's own grammar), `aido.yaml` (the
     WI-M1.4-02 manifest shape), `resources/` (a short
     `resources/README.md` stub, since Git does not track empty
     directories).
   - `aido-code validate` succeeds against the fresh scaffold,
     reporting `Current milestone: DRAFT` / `Not executable`.
     `aido-code run` refuses cleanly (non-zero exit, no provider call)
     until the milestone is edited to `Status: APPROVED`.
   - Git behavior identical to `ai-dev-orchestrator`'s own P1.1 guided
     bootstrap: `git init -b main && git add . && git commit -m
     "Initialize AIDO project"`; Git absent or any step failing keeps
     the scaffold, returns non-zero exit, prints the exact manual
     commands, installs nothing automatically. Target-path validation
     (absent/empty only, no `--force`, `~` expansion, path-traversal/
     symlink rejection for the project name) mirrors that same P1.1
     contract.
   - Offline tests cover: a full successful bootstrap (all files, Git
     history); Git missing (scaffold kept, exit non-zero, instructions
     printed); a Git step failing (same); a nonempty target (refused,
     no files touched); a path-like/unsafe project name (rejected).

7. **WI-M1.4-07** — `validate`/`run`/`status`/`workers`/`config`
   integration. **`FAILED` (real, historical) — superseded by
   07A..07D, never redefined, never deleted.**

   Dependencies: WI-M1.4-05, WI-M1.4-06. Capabilities: development.

   **Real outcome (first governed run, 2026-09-24)**: DEV A (Alice)
   reached Ralph's own `max_iterations` limit (5 iterations, 8m06s,
   exit code 2) without ever committing — this WorkItem's own scope
   (five separate command integrations: `validate`/`run`/`status`/
   `workers`/`config`) was too large for one Ralph loop budget. No
   DEV B/DEV FIX/QA cycle was ever reached for it; its own branch has
   zero diff from `main`. Alice's leftover uncommitted working-tree
   changes were never reviewed, never QA'd, never committed — preserved
   only as a local `git stash` for diagnostic inspection, never applied
   or cherry-picked (`CONTRIBUTING.md`'s core rule: only the governed
   flow's own accepted commits count as real product). This WorkItem's
   own id is retired, never reused, never manually marked otherwise
   than `FAILED` in persisted engine state — see §3 below for the
   recovery split.

   Acceptance criteria (as originally drafted, kept verbatim as the
   historical record — never satisfied by this WorkItem itself):
   - `aido-code validate`: provider-free; validates manifest + roadmap
     structure + resources confinement + that the AIDO `WorkerRegistry`
     itself resolves; prints exactly the two example blocks in
     `docs/PROJECT_CONTRACT.md` §7 (`DRAFT`/`Not executable` or
     `APPROVED`/`Executable`).
   - `aido-code run`: validates; requires `Status: APPROVED`, refused
     cleanly otherwise (non-zero exit, no provider/engine construction
     attempted); loads the AIDO `WorkerRegistry`; builds the typed plan
     (WI-M1.4-05); calls `OrchestratorEngine(...).run()`. No
     orchestration logic is duplicated.
   - `/workers`/`/workers --probe`: no new rendering path — already show
     the AIDO-injected registry via the existing engine-backed code
     path (proven by a test that the AIDO packaged/overridden registry
     is exactly what `/workers` renders).
   - `/config`: shows manifest facts (project id/name/workspace,
     resolved `roadmap`/`resources` paths, `initial_prompt`) plus the
     current milestone id/status plus the existing engine-derived facts
     (`enabled_worker_count`/`providers`/`permission_mode`/
     `base_branch`/`qa_command_count`) — never a raw file dump.
   - `/status`: combines roadmap-level facts (milestone id/status) with
     the real, unchanged `OrchestratorEngine.status()` snapshot; never
     fabricates a WorkItem/MVP status the engine has not actually
     persisted.
   - Offline tests cover each command's new/changed behavior, plus a
     `DRAFT`-project `run` refusal proven to reach zero provider calls
     (fake adapters scripted to raise if invoked, mirroring this
     project's own existing test conventions).

8. **WI-M1.4-08** — Regression, clean-install, and portability
   acceptance. **`BLOCKED` (real, historical:
   `dependency cannot complete: ['WI-M1.4-07']`) — superseded by 08R,
   never redefined, never deleted.**

   Dependencies: WI-M1.4-07. Capabilities: development.

   Acceptance criteria (as originally drafted, kept verbatim as the
   historical record — never attempted, blocked by WI-M1.4-07's own
   failure before any execution):
   - `pytest -q` passes for the whole package, offline, zero real
     provider/Ralph calls anywhere in the suite.
   - One offline acceptance test proves a clean-install shape (a fixed,
     fake `HOME`/`XDG_CONFIG_HOME`, no `~/.config/ai-dev-orchestrator/`
     anywhere, no sibling-checkout worker path referenced anywhere) end
     to end: `init` → `validate` (`DRAFT`) → edit to `APPROVED` →
     `validate` (`Executable`) → `run` reaching a real (faked
     provider/subprocess) WorkItem Flow cycle.
   - M1/M1.1/M1.2/M1.3's own already-covered command behaviors
     (`/help`, `/exit`, blank-line handling, `--probe` rendering, CLI
     launch-argument validation, terminal sanitization) remain passing,
     unregressed, adjusted only where this milestone's own contract
     necessarily changes what `aido.yaml`/`/config` mean.
   - This is the final gate for MVP 0.1.4: `pytest -q` green, `git diff
     --check` clean.

### Recovery split (after the real WI-M1.4-07 failure, 2026-09-24)

`WI-M1.4-07`'s own scope (five separate command integrations in one
WorkItem) exceeded one Ralph loop's iteration budget. Recovery keeps
`WI-M1.4-07`/`WI-M1.4-08`'s own ids **retired forever** — never reused,
never manually redefined — and splits the remaining, still-real work
into five smaller, independently-bounded WorkItems below, each scoped
to fit comfortably inside one Ralph loop. This is still M1.4, not a new
milestone.

9. **WI-M1.4-07A** — Project command context + `validate` integration.

   Dependencies: WI-M1.4-05, WI-M1.4-06. Capabilities: development.

   Acceptance criteria:
   - Introduces (or reuses, if WI-M1.4-05 already offers enough of it)
     one cohesive project-command loading path for the modern AIDO
     contract: loads the project `aido.yaml` manifest, the
     deterministic `ROADMAP.md`, resources, and the AIDO global
     `WorkerRegistry` — never constructs or probes a provider merely to
     validate.
   - `aido-code validate` is migrated onto this same path — never a
     second, parallel validation implementation kept alongside it.
   - Validates, in order: the manifest; the roadmap grammar; resources
     confinement/existence; that the AIDO `WorkerRegistry` itself
     resolves.
   - `Status: DRAFT` → `Current milestone: DRAFT` / `Not executable`,
     successful validation. `Status: APPROVED` → `Current milestone:
     APPROVED` / `Executable`.
   - No provider call. No `OrchestratorEngine.run()`. No parsing logic
     already implemented by WI-M1.4-02/03/04/05 is duplicated — this
     WorkItem wires existing pieces together, it does not re-implement
     any of them.
   - Kept narrowly scoped: no `run`/`status`/`workers`/`config` work
     here beyond the minimal, reusable plumbing WI-M1.4-07B/C/D
     genuinely need (e.g. the one project-command-context loader
     itself) — never a preemptive implementation of their own scope.
   - Offline tests cover: `DRAFT`; `APPROVED`; an invalid manifest; an
     invalid roadmap; an invalid/missing resource; a malformed AIDO
     workers override.

10. **WI-M1.4-07B** — `run` integration + APPROVED gate.

    Dependencies: WI-M1.4-07A. Capabilities: development.

    Acceptance criteria:
    - `aido-code run` uses the project context WI-M1.4-07A produces —
      never a second, parallel loading path.
    - `Status: DRAFT`: fails cleanly, non-zero exit, no provider probe,
      no provider adapter execution, no `OrchestratorEngine` run
      attempted.
    - `Status: APPROVED`: loads the AIDO global `WorkerRegistry`; builds
      the typed `ProjectConfig` through the existing WI-M1.4-05
      transformation; injects the registry using the engine's P13.5
      public seam (`worker_registry=`); calls only public
      `OrchestratorEngine` APIs; invokes `.run()`.
    - AIDO never implements worker selection, DEV A/DEV B scheduling,
      QA verdicts, or Git merge logic — every one of those stays the
      engine's own.
    - Tests use fake provider adapters/a fake Ralph subprocess, exactly
      this repository's own established convention.
    - At least one offline test proves `APPROVED` reaches a real engine
      WorkItem Flow boundary; at least one proves `DRAFT` reaches zero
      provider calls.
    - Does not modify `/status`/`/workers`/`/config` beyond strictly
      necessary shared plumbing (the WI-M1.4-07A context loader).

11. **WI-M1.4-07C** — Workers and config integration.

    Dependencies: WI-M1.4-07A. Capabilities: development.

    Acceptance criteria:
    - `/workers` uses the AIDO global `WorkerRegistry` (never reads
      workers from a project's own `aido.yaml`, which no longer has
      any), stays provider-free; `/workers --probe` uses the existing
      shared engine probe/rendering path — no second worker-rendering
      implementation. Offline tests cover both a packaged-default
      registry and a user-override registry.
    - `/config` displays: project id/name/workspace; `roadmap` path;
      `resources` path; `initial_prompt` indication/content per the
      existing M1.3 terminal-safety conventions; current milestone id;
      current milestone status; `enabled_worker_count`; `providers`;
      `permission_mode`; `base_branch`; `qa_command_count`. Never a raw
      file dump, never a credential, never a project-owned worker
      registry (none exists).
    - Does not modify `/status` in this WorkItem.

12. **WI-M1.4-07D** — `status` integration.

    Dependencies: WI-M1.4-07A, WI-M1.4-07B. Capabilities: development.

    Acceptance criteria:
    - `/status` combines modern roadmap facts (current milestone
      id, `DRAFT`/`APPROVED` state) with the real, persisted engine
      state from `OrchestratorEngine.status()` — never invents a
      WorkItem status from `ROADMAP.md` itself: the roadmap describes
      *intended* work, the engine snapshot describes *actual persisted*
      work. Before a project's first `run`, no fake `COMPLETED`/
      `PENDING` engine state is fabricated.
    - Every dynamic, engine-originated value rendered still passes
      through M1.3's existing terminal sanitizer — never a second,
      parallel sanitization path.
    - `/status --probe` keeps its existing, explicit probe semantics;
      plain `/status` stays provider-free.
    - Offline tests cover: before a project's first run; after an
      offline, fake-engine persisted execution; a `DRAFT` project; an
      `APPROVED` project; provider-free plain `/status`; explicit
      `--probe`.
    - Does not add unrelated timeline/session behavior (M7/M2, both out
      of scope here).

13. **WI-M1.4-08R** — Final regression, clean-install, and portability
    acceptance.

    Dependencies: WI-M1.4-07B, WI-M1.4-07C, WI-M1.4-07D.
    Capabilities: development.

    Acceptance criteria:
    - `pytest -q` passes for the whole package, offline, zero real
      provider/Ralph calls anywhere in the suite. `git diff --check`
      clean.
    - A clean-install-style acceptance test uses isolated `HOME`/
      `XDG_CONFIG_HOME`, referencing neither
      `~/.config/ai-dev-orchestrator/`, any sibling-checkout worker
      path, nor any project-level worker path.
    - One offline end-to-end scenario proves: `aido-code init` → a
      fresh `DRAFT` project → `aido-code validate` → `DRAFT`/`Not
      executable` → edit `ROADMAP.md` to a valid, `APPROVED` mini
      milestone → `aido-code validate` → `APPROVED`/`Executable` →
      `aido-code run` → the real `OrchestratorEngine` → a fake provider/
      subprocess WorkItem Flow cycle. This same test proves: the
      project's own `aido.yaml` contains no `workers`/`providers`/
      `models`; AIDO's workers are global; `ROADMAP.md` is the
      functional source of truth; `resources/` confinement works; the
      engine receives an injected `WorkerRegistry`; no private engine
      orchestration component (`MVPManager`/`WorkerSelector`/
      `QuotaManager`/a `ProviderAdapter`/`InternalQAEngine`/
      `GitGovernanceService`/a Store) is ever imported by `aido_code`.
    - M1/M1.1/M1.2/M1.3's own already-covered command behaviors remain
      passing, unregressed.
    - A real, provider-free manual bootstrap is also run (not just an
      offline test) — `aido-code init "$TMP" acceptance-project` into a
      fresh temp directory, then `aido-code validate` — confirming a
      `DRAFT` project's `run` is refused before any provider is ever
      touched. This does not, by itself, consume a real provider unless
      the governed WorkItem Flow building this WorkItem needs DEV A/
      DEV B to implement it.

Full functional contract every WorkItem above builds toward:
`docs/PROJECT_CONTRACT.md`.

### Real runs (2026-09-24)

Two real, governed `aido run` executions, both against local, untracked
configs (never committed — `CONTRIBUTING.md`, "Local configuration"),
same `project.id`/`state_dir` as every prior milestone, different
`mvp.id`s (`ProjectRuntime.bootstrap()` creates each new MVP without
disturbing any other's persisted WorkItems — same verified precedent as
every prior milestone). **All 8 WorkItems that AIDO Code's own product
ended up needing are `completed`; no code was ever manually written or
corrected by any human/assistant at any point.**

**Run 1** (`mvp-0.1.4`, WI-M1.4-01..08):

| WorkItem | DEV A | DEV B / DEV FIX | Final status |
|---|---|---|---|
| WI-M1.4-01 | Alice (anthropic) | Victor (openai) | `completed` |
| WI-M1.4-02 | Alice (anthropic) | Victor (openai) | `completed` |
| WI-M1.4-03 | Alice (anthropic) | Victor (openai) | `completed` |
| WI-M1.4-04 | Alice (anthropic) | Victor (openai) | `completed` |
| WI-M1.4-05 | Alice (anthropic) | Victor (openai) | `completed` |
| WI-M1.4-06 | Alice (anthropic) | Victor (openai), 2 DEV FIX rounds | `completed` |
| WI-M1.4-07 | Alice (anthropic) | — (Ralph `max_iterations=5` hit before any commit, 8m06s, exit code 2; DEV B/QA never reached) | **`FAILED`** |
| WI-M1.4-08 | — | — (never attempted) | **`BLOCKED`** (`dependency cannot complete: ['WI-M1.4-07']`) |

Alice's own leftover uncommitted work from the failed WI-M1.4-07
attempt was preserved only as a local `git stash` for diagnostic
inspection — never applied, never cherry-picked, never treated as
accepted product (`CONTRIBUTING.md`'s core rule).

**Run 2, recovery** (`mvp-0.1.4-recovery`, WI-M1.4-07A/07B/07C/07D/08R —
the retired `WI-M1.4-07`/`WI-M1.4-08` ids were never reused, their
`FAILED`/`BLOCKED` status never manually mutated):

| WorkItem | DEV A | DEV B / DEV FIX | Final status |
|---|---|---|---|
| WI-M1.4-07A | Alice (anthropic) | Lydie (anthropic) | `completed` |
| WI-M1.4-07B | Alice (anthropic) | Lydie (anthropic) | `completed` |
| WI-M1.4-07C | Alice (anthropic) | Victor (openai), then a real DEV FIX by Alice after a real QA `FAIL` | `completed` |
| WI-M1.4-07D | Alice (anthropic) | Victor (openai) | `completed` |
| WI-M1.4-08R | Alice (anthropic) | Victor (openai) | `completed` |

Splitting the original oversized scope into five independently-bounded
WorkItems was sufficient on its own — no Ralph iteration-limit increase
was made or needed (§5, "Do not increase Ralph iteration limits merely
to force success").

**Final state**: `pytest -q` — 209 passed, 0 failed, 0 skipped (189
after Run 1's WI-01..06 alone, 70 before M1.4). `git diff --check`
clean. A real, provider-free manual bootstrap
(`python -m aido_code init "$TMP" acceptance-project`) was additionally
run outside the offline test suite: the generated `aido.yaml` contains
no `workers`/`providers`/`models`/`mvp`/`work_items`/`qa`; `validate`
reports `Current milestone: DRAFT` / `Not executable`; `run` refuses
cleanly (`Error: Current milestone is DRAFT. Not executable.`, exit 1)
before any provider is touched.

## M2 — Sessions and resume (`SPECIFIED`, not started, unaffected by M1.4)

Fully specified: acceptance contract in `M2_SPEC.yaml`, the session
data model/persistence/concurrency contract in
`docs/SESSION_CONTRACT.md`, 10 governed WorkItems drafted below
(portable template: `aido.m2.example.yaml`). Not yet created in any
orchestrator runtime state; no code has been written. A human GO is
required before launching this milestone's governed WorkItem Flow,
exactly like M1's.

Current, pre-M8 binary name throughout (`docs/CLI_SPEC.md`): every
command below is `aido-code ...`/`python -m aido_code ...`, never
`aido ...` (that syntax is post-M8 only).

**SPEC migration debt (noted by M1.4, not resolved by it)**:
`M2_SPEC.yaml`/`aido.m2.example.yaml` still describe M2 in the
pre-M1.4 shape (a `ProjectConfig`-style YAML `work_items:`/`qa:` list).
Their relevant content — the acceptance contract, the 10 WorkItems
below — must be migrated into `ROADMAP.md`'s own deterministic grammar
(`docs/PROJECT_CONTRACT.md` §3) before a future GO M2, so this project
never carries two sources of functional truth at once. That migration
is real, separate work, not started here, and never a precondition M1.4
itself needed to satisfy.

Must cover:

- a versioned, persistent session model (`docs/SESSION_CONTRACT.md`);
- a session index with a deterministic most-recent rule;
- `aido-code resume`: interactive picker; `aido-code resume
  <session-id>`: direct resume;
- `--resume`/`-r`, `--continue`/`-c` CLI aliases; `/resume`/`/new` in
  the REPL;
- a session's link to its project (directory/`aido.yaml`), without
  duplicating `ProjectConfig` or engine state in the SessionStore;
- strict separation between session/frontend state and engine state:
  session resume never automatically calls `OrchestratorEngine.run()`,
  probes/selects a worker, or mutates engine state (see
  `ARCHITECTURE.md`, "Hard invariant (M2)");
- resume after this process restarts;
- concurrency/corruption/error handling, fail-closed;
- tests entirely offline (`M2_SPEC.yaml`, criterion 17).

**Design hardening (DR-1 through DR-6, external audit 2026-09-23)**:
resolved directly in `docs/SESSION_CONTRACT.md`/`M2_SPEC.yaml`/
`aido.m2.example.yaml`, before any governed implementation starts —
session file as sole source of truth with a rebuildable index and
atomic (temp-file + `os.replace`) writes (DR-1); a real OS-level lock
(`fcntl.flock()`, releases automatically on process death, no stale-lock
cleanup logic) rather than a vague "lock file" (DR-2); `updated_at`
bumped on successful open/resume, not only on command receipt, ties
broken by `session_id` (DR-3); `session_id` format validated before any
disk access, path confinement, symlinks never followed (DR-4); an
explicit never-stored list (env, credentials, raw provider output) for
interaction history, distinct from terminal rendering safety (M1.3)
(DR-5); AIDO Code starts and serves `resume`/`-c`/`/new`/`/help` with no
project bound, an explicit `UNBOUND` session state (DR-6). See
`docs/SESSION_CONTRACT.md` for the full contract.

### Runtime transition (mvp-0.1 -> mvp-0.2)

Verified by direct code inspection of `ProjectRuntime.bootstrap()` and
`OrchestratorEngine._drive()` (`ai-dev-orchestrator`, `src/orchestrator/
project_runtime.py`/`engine.py`), plus an isolated, fully offline
reproduction: the engine supports adding a new `mvp.id` (e.g.
`mvp-0.2`) to the same `project.id`/`state_dir` as an
already-completed MVP (`mvp-0.1`), without conflict, data loss, or
mutation of the prior MVP's historical WorkItem records. `bootstrap()`
scopes WorkItem lookups by `mvp_id`, and
`OrchestratorEngine.run()`/`.status()` operate on whatever `mvp.id`
the currently-loaded `aido.yaml` names, never a separately-tracked
"current MVP" pointer. This is what makes `aido.m2.example.yaml` safe
to prepare against this same project.

### WorkItems

Drafted, portable template only (`aido.m2.example.yaml`); not created
in any orchestrator runtime state.

1. **WI-M2-01** — Session model + versioned persistence.
2. **WI-M2-02** — Session index + deterministic most-recent selection.
3. **WI-M2-03** — Session-to-project/config binding.
4. **WI-M2-04** — Direct resume by session id.
5. **WI-M2-05** — Interactive resume picker.
6. **WI-M2-06** — `--resume`/`-r` and `--continue`/`-c` CLI aliases.
7. **WI-M2-07** — REPL `/resume` and `/new`.
8. **WI-M2-08** — Session/engine isolation (proves resume never calls
   `.run()`/`.probe_workers()`/selects a worker, and never duplicates
   engine state as a source of truth).
9. **WI-M2-09** — Concurrency/corruption/error handling.
10. **WI-M2-10** — Resume-after-process-restart acceptance.

Full criteria: `aido.m2.example.yaml`. Full contract: `M2_SPEC.yaml`
and `docs/SESSION_CONTRACT.md`. Real test scenarios to run after this
milestone is built (not run during preparation):
`docs/M2_REAL_TEST_PLAN.md`.

## M3 — Natural-language piloting

Free-form status/steering questions answered from real engine facts;
see `docs/CLI_SPEC.md`. A conversational layer may explain, never
decide.

## M4 — Non-interactive mode

`aido-code -p "<request>"` (current, pre-M8 binary name), stdin
piping. See `docs/CLI_SPEC.md`.

## M5 — Structured output

`text`/`json`/`stream-json`, built directly from
`OrchestratorEngine`'s snapshot dataclasses: a stable contract a script
can depend on, never a terminal-output parser. See `docs/CLI_SPEC.md`.

## M6 — Doctor/diagnostics

`aido-code doctor` (current, pre-M8 binary name): engine, config,
project, Git, Ralph, providers, workers, observable quota, QA,
permissions; read-only wherever the underlying fact genuinely is. See
`docs/CLI_SPEC.md`.

## M7 — Real-time timeline

Renders engine events (DEV A, DEV B, QA, Git, WAITING, BLOCKED,
COMPLETED). Bounded today by the coarse `work_item.<status>`
granularity `OrchestratorEngine.run()` actually returns; a finer
per-step feed is real, separate, future engine-side work (see
`ARCHITECTURE.md`, "Events"), never simulated here.

## M8 — `aido` command cutover (`DONE`, 2026-09-25)

**Binary name only — completed right after M1.4.** M1.4 itself already
delivered functional parity with the orchestrator's own legacy `aido`
CLI (`init`/`validate`/`run`/`status`, that project's own transitional
surface per its P13.5): AIDO Code's own `init`/`validate`/`run` never
needed an engine-level `.init()` to reach that parity — the still-open
`.init()` gate `docs/ENGINE_CONTRACT.md` used to describe turned out to
be moot, since `aido-code init` is entirely this project's own logic,
never a call into the engine. With parity already real, the cutover
itself became a small, immediate packaging follow-up rather than a
separately-scheduled future milestone.

**Ownership, before/after**:

```text
before: aido      -> ai-dev-orchestrator (orchestrator.cli)
        aido-code -> AIDO Code

after:  aido      -> AIDO Code (aido_code.__main__:main)
        aido-code -> AIDO Code (same main, compatibility alias)
        ai-dev-orchestrator -> engine/library only, no console script
```

**Changes**:

- This project's own `pyproject.toml`: `[project.scripts]` now declares
  both `aido = "aido_code.__main__:main"` (the real, primary command)
  and `aido-code = "aido_code.__main__:main"` (a compatibility alias,
  kept indefinitely — no arbitrary removal date; both point at the
  exact same `main`, never a duplicated implementation).
- `ai-dev-orchestrator`'s own `pyproject.toml` no longer declares
  `[project.scripts]` at all (that project's own P13.6) — a plain `pip
  install ai-dev-orchestrator` installs no console script; its legacy
  `orchestrator.cli` module stays importable, internal-only.
- **Collision, verified real**: installing both distributions, in
  either order, in a clean venv, leaves exactly one `aido` — AIDO
  Code's — since the engine no longer declares one at all. See
  `docs/M1_1_REFERENCE_RUN.md`-style acceptance below.
- WI-M8-01B (the only functional `src/aido_code/*` change this cutover
  needed, built through the governed WorkItem Flow per
  `CONTRIBUTING.md` — never written directly; **`WI-M8-01` itself is
  retired, never reused**: a first governed attempt crashed pre-
  execution on a dirty working tree, and `mark_work_item_running()`
  persists before `prepare_work_item()` can raise — a real
  `ai-dev-orchestrator` crash-recovery gap, noted here, out of this
  task's own scope to fix; that WorkItem id stays stuck `running`
  forever under the abandoned `mvp-m8-cutover`, never mutated,
  `WI-M8-01B` is the real replacement under a fresh `mvp-m8-cutover-2`):
  the CLI's own usage/error messages (`aido_code.__main__`) no longer
  hardcode the `aido-code` name; they reflect whichever command name
  actually invoked the process, so `aido init` (wrong argument count)
  and `aido init`/`validate`/`run` (unrecognized input) print accurate
  usage text regardless of which of the two entry points was used.

**Packaging status** (superseding the M1.1-era notes below, kept as
historical record):

- `RESOLVED` (M1.1): unique, unambiguous PyPI distribution name for the
  engine; automatic transitive install from a local wheelhouse proven
  end to end.
- `RESOLVED` (M8, this cutover): the `aido` binary name itself now
  belongs to AIDO Code; verified with real, clean-venv wheel installs in
  both install orders (engine-then-AIDO-Code and AIDO-Code-with-engine-
  dependency) — `aido` resolves to AIDO Code's own entry point in every
  case, never overwritten by install order.
- `NOT YET RESOLVED`, unaffected by this cutover: no public
  distribution/versioning channel exists yet (no PyPI publish, no
  Trusted Publishing, no tag/release for either package). Today's
  development convention of two sibling Git checkouts with `pip install
  -e ../ai-dev-orchestrator` (`CONTRIBUTING.md`) remains the local
  dev-loop convenience.

### WorkItems

Prepared for AI Dev Orchestrator's real, governed WorkItem Flow
(`CONTRIBUTING.md`) — the only `src/aido_code/*` change this cutover
needed. The local, untracked config that reproduces it for a real
governed run is never committed.

1. **WI-M8-01B** — Dynamic program name in CLI usage/error messages
   (`WI-M8-01` retired, see the note above this list).

   Dependencies: none. Capabilities: development.

   Acceptance criteria:
   - `aido_code.__main__`'s user-facing usage/error strings (the `init
     <parent-path> <project-name>` argument-count message, the
     `validate`/`run` argument-count message, and the unrecognized-
     argument message) no longer hardcode the literal `aido-code` —
     each derives the actually-invoked program name (e.g. from
     `Path(sys.argv[0]).name`, falling back to `aido` if that is empty/
     unavailable) so both the `aido` and `aido-code` entry points print
     an accurate command name in their own usage text.
   - No behavioral change beyond the displayed program name string:
     exit codes, which branch handles which input, and every other
     message stay exactly as before.
   - No second, duplicated implementation of argument handling — the
     existing `main()` control flow is unchanged, only the string
     construction for these three messages.
   - Offline tests cover: the `init` wrong-argument-count message
     reflecting a simulated `aido` invocation; the same reflecting a
     simulated `aido-code` invocation; the `validate`/`run` wrong-
     argument-count message under both; the unrecognized-argument
     message under both; a fallback case (empty/unusual `sys.argv[0]`)
     still prints a sane, non-empty program name.

### Historical notes (M1.1-era, kept as record — superseded above)

- The engine's PyPI distribution rename (`ai-dev-orchestrator`, never
  the third-party-owned `orchestrator`) and automatic transitive-install
  proof (`pip install --no-index --find-links <wheelhouse> aido-code`
  in a fully clean venv installing `ai-dev-orchestrator` automatically,
  `aido-code`'s own commands including `/status --probe` working
  correctly, zero third-party `orchestrator` distribution ever present)
  — see `docs/M1_1_REFERENCE_RUN.md`.

## M9+

Background jobs, attach, logs, stop, respawn, MCP, hooks, plugins, a
TUI, only per real, demonstrated need. Not designed yet.
