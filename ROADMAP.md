# ROADMAP — AIDO Code

Functional roadmap for AIDO Code, the interactive terminal frontend for
AI Dev Orchestrator. See `README.md` for what this project is,
`ARCHITECTURE.md` for the hard rules it never crosses, and
`docs/ENGINE_CONTRACT.md` for the exact engine API it is built against.

## No M0

The engine/frontend decoupling that made this project possible is **not**
part of this roadmap. It is P13 of `ai-dev-orchestrator`'s own
`ROADMAP.md`, already `DONE` there, and out of scope for any milestone
listed here. This roadmap starts at M1.

## Status

`M1 DONE`: WI-01 through WI-07 (`aido.example.yaml`'s governed
WorkItems) were completed by AI Dev Orchestrator's real WorkItem Flow —
see `MVP_SPEC.yaml` for the acceptance contract they satisfy and
`docs/M1_REFERENCE_RUN.md` for the full factual record of that run
(including a real engine defect it found and its subsequent fix).

`M1.1 DONE`: WI-M1.1-01 through WI-M1.1-04 (`aido.m1_1.example.yaml`'s
governed WorkItems) were completed by AI Dev Orchestrator's real
WorkItem Flow — a small technical increment between M1 and M2,
correcting the engine dependency to the renamed `ai-dev-orchestrator`
distribution, adding `probe_workers()` to the engine client, and
extending `/status`/`/workers` with `--probe`; see `M1_1_SPEC.yaml` for
the acceptance contract and `docs/M1_1_REFERENCE_RUN.md` for the full
factual record (including a real Git-commit-identity engine defect it
found). It is not part of M2 and did not start M2.

`M1.2 READY FOR GOVERNED DEVELOPMENT`, not started: a small technical
increment after M1.1 and before M2, consuming ai-dev-orchestrator's
richer `ProviderSnapshot` (P13.3: `quota_windows`/`reset_credits`) so
`/status --probe`/`/workers --probe` render real utilization/remaining/
reset/reset-credit facts, grouped by provider; see `M1_2_SPEC.yaml`,
`aido.m1_2.example.yaml`. It is not part of M2 and does not start M2.

| Milestone | Status |
|---|---|
| M1 — Minimal interactive shell | `DONE` (see `docs/M1_REFERENCE_RUN.md`) |
| M1.1 — CLI conventions and standalone install | `DONE` (see `docs/M1_1_REFERENCE_RUN.md`) |
| M1.2 — Rich provider quota status | `READY FOR GOVERNED DEVELOPMENT`, not started (see `M1_2_SPEC.yaml`) |
| M2 — Sessions and resume | `READY FOR GOVERNED DEVELOPMENT`, not started (see `M2_SPEC.yaml`, `docs/SESSION_CONTRACT.md`) |
| M3 — Natural-language piloting | `À VOTER` |
| M4 — Non-interactive mode | `À VOTER` |
| M5 — Structured output | `À VOTER` |
| M6 — Doctor/diagnostics | `À VOTER` |
| M7 — Real-time timeline | `À VOTER` |
| M8 — `aido` command cutover | `À VOTER`, gated on functional parity |
| M9+ | `À VOTER`, only per real, demonstrated need |

## M1 — Minimal interactive shell

**Objective**: ship the first usable frontend.

Commands: `/help`, `/status`, `/workers`, `/config`, `/validate`,
`/run`, `/exit`. See `docs/CLI_SPEC.md`.

**Acceptance criteria** (also `MVP_SPEC.yaml`):

- detects an `aido.yaml` in the current/a given directory;
- connects to the real public engine (`orchestrator.engine.
  OrchestratorEngine`), never a mock/simulated one, in its own offline
  tests via the engine's own injection seams (`provider_adapters`/
  `subprocess_runner`, see `docs/ENGINE_CONTRACT.md`);
- `/status` reflects real persisted project state;
- `/workers` reflects the real configured worker registry;
- `/validate` reflects real config validation;
- `/run` drives the real engine and is also how a project resumes;
- no orchestration logic (worker selection, QA verdicts, merge
  decisions) is ever duplicated in this project;
- tests are offline (fake provider adapters, fake Ralph subprocess;
  same conventions as `ai-dev-orchestrator`'s own test suite).

## M1.1 — CLI conventions and standalone install

**Status: `DONE`.** WI-M1.1-01 through WI-M1.1-04 (portable template:
`aido.m1_1.example.yaml`, same `project.id`/`state_dir` as M1/M2, its
own `mvp.id: mvp-0.1.1`) were completed by AI Dev Orchestrator's real,
governed WorkItem Flow — see `M1_1_SPEC.yaml` for the acceptance
contract they satisfy and `docs/M1_1_REFERENCE_RUN.md` for the full
factual record. A small technical increment between M1 (`DONE`) and M2
(not started); it is not part of M2 and did not start M2.

Must cover:

- `ai-dev-orchestrator` engine's own PyPI distribution rename (from the
  third-party-owned `orchestrator` name) reflected in this project's
  `pyproject.toml` dependency (`ai-dev-orchestrator>=0.1.2`), with the
  existing `from orchestrator.engine import ...` import path unchanged;
- `EngineClient.probe_workers()`, delegating directly to
  `OrchestratorEngine.probe_workers()`;
- `/status` (no flags) showing the full worker list alongside the
  existing project/MVP/work-item view, with zero provider probes;
- `/status --probe`: the same view plus one real `probe_workers()`
  call, rendering each worker's observable provider state honestly
  (including workers that honestly share one provider's state);
- `/workers` staying static (no probe) and gaining `/workers --probe`,
  sharing the exact same probe/rendering path as `/status --probe` —
  no duplicated logic (KISS);
- `/run` staying project start/resume, unchanged; no new project-level
  `/resume` command (session-level resume is M2's own, separate scope);
- regression proof that M1's existing commands/criteria
  (`MVP_SPEC.yaml`) are not broken.

### M1.1 WorkItems (drafted, portable template only — see `aido.m1_1.example.yaml`; not created in any orchestrator runtime state)

1. **WI-M1.1-01** — Correct AIDO Code engine dependency metadata.
2. **WI-M1.1-02** — Extend `EngineClient` with `probe_workers()`.
3. **WI-M1.1-03** — Improve `/status` and `/workers` UX.
4. **WI-M1.1-04** — Regression/acceptance tests, plus docs.

Full acceptance criteria per WorkItem: `aido.m1_1.example.yaml`. Full
functional contract these WorkItems build toward: `M1_1_SPEC.yaml`.

## M1.2 — Rich provider quota status

**Status: `READY FOR GOVERNED DEVELOPMENT`, not started.** Fully
specified — acceptance contract in `M1_2_SPEC.yaml`, 2 governed
WorkItems drafted below (portable template: `aido.m1_2.example.yaml`,
same `project.id`/`state_dir` as every prior milestone, its own
`mvp.id: mvp-0.1.2`) — but not yet created in any orchestrator runtime
state, and no code has been written. A human GO is required before
launching this milestone's governed WorkItem Flow, exactly like M1.1's.
A small technical increment after M1.1 (`DONE`) and before M2 (not
started); it is not part of M2 and does not start M2.

Must cover:

- `pyproject.toml`'s engine dependency minimum raised to
  `ai-dev-orchestrator>=0.1.3` (the version that introduced
  `ProviderSnapshot.quota_windows`/`reset_credits`);
- `EngineClient` exposing whatever `/status --probe`/`/workers --probe`
  need directly from `OrchestratorEngine.probe_workers()`'s own richer
  `ProviderSnapshot`, no provider-specific logic of its own;
- `/status --probe` rendering utilization/remaining/reset_at/reset
  credits per quota window, never fabricated when unknown;
- `/workers --probe` sharing the exact same rendering path — no
  duplicated quota-rendering logic (KISS, same rule M1.1 already
  established for the plain probe state);
- quota rendered once per provider actually probed, never once per
  worker;
- `/status`/`/workers` (no flags) and `/run` entirely unregressed.

### M1.2 WorkItems (drafted, portable template only — see `aido.m1_2.example.yaml`; not created in any orchestrator runtime state)

1. **WI-M1.2-01** — Consume richer `ProviderSnapshot`.
2. **WI-M1.2-02** — Regression and clean-install UX.

Full acceptance criteria per WorkItem: `aido.m1_2.example.yaml`. Full
functional contract these WorkItems build toward: `M1_2_SPEC.yaml`.

## M2 — Sessions and resume

**Status: `READY FOR GOVERNED DEVELOPMENT`, not started.** Fully
specified — acceptance contract in `M2_SPEC.yaml`, the session data
model/persistence/concurrency contract in `docs/SESSION_CONTRACT.md`,
and 10 governed WorkItems drafted below (portable template:
`aido.m2.example.yaml`, see "Runtime transition" below) — but not yet
created in any orchestrator runtime state, and no code has been written.
A human GO is required before launching this milestone's governed
WorkItem Flow, exactly like M1's.

Current, pre-M8 binary name throughout (see `docs/CLI_SPEC.md`): every
command below is `aido-code ...`/`python -m aido_code ...`, never
`aido ...` (that syntax is post-M8 future syntax only).

Must cover:

- a versioned, persistent session model (`docs/SESSION_CONTRACT.md`);
- a session index with a deterministic most-recent rule;
- `aido-code resume`: interactive picker;
- `aido-code resume <session-id>`: direct resume;
- `--resume`/`-r`, `--continue`/`-c` CLI aliases;
- `/resume`/`/new` in the REPL;
- a session's link to its project (directory/`aido.yaml`), without
  duplicating `ProjectConfig` or engine state in the SessionStore;
- strict separation between session/frontend state and engine state:
  session resume **never** automatically calls `OrchestratorEngine.run()`,
  probes/selects a worker, or mutates engine state (see the "Hard
  invariant (M2)" in `ARCHITECTURE.md`, "Session resume vs. project
  run/resume");
- resume after this process restarts;
- concurrency/corruption/error handling, fail-closed;
- tests entirely offline (`M2_SPEC.yaml`, criterion 17).

### Runtime transition (mvp-0.1 -> mvp-0.2)

Verified by direct code inspection of `ProjectRuntime.bootstrap()` and
`OrchestratorEngine._drive()` (`ai-dev-orchestrator`, `src/orchestrator/
project_runtime.py`/`engine.py`), plus an isolated, temporary, fully
offline reproduction (fake provider adapter, temporary git workspace and
`state_dir`, never the real `aido-code` project state): the engine
supports adding a new `mvp.id` (e.g. `mvp-0.2`) to the **same**
`project.id`/`state_dir` as an already-completed MVP (`mvp-0.1`), without
conflict, data loss, or mutation of the prior MVP's historical WorkItem
records. `bootstrap()` scopes WorkItem lookups by `mvp_id`, and
`OrchestratorEngine.run()`/`.status()` operate on whatever `mvp.id` the
currently-loaded `aido.yaml` names — never on a separately-tracked
"current MVP" pointer. This is what makes `aido.m2.example.yaml` (below)
safe to prepare against this same project.

### M2 WorkItems (drafted, portable template only — see `aido.m2.example.yaml`; not created in any orchestrator runtime state)

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

Full acceptance criteria per WorkItem: `aido.m2.example.yaml`. Full
functional contract these WorkItems build toward: `M2_SPEC.yaml` and
`docs/SESSION_CONTRACT.md`. Real test scenarios to run after this
milestone is actually built (not run in this preparation task):
`docs/M2_REAL_TEST_PLAN.md`.

## M3 — Natural-language piloting

Free-form status/steering questions answered from real engine facts; see
`docs/CLI_SPEC.md`. A conversational layer may explain, never decide.

## M4 — Non-interactive mode

`aido-code -p "<request>"` (current, pre-M8 binary name), stdin piping.
See `docs/CLI_SPEC.md`.

## M5 — Structured output

`text`/`json`/`stream-json`, built directly from `OrchestratorEngine`'s
snapshot dataclasses: a stable contract a script can depend on, never a
terminal-output parser. See `docs/CLI_SPEC.md`.

## M6 — Doctor/diagnostics

`aido-code doctor` (current, pre-M8 binary name): engine, config,
project, Git, Ralph, providers, workers, observable quota, QA,
permissions; read-only wherever the underlying fact genuinely is. See
`docs/CLI_SPEC.md`.

## M7 — Real-time timeline

Renders engine events (DEV A, DEV B, QA, Git, WAITING, BLOCKED,
COMPLETED). Bounded today by the coarse `work_item.<status>` granularity
`OrchestratorEngine.run()` actually returns; a finer per-step feed is
real, separate, future engine-side work (see `ARCHITECTURE.md`,
"Events"), never simulated here.

## M8 — `aido` command cutover

Only after this project demonstrates functional parity with the
orchestrator's own existing `aido` CLI. Until then this project never
claims the `aido` binary name (`python -m aido_code`/`aido-code` instead).
The orchestrator retiring or renaming its own console script is a
separate decision made in that project, not here.

**Packaging requirement, gating this milestone** — status as of M1.1:

- `RESOLVED`: the engine has a unique, unambiguous PyPI distribution
  name (`ai-dev-orchestrator`, never the third-party-owned
  `orchestrator`); this project declares it as a real dependency
  (`ai-dev-orchestrator>=0.1.2`); and automatic installation from local
  wheels was proven end to end — `pip install --no-index --find-links
  <wheelhouse> aido-code` in a fully clean venv (no sibling checkout, no
  prior editable install of either package) installed
  `ai-dev-orchestrator` automatically as a transitive dependency, and
  `aido-code`'s own commands (including `/status --probe`) worked
  correctly against it, all with zero `orchestrator` (third-party)
  distribution ever present. See `docs/M1_1_REFERENCE_RUN.md`.
- `NOT YET RESOLVED`: no public distribution/versioning channel exists
  (no PyPI publish, no Trusted Publishing, no tag/release for either
  package — a deliberate scope boundary of M1.1, a separate human
  decision); the `aido` binary name cutover itself has not happened;
  and the still-open `.init()` gate in `docs/ENGINE_CONTRACT.md`
  ("What this contract does not give AIDO Code (yet)") is unaffected by
  this work.
- Today's development convention of two sibling Git checkouts with
  `pip install -e ../ai-dev-orchestrator` (see `CONTRIBUTING.md`)
  remains the local dev-loop convenience for now; a real, publishable
  install path is proven above but not yet the default onboarding path.

## M9+

Background jobs, attach, logs, stop, respawn, MCP, hooks, plugins, a
TUI, only per real, demonstrated need. Not designed yet.
