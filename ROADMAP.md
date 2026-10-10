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
| M3.2 — Conversational terminal interface (Textual, French by default) | `APPROVED` — current milestone |
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

M3.2 is the current milestone. M4 remains the next candidate after it and
is not started.

## Current milestone

Status: APPROVED

### ID

m3.2

### Objective

Replace the line-based `aido>` prompt with a modern conversational
terminal interface, in the spirit of Claude Code and Codex, without a
second orchestration path. Running `aido` in an interactive terminal opens
a Textual application: the conversation and live engine events scroll
above, the input line stays fixed at the bottom, previous messages stay
reachable by scrolling, submitted lines are recallable from the keyboard,
and a long governed run never freezes the screen. Interface texts are in
French by default, English on request, through a deterministic message
catalog with no AI call. Commands, flags, API names, identifiers and raw
worker output are never translated.

The interface reuses `EngineClient`, the public `EngineEvent` stream, the
existing shared live run path, M2 sessions and the WI-M3-03 deterministic
intent router. It recognizes only the existing intents; any other request
gets a French explanation of what is understood, never a simulated general
assistant. Scripts and non-interactive input keep the classic line
interface and its current output unchanged.

Textual owns the main thread and receives Ctrl+C as a key, so the engine
runs in a worker thread. The engine prerequisite is
`OrchestratorEngine.run(interrupt=threading.Event)` (`ai-dev-orchestrator`
`ae43a0e`): setting it cancels the current cycle exactly like a real
Ctrl+C (process group terminated, `*.interrupted` events, nothing
completed or merged) and raises `KeyboardInterrupt`. Recovery stays
entirely the engine's on the next run.

### Acceptance criteria

- `aido`, `aido resume` and `aido --continue` open the Textual interface when stdin and stdout are terminals; otherwise the classic `run()` loop and its output are unchanged.
- The input line stays visible at the bottom while conversation and events scroll above; earlier messages stay reachable by keyboard and mouse scrolling.
- Up/Down recall previously submitted lines of the current interface session.
- Every slash command and recognized intent goes through one shared dispatcher used by both the classic loop and the interface; no second command, intent, session or orchestration implementation.
- A governed run shows live developers (DEV A/DEV B/DEV FIX with worker), tests (QA), Git, errors and results as they happen, while the interface stays responsive.
- Ctrl+C during a run requests the engine interruption once, keeps the interface open until the engine thread has finished, shows the interruption notice and leaves no process behind; the next run uses the engine's unchanged recovery.
- French is the default interface language; `aido --lang en|fr` or `AIDO_LANG` selects it; no new `aido.yaml` key; translations are deterministic.
- Only public engine facts are displayed, as plain sanitized text; no private reasoning.
- All tests and QA are offline; the 311 existing tests keep passing; `git diff --check` is clean.

### WorkItems

#### WI-M3.2-01 — Shared command dispatcher and deterministic French/English catalog

Dependencies: none
Capabilities: development

Acceptance criteria:

- Extract the per-line handling of `repl.run()` into one shared dispatcher; `repl.run()` keeps its exact signature and observable output and becomes a thin loop over it.
- Add `aido_code.i18n` with `fr` (default) and `en` catalogs keyed by stable message identifiers; lookup is a pure function with no network or AI call; a missing key falls back to the English source text.
- Cover the interface's own known texts: help, input placeholder, not-understood explanation, session messages, run start/summary labels, interruption notice, diagnostic labels, and labels for known engine event kinds (for example `work_item.completed` → "Tâche terminée", QA pass → "Tests validés", waiting for a provider → "En attente d'une IA disponible").
- Never translate commands, flags, API names, WorkItem/worker/session ids, SHAs, paths, or raw worker stdout/stderr.
- Language selection: `aido --lang en|fr` (accepted alongside the existing subcommands and the no-argument start) and `AIDO_LANG`; `--lang` wins; an invalid value prints a clear error and exits 2; no `aido.yaml` change.
- The not-understood explanation in French lists what is understood (status, workers, why waiting/blocked, run/continue) and the slash commands; it never claims general assistant abilities.
- Classic non-interactive output stays byte-identical to the current behavior.
- Offline tests: fr/en catalogs define the same keys; examples above translate as specified; raw output and identifiers are untouched; dispatcher parity for every existing command; existing tests pass unchanged.

#### WI-M3.2-02 — Textual conversational interface

Dependencies: WI-M3.2-01
Capabilities: development

Acceptance criteria:

- Declare `textual>=8.2,<9` in `pyproject.toml`; keep the dependency optional at import time for the classic path so non-interactive use never imports Textual.
- `aido` with no subcommand, `aido resume` and `aido --continue` start the Textual app when `sys.stdin.isatty()` and `sys.stdout.isatty()`; otherwise run the classic loop unchanged.
- Layout: a scrollable conversation log above, an input line docked at the bottom, a status bar showing project, session, language and idle/running state.
- Keyboard: Enter submits; Up/Down recall submitted lines; PageUp/PageDown and mouse wheel scroll the log; new output auto-follows only while the view is at the bottom; `/exit` or Ctrl+D quits when idle.
- Submitted lines are dispatched through the WI-M3.2-01 dispatcher with the current M2 session; results appear as styled messages distinguishing user input, information, errors and results.
- All dynamic text is rendered as plain sanitized text (no Rich/Textual markup interpretation of engine or user content).
- Offline tests with Textual's `App.run_test()`: the input stays docked after many messages, scrolling reaches earlier messages, history recall, `/help` and a status request with a fake engine, the French not-understood explanation, English via `--lang en`, and the non-TTY fallback.

#### WI-M3.2-03 — Live run, responsiveness and interruption in the interface

Dependencies: WI-M3.2-02
Capabilities: development

Acceptance criteria:

- `/run` and a recognized run/continue request in the interface reuse the shared live run path; `EngineClient.run` accepts an optional `interrupt` and passes it to `OrchestratorEngine.run(interrupt=...)`; the engine runs in a Textual thread worker and events reach the UI via `call_from_thread`.
- Fail closed with a clear compatibility message when the loaded engine's `run` lacks `interrupt`; the classic path does not require it.
- Present live facts by role: developer phases with worker name, QA/tests, Git, errors, final result; worker output as a distinct dimmed block; heartbeats update the status bar instead of adding lines; truncation notices and final diagnostics stay visible.
- While a run is active the interface stays responsive (scrolling, history, status bar); other commands are refused with a short translated message instead of starting concurrent engine work.
- Ctrl+C during a run sets the interrupt once and shows that interruption was requested; the app never exits while the engine thread is alive; after it ends, the interrupted events and the existing interruption notice are shown. Ctrl+C when idle clears the input and reminds how to quit. Quitting during a run first requests interruption and waits.
- Only public `EngineEvent` fields and `RunResult` diagnostics are displayed; a private-reasoning sentinel placed outside public fields never appears.
- Offline tests with a fake engine client: progressive display before the run completes, responsiveness during a run, Ctrl+C sets the interrupt and the app waits for the worker, notice displayed, the next run is delegated unchanged, incompatible engine message, no sentinel leak; zero real provider calls.

#### WI-M3.2-04 — Interface acceptance fixes from the real terminal run

Dependencies: WI-M3.2-03
Capabilities: development

Acceptance criteria:

- The interactive Textual interface defaults to French when neither `--lang` nor `AIDO_LANG` is set; the classic non-interactive path keeps its current English output unchanged.
- In the interface only, worker output (`execution.output`) is readable: ANSI SGR color/style sequences are rendered as styles or removed instead of shown as escaped `\x1b[...` text, real line breaks split lines instead of showing a literal `\n`, and any other control character is still escaped by `sanitize_for_terminal`.
- The run start notice appears in the log as soon as a run starts, before the first live event, not after the run ends.
- The status bar labels (project, session, language, idle/running state) are translated through the catalog.
- Offline tests cover the French default of the interface, readable worker output with ANSI sequences and multi-line chunks, start-notice ordering before live events, translated status bar, and unchanged classic output; zero real provider calls.

### QA

#### QA-M3.2-01 — Full offline test suite

Kind: unit_test
Required: true
Timeout: 600
Argv: ["pytest", "-q"]

### Out of scope

- M4 non-interactive mode, P14 consumption metrics, or any engine change beyond the merged `interrupt` prerequisite.
- A general conversational assistant, LLM intent classification, AI translation, RAG or new conversational persistence.
- New `aido.yaml` keys, new session storage formats, or a second orchestration, recovery or worker-selection path.
- Changing persisted M3/M3.1 states or the classic non-interactive output.
