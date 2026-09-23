# CLI spec

The command/flag surface, milestone by milestone. See `ROADMAP.md` for
what each milestone delivers and its acceptance criteria.

## Binary name

**Current (M1 through M7, until M8's cutover gate is met): `aido-code
...` or `python -m aido_code ...`.** The name `aido` belongs to the
orchestrator's own existing CLI until M8. A separate, clearly-labeled
"M8: future syntax" section below documents the post-cutover `aido ...`
syntax — the two are never mixed in the same example.

## Command reference

| Command | Status | Purpose | Provider call |
|---|---|---|---|
| `/help` | `IMPLEMENTED` | List available commands | No |
| `/status` | `IMPLEMENTED` | Project + MVP + work items + all configured workers | No |
| `/status --probe` | `IMPLEMENTED` | Same, plus one real `probe_workers()` call | Yes |
| `/workers` | `IMPLEMENTED` | Configured workers (static view) | No |
| `/workers --probe` | `IMPLEMENTED` | Workers, plus live provider/quota state | Yes |
| `/config` | `IMPLEMENTED` | Loaded `aido.yaml` facts | No |
| `/validate` | `IMPLEMENTED` | Config validation | No |
| `/run` | `IMPLEMENTED` | Start or resume project execution | Potentially |
| `/exit` | `IMPLEMENTED` | Exit the REPL | No |
| `resume`, `--resume`/`-r` | `M2` | Resume a frontend session by id | No |
| `--continue`/`-c` | `M2` | Resume the most recent session | No |
| `/resume` | `M2` | Resume picker, from inside the REPL | No |
| `/new` | `M2` | New frontend session | No |
| Free-form natural language | `M3` | Status/steering questions | Depends |
| `-p "<request>"` | `M4` | Non-interactive mode | Depends |
| `--output json`/`stream-json` | `M5` | Structured output | No |
| `doctor` | `M6` | Read-only diagnostics | No |
| Timeline | `M7` | Real-time event feed | No |

Each M1 command maps directly to one `OrchestratorEngine` call (see
`docs/ENGINE_CONTRACT.md`): `/status` → `.status()`, `/workers` →
`.workers()`, `/validate` → `.validate()`, `/run` → `.run()`. `/config`
shows the loaded `aido.yaml` facts (via `.validate()`'s
`ProjectSnapshot`), never a raw file dump. `/run` is also how a project
resumes; see "Session resume vs. project run" in `ARCHITECTURE.md`.

## M1.1 — `--probe` on `/status`/`/workers`

Full contract: `M1_1_SPEC.yaml` and `aido.m1_1.example.yaml`.

```
/status           # project + MVP + work items + all configured workers, zero provider calls
/status --probe   # same, plus one real probe_workers() call
/workers          # unchanged from M1: static WorkerRegistry view, never a probe
/workers --probe  # same probe_workers() call and rendering as /status --probe
```

`/status` (no flags) extends M1's view with the same worker list
`/workers` renders, still with zero provider probes. `--probe` on
either command is the only thing here that calls
`EngineClient.probe_workers()` (a thin, direct delegation to
`OrchestratorEngine.probe_workers()`); both flags share one
probe/rendering code path. `/run` is unaffected.

## M1.2 — Rich provider quota status on `--probe`

Full contract: `M1_2_SPEC.yaml` and `aido.m1_2.example.yaml`.

`/status --probe` and `/workers --probe` keep M1.1's per-worker
`probe=...` state and, through the same shared rendering path (see
`_format_workers_section()`/`format_provider_quotas()` in `repl.py`),
now also render a `provider quotas:` section: for each provider
actually probed (once per provider, never once per worker), every
observed quota window's `window_type`, `utilization` (%), `remaining`
(%), and `reset_at`, plus any reset credits observed (`title`,
`status`, `available` count). An unknown field renders as the literal
text `unknown`, never a fabricated `0%`/`100%`/count. A provider with
no quota windows renders `quota: unknown` instead of an empty list.

`/status` and `/workers` (no flags) are entirely unaffected; `/run`
stays project start/resume, unchanged.

## M2 — Session commands and flags

Full contract: `M2_SPEC.yaml` and `docs/SESSION_CONTRACT.md`.
Conventions deliberately close to Codex CLI/Claude Code — using the
current, pre-M8 binary name:

```
aido-code resume                # interactive session picker
aido-code resume <session-id>   # resume a specific session
aido-code --resume <session-id> # Claude-style alias
aido-code -r <session-id>       # short alias

aido-code --continue            # continue the most recent session
aido-code -c                    # short alias
```

Equivalently: `python -m aido_code resume`, `python -m aido_code
--resume <session-id>`, etc.

In the REPL:

```
/resume
/new
```

All of the above are session-level and **never** automatically call
`OrchestratorEngine.run()`, probe/select a worker, or otherwise touch
engine state — see `docs/SESSION_CONTRACT.md` and "Session resume vs.
project run/resume" in `ARCHITECTURE.md`. Resuming a session only
restores AIDO Code's own UX state; advancing the project always
requires a separate, explicit `/run`.

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
A conversational layer may explain/summarize; it never becomes a
second authority on project state.

## M4 — Non-interactive mode

```
aido-code -p "status"
aido-code -p "continue le projet"
echo "status" | aido-code -p
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

## M6 — `aido-code doctor`

Read-only diagnostics, covering (as far as each can honestly be
determined without side effects): engine version, config, project
state, Git, Ralph, providers, workers, observable quota, QA, permission
mode.

## M7 — Timeline

Renders `RunResult.events`/a future engine event stream: DEV A, DEV B,
QA, Git, WAITING, BLOCKED, COMPLETED. Granularity is bounded by what
the engine actually emits; see "Events" in `ARCHITECTURE.md`.

## M8 — `aido` command cutover

Gated on functional parity with the orchestrator's own existing `aido`
CLI (`init`/`validate`/`run`/`status`). Before that point, this project
never claims the `aido` command name; it runs as `python -m
aido_code`/`aido-code`. The orchestrator's own console script is
retired or renamed in a separate, later decision.

**Known gate, not yet resolved**: the orchestrator's public
`orchestrator.engine.OrchestratorEngine` façade currently exposes
`.validate()`/`.status()`/`.workers()`/`.probe_workers()`/`.run()`/
`.close()` — no public `.init()` method — while parity requires
matching all four of `init`/`validate`/`run`/`status`. This project
must never import private helpers from `orchestrator.cli` to work
around this gap. See `ROADMAP.md`, "M8", for the options to evaluate —
not decided here, and not something M2 depends on or blocks on.

### M8 future syntax (post-cutover only, never mixed with the current syntax above)

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

Only as real needs are established: background jobs, attach, logs,
stop, respawn, MCP, hooks, plugins, a TUI. None of these are scoped or
designed yet.
