# AIDO Code

The interactive terminal frontend for [AI Dev Orchestrator](https://github.com/yannickameur/ai-dev-orchestrator).

**Status: M1 `DONE`.** WI-01 through WI-07 were completed by AI Dev
Orchestrator's real, governed WorkItem Flow (never by a human/assistant
writing code directly here; see "How this project gets built" below): a
minimal interactive shell exists, installable and runnable, with 32
offline tests passing. See [`docs/M1_REFERENCE_RUN.md`](docs/M1_REFERENCE_RUN.md)
for the full factual record of that run, including a real engine defect
it found and that was fixed before this project was promoted to a
second real reference project. M2 (sessions/resume) and later are
`PLANNED`, not started.

## What AIDO Code is

AIDO Code gives a user a terminal experience familiar to Claude Code,
Codex CLI, and Vibe: a REPL, `/help`-style commands, session history,
structured output. The fundamental difference is what sits behind it:
not a single agent, but AI Dev Orchestrator's multi-worker,
multi-provider engine (DEV A, then DEV B corrective review, then
deterministic QA, then a governed Git merge).

AIDO Code is not itself an agent, and not itself an orchestrator. It is a
thin, stateful client over the engine's public façade
(`orchestrator.engine.OrchestratorEngine`). See
[`docs/ENGINE_CONTRACT.md`](docs/ENGINE_CONTRACT.md) for the exact
contract this project is built against.

## Why this project exists

AI Dev Orchestrator originally shipped its own CLI (`aido
init/validate/run/status`) directly. P13 in that project's own
`ROADMAP.md` separated the two concerns permanently: the orchestrator
stays a reusable, headless engine; the interactive terminal experience
becomes its own product, here. See that project's `ROADMAP.md`, section
P13, for the full decoupling rationale.

## Documents

- [`ROADMAP.md`](ROADMAP.md): the functional roadmap, starting at M1 (no
  M0; the engine/frontend decoupling is P13 of the orchestrator's own
  roadmap, not a milestone of this project).
- [`ARCHITECTURE.md`](ARCHITECTURE.md): target architecture and the
  hard rules this project never crosses (never read SQLite directly,
  never construct `MVPManager`/`WorkerSelector`/`QuotaManager`, never
  pick a worker, never decide a WorkItem is done).
- [`docs/ENGINE_CONTRACT.md`](docs/ENGINE_CONTRACT.md): the exact public
  engine surface this project consumes.
- [`docs/CLI_SPEC.md`](docs/CLI_SPEC.md): the planned command/flag
  surface, milestone by milestone.
- [`MVP_SPEC.yaml`](MVP_SPEC.yaml): the acceptance contract for MVP 0.1
  (M1, a minimal interactive shell).
- [`docs/M1_REFERENCE_RUN.md`](docs/M1_REFERENCE_RUN.md): the factual
  record of M1's real, governed build — including a real engine defect
  it found and its fix.
- [`CONTRIBUTORS.md`](CONTRIBUTORS.md): who/what actually produced M1.

## How this project gets built

Not by a human or an assistant writing code directly into this
repository. AI Dev Orchestrator governs its own development the same way
it governed Morpion Web 3D: DEV A implements, DEV B reviews and
corrects, deterministic QA decides PASS/FAIL, a governed merge lands the
result. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Contributors

See [`CONTRIBUTORS.md`](CONTRIBUTORS.md): who/what actually produced
M1's real, governed commits (workers `Alice`/`Victor`, never a
provider/vendor name), and the project's own maintainer.

## Relationship to `ai-dev-orchestrator`

This is a separate Git repository, separate product, separate release
cycle. It depends on `ai-dev-orchestrator` as its engine (a Python
dependency once real code exists) and, during local development, on that
sibling repository's own `config/workers.yaml` (see
[`aido.example.yaml`](aido.example.yaml)). It never vendors or
reimplements any orchestrator internals.
