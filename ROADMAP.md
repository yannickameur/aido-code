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

m3.4

### Objective

Show, at the top of the Textual interface, the AI plans still available,
and, at the end of a development run, how long each provider actually
worked on the current milestone.

Quotas come only from the existing `EngineClient.probe_workers()` facts
(the same data as `/status --probe`, one probe per provider even with
several workers): Claude windows, Codex 5 h and 7 day limits when they
exist, Gravity `/usage` per model group, and "Non communiqué" for Mistral
Vibe when no reliable value exists. The panel shows the remaining
percentage, the period and the known reset time; it refreshes once when
the interface opens, without blocking it, then only on demand. No
periodic polling.

Execution time comes only from the engine prerequisite
`OrchestratorEngine.execution_times()` (`ai-dev-orchestrator` `3f33795`):
the engine sums recorded DEV A, DEV B and DEV FIX executions of the
current MVP per provider, including every attempt and recovery, and never
counts QA, quota waits or estimator runs. AIDO Code only displays it.
Unknown values are shown as such, never invented. No tokens, no prices,
no new storage, no change to worker selection or to the classic script
output.

### Acceptance criteria

- The interface shows a quota panel under the status bar, filled from one `probe_workers()` call started in a background worker when the interface opens; the interface stays usable meanwhile.
- A documented shortcut refreshes the quotas on demand; no other probe is ever started automatically.
- Each provider shows its remaining percentage, period and known reset time per quota window; "Non communiqué" when the provider reports no window; "Non disponible" when the probe fails or no project is open.
- After each run in the interface (completed, failed or interrupted) a "Fournisseur | Temps exécuté" table for the current milestone is shown, with a "Total IA" row and explicit unknown values.
- French by default, English via the existing language selection; Ctrl+C, recovery, both M3.3 views and the classic output stay unchanged.
- All tests and QA are offline; the full suite keeps passing; `git diff --check` is clean.

### WorkItems

#### WI-M3.4-01 — AI plan quota panel

Dependencies: none
Capabilities: development

Acceptance criteria:

- Add a one-line-per-provider quota panel docked under the status bar of `tui.py`, built only from `ProviderSnapshot` facts returned by `EngineClient.probe_workers()`.
- Provider labels: `anthropic` → Claude, `openai` → Codex, `mistral` → Mistral, `gravity` → Gravity; any other provider keeps its id. Window labels: `five_hour`/`primary_5h` → 5 h, `seven_day`/`secondary_7d` → 7 j (en: 7 d); any other window type, such as Gravity model groups, keeps its own label.
- For each window show the remaining percentage, rounded, and the reset time in local time when known; "inconnu"/"unknown" for an unknown value; "Non communiqué"/"Not reported" when a provider has no window; "Non disponible"/"Not available" when the probe raised, the provider probe reported an error, or no project is open.
- Probe once when the interface mounts, in a Textual thread worker; until it returns the panel shows a translated "Actualisation…" text; the input stays usable.
- Ctrl+R refreshes the panel on demand; a refresh requested while one is in flight is ignored; there is no timer or periodic polling; the shortcut is listed in `/help` in both languages.
- New texts go through `i18n.py` (fr default, en); provider names, window identifiers and raw values are not translated.
- Offline tests with `App.run_test()` and a fake engine client: one probe on mount, non-blocking mount, Ctrl+R triggers exactly one more probe, no probe without a request, Claude/Codex/Gravity windows, Mistral "Non communiqué", probe error and no project "Non disponible", French and English, `/status --probe` and classic output unchanged.

#### WI-M3.4-02 — Execution time summary after a run

Dependencies: WI-M3.4-01
Capabilities: development

Acceptance criteria:

- Add `EngineClient.execution_times()` as a thin pass-through to `OrchestratorEngine.execution_times()`; when the loaded engine lacks it, the interface shows a translated "Bilan des temps non disponible" line instead of failing.
- After every run started from the interface (completed, failed or interrupted, including after Ctrl+C once the engine thread has ended), read the snapshot once and show a table titled with the milestone id: columns "Fournisseur" and "Temps exécuté" (en: "Provider", "Execution time"); rows Claude, Codex, Mistral and Gravity in that order, then any other provider from the snapshot, then "Total IA" (en: "Total AI").
- Durations are formatted as hours, minutes and seconds ("1 h 02 min 05 s", "4 min 12 s", "38 s"); a provider without executions shows "Aucune exécution" (en: "No execution"); `seconds` None shows "Inconnu" (en: "Unknown"); when `unknown_executions` > 0 the row also says how many executions have no known duration.
- The table appears in both simplified and detailed views and is never computed in AIDO Code from events or timestamps of its own.
- Offline tests with a fake engine client: table after a completed run, after a failed run and after an interrupted run, provider order, missing providers, unknown durations, total row, duration formatting, engine without `execution_times()`, French and English; the classic `aido run` output is unchanged.

### QA

#### QA-M3.4-01 — Full offline test suite

Kind: unit_test
Required: true
Timeout: 600
Argv: ["pytest", "-q"]

### Out of scope

- Tokens, prices, costs, P15 or any consumption metric beyond execution time.
- Any change to `ai-dev-orchestrator`, worker selection, probes or persistence.
- Periodic quota polling, new storage, new `aido.yaml` keys, or changes to the classic script output.
