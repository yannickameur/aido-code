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
| M3.3 — Simplified interface display with on-demand details | `DONE` (2026-10-10) |
| M3.4 — AI plan quotas and execution time summary (engine P14 simplified) | `DONE` (2026-10-10) |
| Release v0.2.0 (GitHub Release, engine v0.2.0) | `DONE` (2026-10-10) |
| M3.5 — Terminal reliability fix (workers isolated from the terminal, reliable exits, /export) | `APPROVED` — current milestone |
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

- Both packages are published as GitHub Releases v0.2.0 (wheel and
  sdist); AIDO Code requires `ai-dev-orchestrator>=0.2.0,<0.3`. PyPI
  publication is a separate, undecided step. Development still uses two
  sibling checkouts with `pip install -e ../ai-dev-orchestrator`.

## Next milestone to discuss

M3.2, M3.3 and M3.4 are `DONE` (governed flow plus real terminal
acceptance). The `## Current milestone` block below keeps M3.4's contract
only because the parser requires one. M4 remains a candidate and is not
started.

The interruption defect found during the M3.3 real acceptance (a surviving
`ralph` kept working and committing after Ctrl+C) is fixed in
`ai-dev-orchestrator` `bd176c3`: the engine now terminates the whole worker
session and returns only once no worker process is left.

## Current milestone

Status: APPROVED

### ID

m3.5

### Objective

Urgent fix found while developing the Flutter tic-tac-toe app for real:
mouse reports appeared in the input, Ctrl+C and Ctrl+D stopped working,
text could not be copied, and the terminal window had to be closed. The
cause, reproduced in a real pseudo-terminal, is that workers inherit the
terminal on stdin. M3.5 isolates the terminal from every worker, restores
the terminal on every exit, makes exits reliable, and adds an honest way
to recover displayed text. No interface redesign and no engine change.

### Acceptance criteria

- Workers started from the interface never receive the terminal on stdin; the terminal state is restored on every exit.
- Ctrl+C, Ctrl+D, /exit, /quit and F10 behave as specified; /export recovers all displayed text.
- Simplified/detailed views, quotas, execution times, French by default and the classic output are unchanged.
- All tests and QA are offline; the full suite keeps passing.

### WorkItems

#### WI-M3.5-01 — Isolate the terminal from workers and make exits reliable

Dependencies: none
Capabilities: development

Acceptance criteria:

- Root cause, reproduced in a real pseudo-terminal: the engine starts workers without redirecting stdin, so ralph, the provider CLIs and tools such as the Flutter tool inherit the terminal on fd 0. A child that restores cooked mode (as Dart's stdin.lineMode/echoMode does) or reads stdin breaks Textual's raw mode: SGR mouse reports like ^[[<35;153;41M are echoed, typed keys stop reaching the app, Ctrl+C and Ctrl+D no longer work. Do not hide characters; fix the cause in AIDO Code. Do not change ai-dev-orchestrator.
- In src/aido_code/tui.py, run_tui runs the app inside one context manager that, before App.run(): duplicates fd 0 to a private non-inheritable descriptor, saves its termios attributes, makes Textual read from it by temporarily replacing sys.__stdin__ and sys.stdin with a file object on that descriptor (Textual's Linux driver uses sys.__stdin__.fileno()), and points fd 0 to /dev/null so every process the engine starts inherits /dev/null instead of the terminal.
- On every exit path of run_tui (normal quit, exception, KeyboardInterrupt) the context manager restores the saved termios attributes, writes the mouse/paste disable sequences (?1000l ?1002l ?1003l ?1006l ?1015l ?2004l) and shows the cursor, puts the terminal back on fd 0, restores sys.__stdin__/sys.stdin and closes the private descriptor. An atexit handler performs the same terminal restoration once if the process ends without leaving the context. The classic non-interactive path is unchanged.
- Reliable exits in the interface: Ctrl+C during a run requests the engine interruption once, as today; Ctrl+C when idle clears a non-empty input, and on an empty input shows a translated hint and quits if pressed again within 2 seconds; Ctrl+D when idle quits; /exit and a new /quit command quit when idle; F10 is an emergency quit key that does not depend on Ctrl. Quitting during a run (Ctrl+D, /exit, /quit, F10) first requests the interruption and waits for the engine thread, as today. All new texts go through i18n.py (fr default, en) and are listed in /help.
- Regression tests: a unit test proves that inside the context manager a child subprocess started with default stdin sees /dev/null (not a TTY) while Textual's descriptor still refers to the original input, and that fd 0, sys.__stdin__ and termios attributes are restored afterwards, including after an exception; Textual pilot tests cover the idle Ctrl+C double press, Ctrl+D, /exit, /quit and F10, and quitting during a run waits for the interrupted fake engine; a real pseudo-terminal test (pty.fork, Linux only, skipped elsewhere) starts the interface with a fake engine whose worker child restores cooked mode on its inherited stdin, then sends SGR mouse reports, text, Ctrl+C and Ctrl+D and asserts that the fake engine sees the interrupt and the process exits.
- Do not install packages or modify any virtualenv; do not run the installed aido command; run tests with: PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider. Keep simplified/detailed views, quotas, execution times, French by default and the engine behavior unchanged; existing tests must keep passing.

#### WI-M3.5-02 — Recover displayed text with /export and honest selection

Dependencies: WI-M3.5-01
Capabilities: development

Acceptance criteria:

- Text recovery without fake shortcuts: set AidoApp.ALLOW_SELECT = False so a mouse drag never shows a Textual selection that cannot be copied (Ctrl+C stays the interruption key); keep mouse wheel scrolling. Document in /help, in both languages, that the terminal's own selection works with Shift+drag while the mouse is captured.
- Add a /export command that writes, in order, every conversation message and every entry of the bounded event history in its detailed rendering, plus the latest execution time table and run summary when present, to a UTF-8 text file under the XDG state directory (XDG_STATE_HOME or ~/.local/state)/aido/exports/<session-id>-<UTC timestamp>.txt, never inside the project directory; it prints the full path in the log; it works during a run and when idle; writing errors are shown as translated errors.
- Exported text is the same sanitized public text the interface displays (no private reasoning, no markup); nothing shown is omitted except entries already evicted from the 2000-entry history, which the export header states explicitly when it happened.
- Offline tests: ALLOW_SELECT is False; /export content order and completeness for conversation, history in detailed rendering, table and summary; export during a run; XDG_STATE_HOME honored and the project directory untouched; eviction notice; French and English texts; /help lists /export, /quit, F10 and Shift+drag.
- Do not install packages or modify any virtualenv; do not run the installed aido command; run tests with: PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider. Existing behavior and tests stay unchanged.

#### WI-M3.5-03 — Interrupt the engine cleanly when the terminal window closes

Dependencies: WI-M3.5-02
Capabilities: development

Acceptance criteria:

- Found in the real terminal test: closing the terminal window during a run (SIGHUP) killed the interface without asking the engine to interrupt; the worker kept running unattended for about 40 s, committed on the WorkItem branch, and the execution and WorkItem were left 'running' for engine recovery.
- While the Textual interface runs (inside run_tui's terminal isolation), install handlers for SIGHUP and SIGTERM that request the same engine interruption as Ctrl+C (set the active run's interrupt event, thread-safe, no Textual call from the signal handler that can block), then wait for the engine thread to finish for at most 60 seconds before the process exits; when idle they simply quit. Writes to a vanished terminal (EIO/EBADF) must not raise out of this path. Previous handlers are restored when run_tui returns.
- Do not change ai-dev-orchestrator, the classic non-interactive path, or the existing Ctrl+C/Ctrl+D/quit behavior.
- Regression tests: a unit test sends SIGHUP to the process while a fake engine run is active and asserts that the fake engine sees the interrupt, the run is reported interrupted, and run_tui returns; idle SIGTERM quits; previous signal handlers are restored; a real pseudo-terminal test (pty.fork, Linux only) closes the master side during a fake run and asserts that the fake engine sees the interrupt before the process exits.
- Do not install packages or modify any virtualenv; do not run the installed aido command; run tests with: PYTHONPATH=src python3 -m pytest -q -p no:cacheprovider. Existing tests keep passing.

### QA

#### QA-M3.5-01 — Full offline test suite

Kind: unit_test
Required: true
Timeout: 600
Argv: ["pytest", "-q"]

### Out of scope

- Interface redesign, a multi-AI hub, or any change to `ai-dev-orchestrator`.
- Changes to the classic non-interactive output.
