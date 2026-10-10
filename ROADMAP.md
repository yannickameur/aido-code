# ROADMAP — AIDO Code

AIDO Code is the interactive terminal frontend (`aido`) for AI Dev
Orchestrator. See `README.md` for usage, `ARCHITECTURE.md` for the hard
rules it never crosses, `docs/ENGINE_CONTRACT.md` for the engine API it
consumes and `docs/PROJECT_CONTRACT.md` for the manifest and this file's
grammar. Past governed runs, incidents and detailed milestone records
live in Git history (`git log -p -- ROADMAP.md`), not here.

## Vision

A developer drives a governed project from one terminal: ask what the
project is doing, start or continue a run, watch real worker activity
live, interrupt safely, and get a clear final result. AIDO Code only
renders public engine facts; every orchestration, worker, QA and Git
decision belongs to the engine.

## Principles

- Frontend only: never call Ralph or a provider, read engine stores or
  `.ralph` files, scrape Git, or make orchestration decisions.
- One shared live run path for `aido run`, REPL `/run` and a recognized
  run/continue request.
- Show only facts the engine states; never fabricate tool/command
  activity, never display private reasoning.
- All tests and QA are offline; real providers are used only by the
  governed WorkItem Flow driving development.
- Every functional change goes through the governed flow
  (`CONTRIBUTING.md`). REUSE FIRST, KISS, YAGNI.
- This file's `## Current milestone` block follows the deterministic
  grammar of `docs/PROJECT_CONTRACT.md` §3: exactly one such section,
  `Status: APPROVED` or `Status: DRAFT`. Its content must match the
  engine's persisted MVP for that milestone.

## Where we stand

| Milestone | Status |
|---|---|
| M1 — Minimal interactive shell | `DONE` |
| M1.1 — CLI conventions and standalone install | `DONE` |
| M1.2 — Rich provider quota status | `DONE` |
| M1.3 — Audit hardening | `DONE` |
| M1.4 — Autonomous AIDO project contract | `DONE` |
| M8 — `aido` command cutover (`aido-code` kept as alias) | `DONE` |
| M2 — Sessions and resume | `DONE` |
| M2.1 — Graceful interactive interruption | `DONE` |
| M2.2 — CLI-level `aido status` parity | `DONE` |
| M2.3 — Worker pool aligned with validated providers | `DONE` |
| M3 — Conversational piloting and live execution | `PARTIAL` (historical outcome, see below) |
| M3.1 — Live operational UX and conversational completion | `DONE` (governed acceptance 2026-10-10) |
| M4 — Non-interactive mode | `À VOTER` |
| M5 — Structured output | `À VOTER` |
| M6 — Doctor/diagnostics | `À VOTER` |
| M9+ | `À VOTER`, only per real, demonstrated need |

M7 was folded into M3/M3.1 (live timeline). M3's governed run
(2026-10-06) ended `PARTIAL`: WI-M3-03 (deterministic intent router)
completed; WI-M3-01 failed and WI-M3-02/04 were blocked. Those persisted
statuses are never reopened; the unfinished scope was delivered by M3.1.

M3.1 acceptance: all three WorkItems completed through the governed
flow; engine P21.1 closed the private-reasoning display defect
(`wi-acc-01` `COMPLETED`, governed QA PASS on engine `f1e28f8d`, 1441
engine and 311 AIDO Code tests PASS, governed merge and tag, real Ctrl+C
and resume PASS on `p211-live7`). No non-empty real `thinking` text was
observed; suppression is proven by deterministic synthetic tests.

## Future work

### M4 — Non-interactive mode

`aido -p "<request>"` and stdin piping. See `docs/CLI_SPEC.md`.

### M5 — Structured output

`text`/`json`/`stream-json`, built directly from `OrchestratorEngine`
snapshot dataclasses: a stable contract a script can depend on, never a
terminal-output parser.

### M6 — Doctor/diagnostics

`aido doctor`: engine, config, project, Git, Ralph, providers, workers,
observable quota, QA, permissions; read-only wherever the underlying
fact genuinely is.

### Known constraints

- No public distribution channel yet (no PyPI publish or release for
  either package). Development uses two sibling checkouts with
  `pip install -e ../ai-dev-orchestrator`.
- `ai-dev-orchestrator>=0.1.3` does not prove a packaged engine contains
  P21/P21.1; a packaged release needs a published engine version with
  them and a matching dependency minimum.

## Next milestone to discuss

None is approved. M4 is the natural next candidate; it must be specified
and approved (`Status: APPROVED`) in a new `## Current milestone` block
before any run. M4 is not started.

## Completed milestone contract (M3.1)

The block below is M3.1's approved contract, kept verbatim because the
parser requires exactly one `## Current milestone` and the engine's
persisted `m3.1` MVP was bootstrapped from it. Replace it only when the
next milestone is approved.

## Current milestone

Status: APPROVED

### ID

m3.1

### Objective

Finish the user-facing M3 capabilities now that engine P21 supplies
real worker output, neutral heartbeats, and typed failure diagnostics.
During an explicit `aido run`, AIDO Code must show useful activity while
the run is happening, then leave a clear final result. CLI `aido run`,
REPL `/run`, and a recognized run/continue request use one shared live
run path. AIDO Code remains a frontend: it renders only public engine
facts and never calls Ralph or a provider, reads engine stores or `.ralph`
files, reconstructs activity from Git, or makes orchestration decisions.

The expected human experience includes real WorkItem/DEV A/DEV B/DEV
FIX/QA/Git transitions, the selected worker and known execution
metadata, progressive stdout/stderr text, a neutral elapsed-time
heartbeat during silence, and an explicit truncation notice when P21
bounds live output. On failure, the final view explains the phase,
execution identity and available `FailureDiagnostic` facts rather than
only displaying `WI-X: failed`. Output text is never reclassified as a
tool call, test, or commit unless the engine actually states that fact.
No chain-of-thought is presented; output that cannot be classified as
safe operational text must not be shown as private reasoning.

The hard development prerequisite is the verified sibling editable
engine at SHA `6456c93828a89ffc72b1966e04bdd0fc693469a2`, loaded by
the stable `aido-runner` executable. Its public P21 surface is described
in `docs/ENGINE_CONTRACT.md`. The engine and AIDO Code still declare
`0.1.3` and `ai-dev-orchestrator>=0.1.3` respectively; that minimum
does not prove a packaged engine contains P21. A normal packaged AIDO
Code release requires a distinct, actually published engine version
containing P21 and a matching dependency minimum. No version is guessed
or changed during this preparation.

P21's real disposable Gravity spike delivered 62 progressive stdout
chunks, two heartbeats, then more output. Ralph terminated with
`max_iterations` after five iterations, no business verdict, exit code
2, no commit, and no lingering Ralph/Gravity process. This proves the
stream and diagnostic, not which tools or commands Gravity used. M3.1
renders such output faithfully without a Gravity-specific parser or a
fabricated Claude-Code-like activity model.

### Acceptance criteria

- `aido run`, `/run`, and the existing deterministic run/continue intent share one live `EngineClient.run(on_event=...)` path to `OrchestratorEngine.run(on_event=...)`.
- P18 WorkItem/DEV A/DEV B/DEV FIX/QA/Git/interruption events and P21 output, truncation, and heartbeat events are rendered promptly from public `EngineEvent` fields, with no polling or scraping.
- Actual stdout/stderr text is preserved when safe to display; dynamic terminal values pass through the existing `sanitize_for_terminal()` path; unknown or malformed events cannot abort the governed run.
- Worker/provider/backend/profile/model/quality/reasoning and commit facts are shown only when the engine supplies them; a silent worker produces only a neutral elapsed-time heartbeat.
- Each available `RunResult.diagnostics` entry gives a useful final failure explanation, including the business-verdict and Ralph facts actually reported, without asserting an unproved provider cause.
- A loaded engine lacking the required P21 `on_event`, event payloads, or `RunResult.diagnostics` fails closed with a clear compatibility message; there is no silent coarse-only fallback presented as live observability.
- Ctrl+C during CLI or REPL run produces no traceback; already rendered output remains visible, and the next run leaves recovery decisions entirely to the engine.
- Session `aido resume` and `/resume` keep their M2 meaning and never substitute for engine run recovery.
- WI-M3-03's shipped deterministic router is reused unchanged in concept; idle status questions use fresh engine snapshots and a run intent enters the shared live path.
- All tests and QA are offline, preserve M1 through M2.3 and WI-M3-03 behavior, and leave `git diff --check` clean.

### WorkItems

#### WI-M3.1-01 — Render live orchestration and worker execution stream

Dependencies: none
Capabilities: development

Acceptance criteria:

- Build one shared live-run path for CLI `aido run` and REPL `/run`; `EngineClient` passes `on_event` to `OrchestratorEngine.run(on_event=...)`, with no second orchestration path.
- Render the existing P18 WorkItem, DEV A, DEV B, DEV FIX, QA, Git, and interruption transitions as they arrive.
- Render P21 `execution.output` promptly, preserving observed text and distinguishing stdout/stderr when useful without duplicate noise or invented semantic labels.
- Render `execution.heartbeat` only as still-running with actual `elapsed_seconds`; render `execution.output_truncated` with its actual reason and delivered counts.
- Route all dynamic terminal values, including output text and metadata, through the existing `sanitize_for_terminal()` path; do not expose chain-of-thought or classify unstructured backend text as a command/tool/test.
- Handle unknown, malformed, or partial future `EngineEvent` kinds without allowing a presentation error to kill a governed run; retain the end-of-run summary after the live stream.
- Show worker/display name, provider, backend, profile, model, quality tier, reasoning effort, and commit SHA only from real `EngineEvent` fields when available.
- Consume every `RunResult.diagnostics` entry and render phase, worker/display name, provider, backend, model, execution status, known exit code, business verdict, known Ralph termination reason/iterations, last output if present, summary, and next action; never show only `WI-X: failed` when a diagnostic exists.
- Do not causally blame a provider without supporting engine facts; do not read Git, SQLite, `.ralph`, or subprocess output outside the public `EngineEvent` stream.
- Treat P21 as a hard API prerequisite and fail closed with a clear engine-compatibility message if `on_event`, required event fields/payloads, or `RunResult.diagnostics` are missing.
- Add offline tests for progressive display before run completion, metadata, stdout/stderr, heartbeat, truncation, sanitization, diagnostics, unknown events, and missing P21 API; make zero real provider calls.

#### WI-M3.1-02 — Handle graceful interruption and recovery UX

Dependencies: WI-M3.1-01
Capabilities: development

Acceptance criteria:

- Handle Ctrl+C once for the shared CLI `aido run` and REPL `/run` path, without a raw traceback or a second AIDO recovery state machine.
- Render real `run.interruption_requested`, `*.interrupted`, `qa.interrupted`, and `run.interrupted` events when supplied; preserve output already emitted before interruption.
- Tell the user that the governed engine state determines recovery on the next run; the next `aido run` calls the engine's existing recovery path unchanged.
- Keep session `aido resume` and `/resume` session-only; do not conflate them with project execution recovery.
- Add offline tests with simulated KeyboardInterrupt/cancellation only; do not call a real provider.

#### WI-M3.1-03 — Complete conversational/session integration and regression acceptance

Dependencies: WI-M3.1-01, WI-M3.1-02
Capabilities: development

Acceptance criteria:

- Reuse the delivered WI-M3-03 deterministic router and its closed intents: status/state, why waiting/blocked, workers/providers, and run/continue; do not rewrite it or add an LLM classifier.
- Route a recognized run/continue request through the exact same shared live-run path as `/run` and CLI `aido run`.
- Answer idle status questions from fresh engine snapshots; add no background monitor, polling loop, or new conversational persistence.
- Reuse only M2 `SessionStore`/project binding; add no RAG, vector database, long-term memory, or model training.
- Cover M1 through M2.3 and WI-M3-03 behavior with offline regression tests; run full `pytest -q` and `git diff --check` with zero real provider calls.

### QA

#### QA-M3.1-01 — Full offline test suite

Kind: unit_test
Required: true
Timeout: 300
Argv: ["pytest", "-q"]

### Out of scope

- Reopening or changing the persisted FAILED/BLOCKED M3 WorkItems or reimplementing WI-M3-03.
- Direct Ralph/provider invocation, engine SQLite/`.ralph`/Git scraping, or local worker selection/QA/Git decisions.
- Provider-specific output parsing, fabricated command/tool activity, or chain-of-thought display.
- New recovery state machines, background monitoring, polling, detached jobs, or remote attach.
- New conversational storage, RAG, vector databases, model training, or an LLM intent classifier.
- Publishing or inventing an engine release version as part of this documentary preparation.
