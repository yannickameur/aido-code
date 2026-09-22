# CLI spec

The command/flag surface, milestone by milestone (see `ROADMAP.md` for
what each milestone actually delivers and its acceptance criteria).

- **M1: `IMPLEMENTED`/`DONE`** — the commands below under "M1" are real,
  tested, and shipped (see `README.md`, "Status", and
  `docs/M1_REFERENCE_RUN.md`).
- **M2: `READY FOR GOVERNED DEVELOPMENT`, not started** — specified
  (`M2_SPEC.yaml`, `docs/SESSION_CONTRACT.md`) but not yet built.
- **M3-M8: `PLANNED`/`À VOTER`** — not specified in detail yet, nothing
  below for these milestones is implemented.

## Binary name

**Current (M1 through M7, until M8's cutover gate is met — see "M8"
below): `aido-code ...` or `python -m aido_code ...`.** The name `aido`
belongs to the orchestrator's own existing CLI until M8; every command
in this document below M8 uses `aido-code`/`python -m aido_code`, never
`aido`. A separate, clearly-labeled "M8: future syntax" section further
down documents the post-cutover `aido ...` syntax — the two are never
mixed in the same example.

## M1 — REPL commands

```
/help
/status
/workers
/config
/validate
/run
/exit
```

Each maps directly to one `OrchestratorEngine` call (see
`docs/ENGINE_CONTRACT.md`): `/status` → `.status()`, `/workers` →
`.workers()`, `/validate` → `.validate()`, `/run` → `.run()`. `/config`
shows the loaded `aido.yaml` facts (via `.validate()`'s
`ProjectSnapshot`), not a raw file dump. `/run` is also how a project
resumes; see "Session resume vs. project run" in `ARCHITECTURE.md`.

## M2 — Session commands and flags (`READY FOR GOVERNED DEVELOPMENT`, not implemented)

Full functional contract: `M2_SPEC.yaml` and `docs/SESSION_CONTRACT.md`.
Conventions deliberately close to Codex CLI/Claude Code, so an existing
user of either is not lost — using the current, pre-M8 binary name (see
"Binary name" above):

```
aido-code resume                # interactive session picker
aido-code resume <session-id>   # resume a specific session
aido-code --resume <session-id> # Claude-style alias
aido-code -r <session-id>       # short alias

aido-code --continue            # continue the most recent session
aido-code -c                    # short alias
```

Equivalently: `python -m aido_code resume`, `python -m aido_code --resume
<session-id>`, etc.

In the REPL:

```
/resume
/new
```

All of the above are session-level (AIDO Code's own conversation/UX
state) and **never** automatically call `OrchestratorEngine.run()`,
probe/select a worker, or otherwise touch engine state — see
`docs/SESSION_CONTRACT.md` and "Session resume vs. project run/resume"
in `ARCHITECTURE.md` for the exact invariant. Resuming a session only
restores AIDO Code's own UX state; advancing the project always requires
a separate, explicit `/run`.

## M3 — Natural-language piloting (`PLANNED`, not specified in detail)

Free-form questions/requests handled in the REPL, e.g.:

```
où en est le projet ?
quels workers sont disponibles ?
continue le projet
pourquoi WI-12 attend ?
qu'est-ce qui bloque la QA ?
```

Every fact used to answer comes from an `OrchestratorEngine` snapshot.
A conversational layer may explain/summarize; it never becomes a second
authority on project state.

## M4 — Non-interactive mode (`PLANNED`, not specified in detail)

Using the current, pre-M8 binary name (see "Binary name" above):

```
aido-code -p "status"
aido-code -p "continue le projet"
echo "status" | aido-code -p
```

## M5 — Structured output (`PLANNED`, not specified in detail)

```
--output text          # default, human-readable
--output json
--output stream-json
```

The `json`/`stream-json` shapes are `OrchestratorEngine`'s own snapshot
dataclasses, serialized directly (see `docs/ENGINE_CONTRACT.md`): a
stable API contract a script can depend on, never a parse of the
human-readable terminal rendering.

## M6 — `aido-code doctor` (`PLANNED`, not specified in detail)

Read-only diagnostics, covering (as far as each can honestly be
determined without side effects): engine version, config, project
state, Git, Ralph, providers, workers, observable quota, QA, permission
mode. Current, pre-M8 binary name: `aido-code doctor` /
`python -m aido_code doctor`.

## M7 — Timeline (`PLANNED`, not specified in detail)

Renders `RunResult.events`/future engine event stream: DEV A, DEV B, QA,
Git, WAITING, BLOCKED, COMPLETED. Granularity is bounded by what the
engine actually emits; see "Events" in `ARCHITECTURE.md`.

## M8 — `aido` command cutover (`À VOTER`, gated on functional parity)

Only after functional parity with the orchestrator's own existing `aido`
CLI (`init`/`validate`/`run`/`status`) is demonstrated. Before that
point, this project never claims the `aido` command name; it runs as
`python -m aido_code`/`aido-code`. The orchestrator's own console script
is retired or renamed in a separate, later decision; this project does
not do that unilaterally.

**Known gate, not yet resolved**: the orchestrator's public
`orchestrator.engine.OrchestratorEngine` façade currently exposes
`.validate()`/`.status()`/`.workers()`/`.probe_workers()`/`.run()`/
`.close()` — **no public `.init()` method** — while parity requires
matching all four of `init`/`validate`/`run`/`status`. This project must
never import private helpers from `orchestrator.cli` to work around this
gap. See `ROADMAP.md`, "M8", for the options to evaluate (a future public
engine primitive, a frontend-only solution using a stable contract, or
another clean mechanism) — not decided here, and not something M2
depends on or blocks on.

### M8: future syntax (post-cutover only, never mixed with the current syntax above)

Only after the M8 gate above is met:

```
aido resume
aido resume <session-id>
aido --resume <session-id>
aido -r <session-id>
aido --continue
aido -c
aido -p "status"
aido doctor
```

## M9+

Only as real needs are established: background jobs, attach, logs, stop,
respawn, MCP, hooks, plugins, a TUI. None of these are scoped or
designed yet.
