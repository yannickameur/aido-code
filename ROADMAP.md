# ROADMAP — AIDO Code

Functional roadmap for AIDO Code, the interactive terminal frontend for
AI Dev Orchestrator. See `README.md` for what this project is,
`ARCHITECTURE.md` for the hard rules it never crosses, and
`docs/ENGINE_CONTRACT.md` for the exact engine API it is built against.

No M0: the engine/frontend decoupling that made this project possible
is P13 of `ai-dev-orchestrator`'s own `ROADMAP.md`, already `DONE`
there. This roadmap starts at M1.

## Where we stand

DONE: M1, M1.1, M1.2
NEXT: M2, ready for governed development, not started
FUTURE: M3-M8

| Milestone | Status |
|---|---|
| M1 — Minimal interactive shell | `DONE` (see `docs/M1_REFERENCE_RUN.md`) |
| M1.1 — CLI conventions and standalone install | `DONE` (see `docs/M1_1_REFERENCE_RUN.md`) |
| M1.2 — Rich provider quota status | `DONE` (see `M1_2_SPEC.yaml`) |
| M2 — Sessions and resume | `READY FOR GOVERNED DEVELOPMENT`, not started (see `M2_SPEC.yaml`, `docs/SESSION_CONTRACT.md`) |
| M3 — Natural-language piloting | `À VOTER` |
| M4 — Non-interactive mode | `À VOTER` |
| M5 — Structured output | `À VOTER` |
| M6 — Doctor/diagnostics | `À VOTER` |
| M7 — Real-time timeline | `À VOTER` |
| M8 — `aido` command cutover | `À VOTER`, gated on functional parity |
| M9+ | `À VOTER`, only per real, demonstrated need |

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

## M1.3 — Audit hardening (`READY FOR GOVERNED DEVELOPMENT`, not started)

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

### WorkItems (drafted, portable template only — see `aido.m1_3.example.yaml`; not created in any orchestrator runtime state)

1. **WI-M1.3-01** — CLI launch argument validation (F-01).
2. **WI-M1.3-02** — Terminal rendering safety (F-02).
3. **WI-M1.3-03** — Regression + engine contract fix (F-03).

Full acceptance criteria per WorkItem: `aido.m1_3.example.yaml`. Full
functional contract these WorkItems build toward: `M1_3_SPEC.yaml`.

## M2 — Sessions and resume (`READY FOR GOVERNED DEVELOPMENT`, not started)

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

## M8 — `aido` command cutover

Only after this project demonstrates functional parity with the
orchestrator's own existing `aido` CLI. Until then this project never
claims the `aido` binary name (`python -m aido_code`/`aido-code`
instead). The orchestrator retiring or renaming its own console script
is a separate decision made in that project, not here.

**Packaging requirement, gating this milestone** — status as of M1.1:

- `RESOLVED`: the engine has a unique, unambiguous PyPI distribution
  name (`ai-dev-orchestrator`, never the third-party-owned
  `orchestrator`); this project declares it as a real dependency
  (`ai-dev-orchestrator>=0.1.2`); automatic installation from local
  wheels was proven end to end — `pip install --no-index --find-links
  <wheelhouse> aido-code` in a fully clean venv (no sibling checkout,
  no prior editable install of either package) installed
  `ai-dev-orchestrator` automatically as a transitive dependency, and
  `aido-code`'s own commands (including `/status --probe`) worked
  correctly against it, all with zero `orchestrator` (third-party)
  distribution ever present. See `docs/M1_1_REFERENCE_RUN.md`.
- `NOT YET RESOLVED`: no public distribution/versioning channel exists
  (no PyPI publish, no Trusted Publishing, no tag/release for either
  package, a deliberate scope boundary of M1.1); the `aido` binary
  name cutover itself has not happened; the still-open `.init()` gate
  in `docs/ENGINE_CONTRACT.md` ("What this contract does not give
  AIDO Code (yet)") is unaffected by this work.
- Today's development convention of two sibling Git checkouts with
  `pip install -e ../ai-dev-orchestrator` (see `CONTRIBUTING.md`)
  remains the local dev-loop convenience for now; a real, publishable
  install path is proven above but not yet the default onboarding
  path.

## M9+

Background jobs, attach, logs, stop, respawn, MCP, hooks, plugins, a
TUI, only per real, demonstrated need. Not designed yet.
