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

| Milestone | Status |
|---|---|
| M1 — Minimal interactive shell | `DONE` (see `docs/M1_REFERENCE_RUN.md`) |
| M2 — Sessions and resume | `PLANNED` (WorkItems drafted, not scheduled) |
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

## M2 — Sessions and resume

**Not scheduled for MVP 0.1.** WorkItems are drafted (see "M2 WorkItems"
below) but not created as real, executable orchestrator WorkItems yet:
per explicit instruction, this roadmap prepares them without launching
any of them.

Must cover:

- session storage;
- a session index;
- `aido resume`;
- a session picker;
- `aido resume <session-id>`;
- `--resume`/`-r`;
- `--continue`/`-c`;
- `/resume`/`/new` in the REPL;
- a session's link to its project (directory/`aido.yaml`);
- strict separation between session/frontend state and engine state (see
  "Session resume vs. project run/resume", `ARCHITECTURE.md`);
- resume after this process restarts;
- offline tests.

### M2 WorkItems (drafted, not created in any orchestrator state)

1. Session storage format and store.
2. Session index (list/most-recent).
3. `aido resume`: interactive picker.
4. `aido resume <session-id>`: direct resume.
5. `--resume`/`-r` flag aliases.
6. `--continue`/`-c` flag aliases.
7. `/resume`/`/new` REPL commands.
8. Session-to-project linking.
9. Session/engine state separation: acceptance test proving a session
   resume never bypasses or duplicates `OrchestratorEngine.run()`'s own
   WAITING/RECOVERY_REQUIRED handling.
10. Resume-after-restart acceptance test.

## M3 — Natural-language piloting

Free-form status/steering questions answered from real engine facts; see
`docs/CLI_SPEC.md`. A conversational layer may explain, never decide.

## M4 — Non-interactive mode

`aido -p "<request>"`, stdin piping. See `docs/CLI_SPEC.md`.

## M5 — Structured output

`text`/`json`/`stream-json`, built directly from `OrchestratorEngine`'s
snapshot dataclasses: a stable contract a script can depend on, never a
terminal-output parser. See `docs/CLI_SPEC.md`.

## M6 — Doctor/diagnostics

`aido doctor`: engine, config, project, Git, Ralph, providers, workers,
observable quota, QA, permissions; read-only wherever the underlying
fact genuinely is. See `docs/CLI_SPEC.md`.

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

**Packaging requirement, gating this milestone**: today's development
convention of two sibling Git checkouts with `pip install -e
../ai-dev-orchestrator` (see `CONTRIBUTING.md`) is a development-only
convenience, never something the shipped product may require. Before
this project claims the `aido` command, there must be a stable
distribution/versioning contract between `aido-code` and
`ai-dev-orchestrator` that lets the final product be installed without
manually managing two sibling Git checkouts. The exact mechanism is not
designed yet (candidates to evaluate at cutover time include: a
publishable engine package, a versioned dependency, a common
distribution, or another standard Python packaging mechanism); per
KISS/YAGNI, this is documented now as a requirement, not built now, since
M1 does not need it.

## M9+

Background jobs, attach, logs, stop, respawn, MCP, hooks, plugins, a
TUI, only per real, demonstrated need. Not designed yet.
