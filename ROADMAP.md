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
| M3.2 — Conversational terminal interface (Textual, French by default) | `DONE` (2026-10-10) |
| M3.3 — Simplified interface display with on-demand details | `APPROVED` — current milestone |
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

M3.2 is `DONE` (governed flow plus a real terminal acceptance). M3.3 is the
current milestone. M4 remains the next candidate and is not started.

## Current milestone

Status: APPROVED

### ID

m3.3

### Objective

Make the Textual interface as readable as possible. By default a run shows
short, human sentences built only from real public engine events, for
example "Alice développe…", "Alice a terminé son développement", "Victor
vérifie le code…", "Tests en cours…", "Tests validés", "Fusion du code
terminée", "Tâche terminée". Technical prefixes such as `[dev_b.started]`,
unneeded identifiers and Ralph's internal logs are hidden in that view.
A keyboard shortcut switches, at any time including during a run, to a
detailed view with the technical events, worker output and diagnostics.
The details come from a bounded in-memory history; no second permanent
copy of the logs is written.

The work reuses `tui.py`, `live_run.py`, the `i18n.py` catalog and the
public `EngineEvent` stream. No engine change, no governance change, and
the classic script output stays unchanged. Errors, useful diagnostics,
Ctrl+C interruption and recovery stay visible in both views. No action,
result or progress is ever invented, and no private reasoning is shown.

### Acceptance criteria

- The interface starts in the simplified view; a run shows one short translated sentence per meaningful real event and nothing for events without a sentence.
- A documented shortcut toggles simplified/detailed view instantly, also during a run, without blocking the engine or losing entries.
- The detailed view shows the current technical rendering (event kinds, metadata, worker output, truncation, diagnostics) from a bounded in-memory history.
- Errors, failures, waiting/blocked states, diagnostics, interruption and recovery notices appear in both views.
- French by default, English via the existing language selection; worker output, technical names and commands are never translated.
- The classic non-interactive output is byte-identical to before.
- All tests and QA are offline; the full existing suite keeps passing; `git diff --check` is clean.

### WorkItems

#### WI-M3.3-01 — Simplified event sentences

Dependencies: none
Capabilities: development

Acceptance criteria:

- Add a pure function in `live_run.py` that returns the simplified sentence for one public `EngineEvent`, or `None` when the event has no simplified form; it reads only public event fields and never raises for a malformed or unknown event.
- Sentences come from new `i18n.py` keys in `fr` and `en`, with the worker display name when the event supplies it: DEV A started/completed ("{worker} développe…", "{worker} a terminé son développement"), DEV B started/completed ("{worker} vérifie le code…", "{worker} a terminé sa vérification"), DEV FIX started/completed ("{worker} corrige le code…", "{worker} a terminé sa correction"), QA started/pass/fail/inconclusive ("Tests en cours…", "Tests validés", "Tests en échec", "Tests non concluants"), merge completed ("Fusion du code terminée"), WorkItem started/completed/needs rework ("Nouvelle tâche : {work_item}", "Tâche terminée", "Tâche à reprendre"), and the run interruption events.
- Failure, blocked, waiting and recovery-required events always produce a sentence that keeps the essential reported facts (WorkItem, worker when known, reason or eligible time when the engine supplies it); unknown event kinds whose name contains failed/error/blocked produce a generic translated error sentence with the kind.
- `execution.output`, `execution.heartbeat`, `execution.output_truncated` and `*.selected` events have no simplified sentence; a missing worker name yields a neutral sentence ("Développement en cours…"), never an invented name.
- The existing `render_event`, `LiveRunRenderer`, `format_diagnostics` and classic output are unchanged.
- Offline tests: every listed event in fr and en, missing worker name, failure facts preserved, unknown and malformed events, a private-reasoning sentinel outside public fields never appears, classic output unchanged.

#### WI-M3.3-02 — Simplified/detailed views in the Textual interface

Dependencies: WI-M3.3-01
Capabilities: development

Acceptance criteria:

- The interface starts in simplified view; live events display the WI-M3.3-01 sentence in that view and the existing `render_event` text in detailed view; events without a sentence (worker output, heartbeat, truncation, selection) appear only in detailed view; the heartbeat keeps updating the status bar in both views.
- Ctrl+O toggles the view at any time, including during a run, and the status bar shows the current view in the current language; the shortcut is listed in `/help` in both languages.
- Each live entry keeps both renderings in a bounded in-memory history (a `collections.deque` with a fixed maximum, at least 2000 entries); toggling rebuilds the log from that history plus the non-event conversation messages, keeps their order, and follows the bottom only if the view was at the bottom; nothing is written to disk.
- Errors, diagnostics, interruption and recovery notices, and command results appear in both views.
- Event handling stays on the existing `call_from_thread` path; toggling never blocks or cancels the engine worker, and Ctrl+C keeps its current behavior in both views.
- Offline tests with `App.run_test()` and a fake engine client: simplified default, toggle during a run, both views keep all entries in order, history bound respected, French and English labels, errors and diagnostics visible in simplified view, Ctrl+C during a run still sets the interrupt and the app waits, classic non-TTY path unchanged.

### QA

#### QA-M3.3-01 — Full offline test suite

Kind: unit_test
Required: true
Timeout: 600
Argv: ["pytest", "-q"]

### Out of scope

- Any change to `ai-dev-orchestrator`, the governance, the engine event model or the classic script output.
- Summarizing or classifying raw worker output, inventing progress, or showing private reasoning.
- Persisting logs, new `aido.yaml` keys, M4 or P14.
