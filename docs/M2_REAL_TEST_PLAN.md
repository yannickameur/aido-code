# M2 real test plan

Scenarios to run **after** M2 (`M2_SPEC.yaml`, `docs/SESSION_CONTRACT.md`)
is actually built by the governed WorkItem Flow (`aido.m2.example.yaml`,
WI-M2-01 through WI-M2-10). **Not executed by this preparation task.**
WI-M2-01 through WI-M2-10's own offline pytest QA is the primary,
automated acceptance gate (`M2_SPEC.yaml`, criterion 17); this plan is
the additional real, human-driven smoke pass to run once that QA is
green — mirroring how M1's own real smoke test was run after its
WorkItems completed (`docs/M1_REFERENCE_RUN.md`).

**Provider consumption note**: every scenario below is read-only/session-
level and consumes no real provider — except **TEST 12**, which
explicitly exercises `/run` and therefore *can* drive a real DEV A/DEV
B/QA/merge cycle against real providers if a WorkItem is actually
eligible at that point. That is flagged inline; every other test is
provider-free by construction (this is exactly what WI-M2-08 exists to
prove automatically, offline, before this plan is ever run for real).

## TEST 1 — Create a new session

`aido-code` (or `python -m aido_code`) started fresh in a project
directory with a valid `aido.yaml`. Expect: a new session is created,
attached to that project, empty interaction history. No provider call.

## TEST 2 — Exit and resume by session id

From TEST 1's session, exit the process, note the session id, then run
`aido-code resume <session-id>`. Expect: the same session reopens with
its prior interaction history intact.

## TEST 3 — Resume with `-r`

`aido-code -r <session-id>` (and `aido-code --resume <session-id>`).
Expect: identical behavior to TEST 2's direct resume.

## TEST 4 — Resume the most recent session with `-c`

With at least two sessions on disk with different `updated_at` values,
run `aido-code -c` (and `aido-code --continue`). Expect: the session
with the latest `updated_at` reopens, per the documented deterministic
rule (`docs/SESSION_CONTRACT.md`) — never the wrong one, never
filesystem-order-dependent.

## TEST 5 — Use the `resume` picker

`aido-code resume` with no id, several sessions existing. Expect: an
interactive picker lists them; selecting one resumes it exactly as a
direct resume would.

## TEST 6 — Create `/new` from the REPL

From inside a running session, run `/new`. Expect: a fresh session id,
empty interaction history, attached to the current project, the prior
session's own file on disk untouched.

## TEST 7 — Use `/resume` from another session

From inside a running session (not the target), run `/resume` and pick
a different existing session. Expect: the REPL switches context to that
session's own state; the originating session's file is untouched.

## TEST 8 — Resume never launches a WorkItem

Resume a session bound to a project with at least one `READY`/
`NEEDS_REWORK` WorkItem. Expect: no WorkItem starts, no execution
record is created, engine state (verified via `aido-code`'s own
`/status`, or the engine's own `aido status`) is unchanged by the resume
itself.

## TEST 9 — Resume never triggers a provider call

Resume a session while monitoring for any outbound provider
call/process (e.g. no `claude`/`codex`/`vibe` subprocess spawned, no
provider probe logged). Expect: zero provider activity from the resume
itself.

## TEST 10 — Engine project in `WAITING`: resume does not disturb it

Bind a session to a project whose engine state is currently `WAITING`.
Resume the session. Expect: engine status remains exactly `WAITING`
afterward (checked via the engine's own status, not the session's
cached display) — resume never advances or clears a wait.

## TEST 11 — Engine project in `RECOVERY_REQUIRED`: resume does not consume/resolve it

Same as TEST 10, but with `RECOVERY_REQUIRED`. Expect: the status is
unchanged by the resume; only a subsequent real `/run` (TEST 12) may
resolve it, exactly as the engine itself decides.

## TEST 12 — Only then, `/run`: the engine actually resumes

**May consume a real provider.** From a resumed session (TEST 10/11's
project), explicitly run `/run`. Expect: the engine drives its own real
state machine (`WAITING`/`RECOVERY_REQUIRED`/`READY` handling) exactly
as `OrchestratorEngine.run()` defines — this is the first and only point
in this plan where an engine action, and therefore a real provider call,
is expected to happen. Confirm this only happens after an explicit
`/run`, never automatically as part of resume.

## TEST 13 — Session bound to a moved/deleted `aido.yaml`

Resume a session whose bound project directory or `aido.yaml` no longer
exists at its recorded path. Expect: a clean, explicit failure naming
the missing path (per `docs/SESSION_CONTRACT.md`'s documented choice) —
never a silent recreation of the project, never a raw traceback.

## TEST 14 — Unknown session

`aido-code resume <a session id that does not exist>`. Expect: a clean,
explicit "unknown session" error — never a silently created empty
session standing in for it.

## TEST 15 — Corrupted session

Hand-corrupt a session file on disk (e.g. truncate it / break its JSON)
and attempt to resume it. Expect: a clean, explicit error naming the
session id and the problem — never a silent drop, never a silent
"repair," never a raw traceback.

## TEST 16 — Two processes, same session

Start two AIDO Code processes and have both attempt to open the exact
same session concurrently. Expect: the documented fail-closed behavior
(`docs/SESSION_CONTRACT.md`'s concurrency contract) — one succeeds, the
other gets an explicit "already in use" error, never silent corruption
of the session file, never a torn/inconsistent write.

## TEST 17 — Simulated restart

Fully stop the AIDO Code process (not just exit cleanly — simulate a
kill/crash) mid-session, then start a new process and resume that same
session id. Expect: the session is either intact (if the last write
completed) or cleanly reported as corrupted (TEST 15's path) — never
silently and incorrectly "fine" with lost/garbled data.

## TEST 18 — M1 regression

With and without an active session, exercise every M1 command:
`/status`, `/workers`, `/config`, `/validate`, `/run`, `/help`, `/exit`.
Expect: identical, correct behavior to `MVP_SPEC.yaml`'s own acceptance
criteria — M2 introduces sessions without changing any M1 command's own
contract.
