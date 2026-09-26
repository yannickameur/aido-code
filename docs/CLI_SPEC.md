# CLI spec

The command/flag surface, milestone by milestone. See `ROADMAP.md` for
what each milestone delivers and its acceptance criteria.

## Binary name

**`aido ...` is the real, current command (M8, `DONE`).** `aido-code
...`/`python -m aido_code ...` remain fully equivalent, kept
indefinitely as a compatibility alias — both resolve to the exact same
`aido_code.__main__:main`, never a duplicated implementation. Examples
below use `aido` by convention; substituting `aido-code` anywhere below
changes nothing. See `ROADMAP.md`, M8, for the cutover itself — the
`aido` name no longer belongs to `ai-dev-orchestrator`'s own legacy CLI,
which installs no console script at all any more (that project's own
P13.6).

## Command reference

| Command | Status | Purpose | Provider call |
|---|---|---|---|
| `init <parent-path> <name>` | `M1.4` | Bootstrap a new project (manifest + `ROADMAP.md` DRAFT + `resources/` + Git) | No |
| `validate` | `M1.4` (CLI-level; also `/validate` in the REPL) | Manifest + roadmap + resources + AIDO registry validation | No |
| `run` | `M1.4` (CLI-level; also `/run` in the REPL) | Start or resume project execution, requires `Status: APPROVED` | Potentially |
| `/help` | `IMPLEMENTED` | List available commands | No |
| `/status` | `IMPLEMENTED`, extended `M1.4` | Roadmap milestone facts + project + MVP + work items + all AIDO-configured workers | No |
| `/status --probe` | `IMPLEMENTED` | Same, plus one real `probe_workers()` call | Yes |
| `/workers` | `IMPLEMENTED` | AIDO's own configured workers (static view, `M1.4`: sourced from AIDO's global config, never a project's) | No |
| `/workers --probe` | `IMPLEMENTED` | Workers, plus live provider/quota state | Yes |
| `/config` | `IMPLEMENTED`, extended `M1.4` | Manifest + roadmap facts + loaded engine facts | No |
| `/validate` | `IMPLEMENTED` | Same as the CLI-level `validate` above, from inside the REPL | No |
| `/run` | `IMPLEMENTED` | Same as the CLI-level `run` above, from inside the REPL | Potentially |
| `/exit` | `IMPLEMENTED` | Exit the REPL | No |
| `resume`, `resume <session-id>` | `M2` | Resume a frontend session by id | No |
| `--continue`/`-c` | `M2` | Resume the most recent session | No |
| `/resume` | `M2` | Resume picker, from inside the REPL | No |
| `/new` | `M2` | New frontend session | No |
| Free-form natural language | `M3` | Status/steering questions | Depends |
| `-p "<request>"` | `M4` | Non-interactive mode | Depends |
| `--output json`/`stream-json` | `M5` | Structured output | No |
| `doctor` | `M6` | Read-only diagnostics | No |
| Timeline | `M7` | Real-time event feed | No |

Each command maps directly to one `OrchestratorEngine` call (see
`docs/ENGINE_CONTRACT.md`): `/status` → `.status()`, `/workers` →
`.workers()`, `validate`/`/validate` → `.validate()`, `run`/`/run` →
`.run()`. `/config` shows the loaded manifest/roadmap facts plus
`.validate()`'s `ProjectSnapshot`, never a raw file dump. `run`/`/run`
is also how a project resumes; see "Session resume vs. project run" in
`ARCHITECTURE.md`.

## M1.4 — Autonomous AIDO project contract

Full grammar/schema: `docs/PROJECT_CONTRACT.md`. Full milestone
rationale: `ROADMAP.md`, M1.4.

```
aido init <parent-path> <project-name>   # scaffold a new project
aido validate                            # manifest + roadmap + resources + AIDO registry, provider-free
aido run                                 # requires the roadmap's Current milestone: Status: APPROVED
```

`init`/`validate`/`run` are new **CLI-level** subcommands (argv-based,
before the REPL starts) — real functional parity with
`ai-dev-orchestrator`'s own legacy `aido init/validate/run/status` CLI
(that project's own P13.5-documented transitional surface, now retired
as a console script per its own P13.6). This parity is exactly what let
M8's own binary-name cutover happen immediately after M1.4 — see
`ROADMAP.md`, M8. `validate`/`run` also remain available
as `/validate`/`/run` from inside the REPL, delegating to the exact
same underlying logic — never a second, duplicated implementation.

A project's own `aido.yaml` no longer resembles `ai-dev-orchestrator`'s
own schema: no `workers:`/`providers:`/`models:`/`mvp:`/`work_items:`/
`qa:`. It names a project, a `ROADMAP.md`, a `resources/` directory, and
an `initial_prompt` — see `docs/PROJECT_CONTRACT.md` §2. `ROADMAP.md`
itself, parsed deterministically (§3), replaces `MVP_SPEC.yaml`'s
future role as the executable acceptance contract.

`/workers`/`/status`/`/config` are otherwise unchanged commands whose
underlying data now comes from AIDO's own global worker configuration
(`docs/PROJECT_CONTRACT.md` §4) and the parsed manifest/roadmap, never
from a project-level `workers.yaml`.

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

Full contract: `ROADMAP.md`, M2. Conventions deliberately close to
Codex CLI/Claude Code:

```
aido resume                # interactive session picker
aido resume <session-id>   # resume a specific session

aido --continue            # continue the most recently used session
aido -c                    # short alias
```

Equivalently: `python -m aido_code resume`, `python -m aido_code
--continue`, etc.

In the REPL:

```
/resume
/new
```

Not added in M2: `--resume`/`-r` — `resume <session-id>` already covers
that capability; a separate alias is not needed.

All of the above are session-level and **never** automatically call
`OrchestratorEngine.run()`, probe/select a worker, or otherwise touch
engine state — see "Session resume vs. project run/resume" in
`ARCHITECTURE.md`. Resuming a session only restores AIDO Code's own
minimal frontend state (and its optional project binding); advancing
the project always requires a separate, explicit `/run`.

**Works without a project (`aido.yaml`) present**: `aido` with no
project detected, `aido resume`/`--continue`/`-c`, and REPL `/new`/
`/help` all start a session with `project_path = null` rather than
failing — see `ROADMAP.md`, M2. A project-requiring command
(`/status`, `/workers`, `/validate`, `/run`) issued from a session with
no project bound replies with a clean "no project bound" message; it
never crashes, fabricates a project, or searches for one.

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

## M8 — `aido` command cutover (`DONE`, 2026-09-25)

Completed right after M1.4, which already delivered functional parity
with the orchestrator's own legacy `aido` CLI (`init`/`validate`/`run`/
`status`). `aido` is now this project's own real, primary command
(`aido_code.__main__:main`); `aido-code`/`python -m aido_code` remain a
compatibility alias, kept indefinitely. `ai-dev-orchestrator`'s own
console script was retired (that project's own P13.6) — a plain `pip
install ai-dev-orchestrator` installs no command at all any more; that
distribution's legacy `orchestrator.cli` module stays importable,
internal-only. See `ROADMAP.md`, M8, for the full record.

**Gate that turned out moot**: the orchestrator's public
`orchestrator.engine.OrchestratorEngine` façade exposes
`.validate()`/`.status()`/`.workers()`/`.probe_workers()`/`.run()`/
`.close()` — still no public `.init()` method. This never blocked
parity: `aido init` is entirely this project's own logic
(`aido_code.project_init`), never a call into the engine. This project
still never imports private helpers from `orchestrator.cli`.

### Future command syntax (not yet built — M2/M3/M4/M6, binary name already `aido`)

The binary name itself is no longer a gate for any of these — only the
commands themselves remain unbuilt:

```
aido resume
aido resume <session-id>
aido --continue
aido -c
aido -p "status"
aido doctor
```

## M9+

Only as real needs are established: background jobs, attach, logs,
stop, respawn, MCP, hooks, plugins, a TUI. None of these are scoped or
designed yet.
