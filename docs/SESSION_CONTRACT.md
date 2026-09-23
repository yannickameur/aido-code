# Session contract (M2)

The functional contract for M2 ("Sessions and resume"). See
`M2_SPEC.yaml` for the acceptance criteria this contract must satisfy,
`ARCHITECTURE.md`'s "Hard invariant (M2)" for the resume/run
separation, and `docs/CLI_SPEC.md`'s M2 section for the exact command
surface. Not implemented yet — this is what the governed WorkItem Flow
(`aido.m2.example.yaml`, WI-M2-01 through WI-M2-10) builds against.

## In one sentence

A session is AIDO Code's own frontend UX state — never a `Project`, an
`MVP`, a `WorkItem`, an `ExecutionRecord`, a `WaitRecord`, or a
replacement/copy of any orchestrator persistence. It records how a user
has been interacting with AIDO Code and which project it points at; it
is never authoritative for what the engine itself has done or decided.

## Stored fields

| Field | Description |
|---|---|
| `schema_version` | Integer, incremented on any breaking change to this shape. Never inferred from file structure. |
| `session_id` | Stable, opaque, unique, serializable identifier — see "Session identifier" below. |
| `created_at` | Timezone-aware timestamp, set once, never changed. |
| `updated_at` | Timezone-aware timestamp, updated on every write. |
| Project/config binding | Directory + exact `aido.yaml` path — see "Project binding" below. |
| Interaction history | See "Interaction history" below. |
| Display metadata | Only what's genuinely necessary to resume correctly (e.g. active display mode); kept minimal, nothing speculative for M3+. |

### Session identifier

`session_id` is stable (never regenerated for the same session), opaque
(carries no embedded meaning a caller should parse, e.g. never
`"<project_id>-<n>"`), unique (a UUID4 or equivalent), and serializable
(a plain string, safe to print, log, pass on a command line). It is
never derived from `project_id`, `mvp_id`, `work_item_id`, a provider
name, or a worker id — a session outlives, and is entirely independent
of, any specific engine identity.

### Interaction history

M2 comes before M3 (natural-language piloting): its history is a plain,
structured record, never a "conversation" and never involving an LLM.
Each entry records: the user command (`/status`, `/workers`, ...), the
rendered result (or a structured reference to it, never a lossy
re-summary a later reader could mistake for the real thing), a
timestamp, and the input type (REPL command, CLI flag, ...). M3 may
later extend this same model to natural-language requests; M2 itself
introduces no LLM, no natural-language interpretation, and no new
authority over project state.

## Storage

Persistence belongs entirely to AIDO Code. It never uses, reads, or
writes any of `ai-dev-orchestrator`'s own SQLite files or its state
directory.

**Location**: `$XDG_STATE_HOME/aido-code/`, falling back to
`~/.local/state/aido-code/` when unset — mirroring the engine's own
P12 default-state-dir convention, but under this project's **own**
directory, never inside `~/.local/state/ai-dev-orchestrator/`. Sessions
live at `sessions/<session_id>.json`, plus a small index
(`sessions/index.json`: id + `updated_at` per session) — enough for the
most-recent-session rule (`--continue`/`-c`) and the interactive picker
without reading every session file on every invocation.

**Format (KISS/YAGNI)**: one versioned JSON file per session. M2's
actual needs (read one session by id, list a small local index, detect
corruption, evolve the schema) don't require SQLite's transactional or
relational features at a single local user's session count. If a real,
demonstrated need appears later (very large session counts, real
concurrent-access patterns this can't safely satisfy), that becomes a
separate, evidenced decision, not built now.

**Corruption**: a session file that fails to parse as JSON, or fails
basic schema validation (missing field, unreadable `schema_version`),
is reported as a clean, explicit error naming the session id and the
problem — never silently dropped, never silently "repaired," never
treated as if it didn't exist.

**Secrets**: a session file never contains an API key, token, or
credential of any kind.

## Commands

Current, pre-M8 binary name throughout (`docs/CLI_SPEC.md`).

| Command | Behavior |
|---|---|
| `aido-code resume` | Interactive picker over the session index |
| `aido-code resume <id>` | Direct resume of that exact session |
| `aido-code --resume <id>` / `-r <id>` | Aliases of direct resume |
| `aido-code --continue` / `-c` | Resumes the single most recently *used* session (latest `updated_at` in the index; ties break by `session_id`, never filesystem order). Fails explicitly if no session exists, rather than silently creating one. |
| `/resume` | Same picker, invoked from inside a running session |
| `/new` | New session: fresh `session_id`, attached to the detected project if one exists (else created unbound), empty interaction history, no engine-side `Project`/`MVP`/`WorkItem` created |

## Hard safety rule

**Resume never calls `OrchestratorEngine.run()`, probes or selects a
worker, or mutates engine state** — see `ARCHITECTURE.md`'s "Hard
invariant (M2)". Every command in the table above is session-level
only: it restores or creates AIDO Code's own UX state and nothing
about the engine's.

## Project binding

A session stores a stable reference to the project it is attached to:
the project directory and the exact path to the `aido.yaml` used. On
resume, this association is restored as-is. The SessionStore never
duplicates `ProjectConfig` (project/worker registry contents) inside a
session, and never copies engine state into it — a session only ever
points at where the configuration lives, read fresh (via
`OrchestratorEngine.open(...)`) when actually needed.

If the bound project directory or `aido.yaml` no longer exists, resume
fails cleanly with an explicit, actionable error naming the missing
path, consistent with this project's and the engine's own fail-closed
convention. AIDO Code never silently recreates the project or guesses
a replacement path. A degraded read-only mode (opening a session for
its own interaction history only, explicitly labeled) is a reasonable
future refinement, not required or built by M2 (YAGNI).

## Concurrency

M2 does not require a distributed system or a session broker/server —
explicitly not built. The minimal contract, fail-closed:

- Two processes must never be able to write the same session file
  concurrently and produce a torn/inconsistent result.
- Mechanism: an exclusive, local advisory lock held for the duration a
  session is open (e.g. a lock file next to the session file, acquired
  non-blocking). A second process attempting to open the same
  `session_id` while it is locked fails explicitly — "session `<id>`
  is already in use by another process" — rather than silently
  attaching to it or corrupting it.
- No server, no cross-machine coordination, no queueing: a single-user,
  local-filesystem contract only.

## What is never stored

The SessionStore must never persist any of the following as a source
of truth: WorkItem status, MVP status, `WAITING`/`RECOVERY_REQUIRED`,
`ExecutionRecord`, quota state, QA verdict, merge state — all of this
belongs to the engine alone.

A session's interaction history may retain a *display record* of a
past `/status` result (what was shown, when) — but any **current**
question about project state must go through `OrchestratorEngine`
again, never be answered from a session's own cached copy. A session is
a UX log, never a second engine.
