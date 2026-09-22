# Session contract (M2)

The functional contract for M2 ("Sessions and resume"). See
`M2_SPEC.yaml` for the acceptance criteria this contract must satisfy,
`ARCHITECTURE.md`'s "Hard invariant (M2)" for the resume/run separation,
and `docs/CLI_SPEC.md`'s M2 section for the exact command surface. Not
implemented yet — this document is what the governed WorkItem Flow
(`aido.m2.example.yaml`, WI-M2-01 through WI-M2-10) builds against.

## What a Session is

A Session is an **AIDO Code frontend object** — this project's own UX
state. It is not, and never becomes:

- a `Project` (the engine's own concept);
- an `MVP`;
- a `WorkItem`;
- an `ExecutionRecord`;
- a `WaitRecord`;
- a replacement for, or a copy of, any orchestrator persistence.

A Session records *how a user has been interacting with AIDO Code*, and
which project it is pointed at. It never records, and never becomes
authoritative for, what the engine itself has done or decided.

## Minimum session fields

- `schema_version` — an integer, incremented on any breaking change to
  this shape. Never inferred from file structure.
- `session_id` — see "Session identifier" below.
- `created_at` — timezone-aware timestamp, set once, never changed.
- `updated_at` — timezone-aware timestamp, updated on every write.
- **Project/config binding** — see "Session-to-project binding" below.
- **Interaction history** — see "Interaction history" below.
- Any metadata genuinely necessary to resume correctly (e.g. which
  display mode was active) — kept minimal; nothing speculative for a
  milestone (M3+) not yet built.

## Session identifier

`session_id` must be:

- **stable** — never regenerated for the same session;
- **opaque** — carries no embedded meaning a caller should parse or rely
  on (e.g. not `"<project_id>-<n>"`);
- **unique** — collision-free in practice (e.g. a UUID4 or equivalent);
- **serializable** — a plain string, safe to print, log, and pass on a
  command line (`aido-code resume <session-id>`).

`session_id` is never derived from, or coupled to, `project_id`,
`mvp_id`, `work_item_id`, a provider name, or a worker id — a session
outlives, and is entirely independent of, any specific engine identity.
Reusing or deriving a session's identity from engine identifiers would
make the two concepts leak into each other, which is exactly what this
contract exists to prevent.

## Interaction history (M2 — not an LLM conversation)

M2 comes before M3 (natural-language piloting). Its history is a plain,
structured **interaction history**, never a "conversation" and never
involving an LLM. Each entry records, at minimum:

- the user command (`/status`, `/workers`, `/config`, `/validate`,
  `/run`, `/help`, ...);
- the rendered result (or a structured reference to it — never a lossy
  re-summary a later reader could mistake for the real thing);
- a timestamp;
- the input type (REPL command, CLI flag, ...);
- any structured reference needed to reconstruct what was shown (e.g.
  which snapshot fields were rendered), without duplicating the engine's
  own snapshot types wholesale.

M3 may later extend this same model to natural-language requests; M2
itself introduces no LLM, no natural-language interpretation, and no new
authority over project state — an interaction history entry is a display
record, never a decision record.

## Persistence: ownership, location, format

Persistence belongs entirely to AIDO Code. It **never** uses, reads, or
writes any of `ai-dev-orchestrator`'s own SQLite files or its state
directory.

**Location**: `$XDG_STATE_HOME/aido-code/`, falling back to
`~/.local/state/aido-code/` when `XDG_STATE_HOME` is unset — mirroring
the engine's own P12 default-state-dir convention, but under this
project's **own** directory, never inside
`~/.local/state/ai-dev-orchestrator/`. Sessions live under a dedicated
subdirectory: `~/.local/state/aido-code/sessions/` (or the
`$XDG_STATE_HOME` equivalent).

**Format decision (KISS/YAGNI)**: one versioned JSON file per session
(e.g. `sessions/<session_id>.json`), plus a small session index file
(e.g. `sessions/index.json`) recording, per session, its id and
`updated_at` — the minimum needed for the most-recent-session rule
(`--continue`/`-c`) and the interactive picker (`resume` with no id)
without reading every session file on every invocation.

Why JSON, not SQLite: M2's actual needs (read one session by id, list a
small local index, detect corruption, evolve the schema) do not require
transactional multi-row queries, concurrent writers across many
sessions, or relational structure — a single local user's session count
is small. JSON satisfies every requirement in `M2_SPEC.yaml` (versioned,
restart-readable, corruption-detectable via a parse/schema check,
evolvable via `schema_version`, no secrets) with the smallest possible
mechanism. SQLite is not chosen by reflex; if a real, demonstrated need
appears later (e.g. very large session counts, real concurrent-access
patterns this file-based approach can't satisfy safely), that becomes a
separate, evidenced decision — not built now.

**Corruption/invalid session**: a session file that fails to parse as
JSON, or that fails basic schema validation (missing required field,
wrong `schema_version` this version of AIDO Code cannot read), is
reported as a clean, explicit error naming the session id and the
problem — never silently dropped, never silently "repaired," never
treated as if it didn't exist.

**Secrets**: a session file never contains an API key, token, or
credential of any kind — nothing here differs from `ai-dev-orchestrator`
itself on this point.

## Concurrency

M2 does not require a distributed system or a session broker/server —
explicitly not built. The minimal contract, fail-closed:

- **Never silent corruption.** Two processes must never be able to write
  the same session file concurrently and produce a torn/inconsistent
  result.
- Mechanism: an exclusive, local advisory lock held for the duration a
  session is open (e.g. a lock file next to the session file, acquired
  non-blocking). A second process attempting to open the same
  `session_id` while it is locked fails explicitly — a clear "session
  `<id>` is already in use by another process" error — rather than
  silently attaching to it or corrupting it.
- No server, no cross-machine coordination, no queueing: this is a
  single-user, local-filesystem contract only.

## `/new` — new session

A new session:

- receives a new, freshly-generated `session_id`;
- is attached to the current project/config if one is detected in the
  working directory (see binding below), otherwise created unbound;
- starts with an empty interaction history;
- creates **no** engine-side `Project`/`MVP`/`WorkItem`;
- triggers **no** provider call;
- never calls `OrchestratorEngine.run()`.

## Resume — exact command semantics

All of the below are session-level only (see ARCHITECTURE.md's "Hard
invariant (M2)"): **none of them ever call `OrchestratorEngine.run()`,
probe/select a worker, or mutate engine state.** Current, pre-M8 binary
name throughout (`docs/CLI_SPEC.md`).

- `aido-code resume` — interactive picker: lists known sessions (from
  the session index) for the user to choose one.
- `aido-code resume <session-id>` — direct resume of that exact session.
- `aido-code --resume <session-id>` / `aido-code -r <session-id>` —
  aliases of direct resume.
- `aido-code --continue` / `aido-code -c` — resumes the single most
  recently *used* session (by `updated_at` in the session index — the
  session whose `updated_at` is latest; ties, if they ever occur, break
  by `session_id` for a fully deterministic result, never by filesystem
  iteration order). Fails explicitly if no session exists yet, rather
  than silently creating one.
- REPL `/resume` — same picker as `aido-code resume`, invoked from
  inside a running session.
- REPL `/new` — see above.

## Session-to-project binding

A session stores a **stable reference** to the project it is attached
to: at minimum, the project directory and the exact path to the
`aido.yaml` used. On resume, this association is restored as-is.

The SessionStore **never**:

- duplicates `ProjectConfig` (project/worker registry contents, etc.)
  inside a session — the session only ever points at where that
  configuration lives, and reads it fresh (via
  `OrchestratorEngine.open(...)`) when actually needed;
- copies any engine state into the session.

**If the bound project directory or `aido.yaml` no longer exists**: the
resume fails cleanly with an explicit, actionable error naming the
missing path — consistent with this project's and the engine's own
fail-closed convention (see `ARCHITECTURE.md`, `CONTRIBUTING.md`). AIDO
Code never silently recreates the project or guesses a replacement path.
A degraded mode that opens the session read-only for its own interaction
history, explicitly labeled as such, is a reasonable future refinement
but is not required by M2 and is not built here (YAGNI) — M2 only needs
the clean-failure path.

## Never a duplicate source of truth for engine state

The SessionStore must **never** persist any of the following as a
source of truth:

- WorkItem status;
- MVP status;
- `WAITING`/`RECOVERY_REQUIRED`;
- `ExecutionRecord`;
- quota state;
- QA verdict;
- merge state.

All of this belongs to the engine alone. A session's interaction history
may retain a *display record* of a past `/status` result (what was shown
to the user, when) — but any **current** question about project state
must go through `OrchestratorEngine` again, never be answered from a
session's own cached copy. A session is a UX log, never a second engine.
