# CLI spec

The planned command/flag surface, milestone by milestone (see
`ROADMAP.md` for what each milestone actually delivers and its
acceptance criteria). Nothing in this document is implemented yet; see
`README.md`, "Status".

## Binary name (provisional, M1–M7)

During development: `python -m aido_code`, or `aido-code` once the
package exposes a console script. The name `aido` is not claimed by this
project until M8 (cutover), and only after functional parity with the
orchestrator's own existing `aido` CLI is demonstrated. See "M8" below
and `ROADMAP.md`.

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

## M2 — Session commands and flags

Conventions deliberately close to Codex CLI/Claude Code, so an existing
user of either is not lost:

```
aido resume                # interactive session picker
aido resume <session-id>   # resume a specific session
aido --resume <session-id> # Claude-style alias
aido -r <session-id>       # short alias

aido --continue            # continue the most recent session
aido -c                    # short alias
```

In the REPL:

```
/resume
/new
```

All of the above are session-level (AIDO Code's own conversation/UX
state), never a substitute for the engine's own `.run()`-is-resume
semantics. See "Session resume vs. project run/resume" in
`ARCHITECTURE.md` for why these must never be conflated.

## M3 — Natural-language piloting

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

## M4 — Non-interactive mode

```
aido -p "status"
aido -p "continue le projet"
echo "status" | aido -p
```

## M5 — Structured output

```
--output text          # default, human-readable
--output json
--output stream-json
```

The `json`/`stream-json` shapes are `OrchestratorEngine`'s own snapshot
dataclasses, serialized directly (see `docs/ENGINE_CONTRACT.md`): a
stable API contract a script can depend on, never a parse of the
human-readable terminal rendering.

## M6 — `aido doctor`

Read-only diagnostics, covering (as far as each can honestly be
determined without side effects): engine version, config, project
state, Git, Ralph, providers, workers, observable quota, QA, permission
mode.

## M7 — Timeline

Renders `RunResult.events`/future engine event stream: DEV A, DEV B, QA,
Git, WAITING, BLOCKED, COMPLETED. Granularity is bounded by what the
engine actually emits; see "Events" in `ARCHITECTURE.md`.

## M8 — `aido` command cutover

Only after functional parity with the orchestrator's own existing `aido`
CLI (`init`/`validate`/`run`/`status`) is demonstrated. Before that
point, this project never claims the `aido` command name; it runs as
`python -m aido_code`/`aido-code`. The orchestrator's own console script
is retired or renamed in a separate, later decision; this project does
not do that unilaterally.

## M9+

Only as real needs are established: background jobs, attach, logs, stop,
respawn, MCP, hooks, plugins, a TUI. None of these are scoped or
designed yet.
