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
| Read-only `aido version` / `aido v` and `/version` / `/v` | `DONE` (unreleased) |
| M2.3 — Worker pool aligned with validated providers | `DONE` |
| M3 — Conversational piloting and live execution | `PARTIAL` (historical outcome, see below) |
| M3.1 — Live operational UX and conversational completion | `DONE` (governed acceptance 2026-10-10) |
| M3.2 — Conversational terminal interface (Textual, French by default) | `DONE` (2026-10-10) |
| M3.3 — Simplified interface display with on-demand details | `DONE` (2026-10-10) |
| M3.4 — AI plan quotas and execution time summary (engine P14 simplified) | `DONE` (2026-10-10) |
| Release v0.2.0 (GitHub Release, engine v0.2.0) | `DONE` (2026-10-10) |
| M3.5 — Terminal reliability fix (workers isolated from the terminal, reliable exits, /export) | `DONE` (2026-10-10) |
| Release v0.2.1 (corrective, M3.5 only; engine stays v0.2.0) | `DONE` (2026-10-10) |
| Release v0.2.2 (`aido version` / `aido v`, `/version` / `/v`; engine v0.2.1) | `DONE` (2026-10-11) |
| M3.6 — Two priority local Qwen workers (BMAX / Ollama / Ralph) | `DONE` (2026-11-02) — WI-M3.6-01/02 completed; 461 tests, real Qwen acceptance, CI and deployment PASS |
| Release v0.2.3 (engine v0.2.2, BMAX deployment and tested rollback) | `DONE` (2026-11-02) |
| M4 — Non-interactive mode | `DRAFT` (prepared for review) |
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

### M3.6 — Two priority local Qwen workers (governed implementation completed)

**2026-10-31 decision:** prioritize this over M4-M6. Track through [AIDO Code issue #17](https://github.com/yannickameur/aido-code/issues/17) and [engine P2 issue #63](https://github.com/yannickameur/ai-dev-orchestrator/issues/63). Run locally on **BMAX Ubuntu** against GitHub repositories, not GitLab or Mac; no iOS/SwiftUI, new UI, or unrelated scope.

Add two workers in AIDO's **global** registry (`worker_config.py` resolves `$XDG_CONFIG_HOME/aido/workers.yaml` then packaged defaults): `qwen_developer` and `qwen_reviewer`, both enabled, `provider: ollama`, initial model `qwen3.5:9b`, `development` capability, separate worker identities and sessions. Do not impose a BMAX-specific default on every installed AIDO or put workers in project `aido.yaml`. On the BMAX, configure an opt-in override while preserving cloud fallback. Show observed facts with existing `/workers` / `/status --probe`; no fake quota.

**Critical policy test:** when both Qwen workers and cloud workers are available, local-first **DEV A = Qwen Developer; DEV B = Qwen Reviewer** despite default cross-provider review preference. `DEV_B.worker_id != DEV_A.worker_id` stays absolute, but there is no false provider/model diversity claim. Only opt-in BMAX installations should change selection behavior. If Ollama is unreachable, use eligible cloud workers without inventing quota resets.

**Governed WorkItems to prepare after the engine P2 compatibility is validated:**

#### WI-M3.6-01 — Global Qwen workers and opt-in local-first wiring

Dependencies: none
Capabilities: development

Acceptance criteria:

- Use the existing schema and loading path; add/document two distinct Ollama worker identities with priority over cloud only in explicit BMAX configuration; no globally enabled Ollama for users who did not opt in.
- Reuse the engine's local-first selection policy once delivered; do not rebuild `WorkerSelector`, `QuotaManager`, or model detection inside the frontend.
- Offline tests cover global registry, two identities, precedence vs cloud, fallback, validation and unchanged behavior for non-opt-in installations.

#### WI-M3.6-02 — Integrate and verify BMAX release

Dependencies: WI-M3.6-01
Capabilities: development

Acceptance criteria:

- Verify compatible engine release is installed in a separate stable venv; never edit the active venv in place or import the editable checkout being modified as controller.
- Test existing frontend commands `/workers`, `/status`, `/status --probe`, `aido version`/`aido v`, plus full offline CI.
- Run real BMAX AIDO→Ralph→Qwen DEV A→different Qwen DEV B→deterministic QA PASS→governed Git merge on a disposable Git project. Verify BMAX/Ollama is the actual inference source; no false success.
- Publish only with passing tests, governed acceptance and documented rollback. Indicative target `v0.2.3` after engine v0.2.2 (confirm actual tags); GitHub wheel, sdist, checksums; no PyPI.

**State gate verified:** local persisted state was inspected before switching the current milestone to M3.6. WI-M3.6-01 and WI-M3.6-02 completed through the installed stable AIDO controller, distinct DEV phases, deterministic QA and governed merge. The final QA passed 461 tests on `904195e`; PR #19 merged the identical source tree at `be76fc6` with Python 3.10/3.12 CI green. The current milestone contract below remains unchanged for persisted-state compatibility. Final release/deployment evidence is recorded separately in [BMAX deployment](docs/BMAX_DEPLOYMENT.md).

### M4 — Non-interactive mode

See the [M4 draft](#m4--non-interactive-mode-draft) for the `-p` contract,
acceptance tests and governed WorkItems.

### M5 — Structured output

`text`/`json`/`stream-json`, built directly from `OrchestratorEngine`
snapshot dataclasses: a stable contract a script can depend on, never a
terminal-output parser.

### M6 — Doctor/diagnostics

`aido doctor`: engine, config, project, Git, Ralph, providers, workers,
observable quota, QA, permissions; read-only wherever the underlying
fact genuinely is.

### Optional project skill — UI UX Pro Max (`À VOTER`)

**Objective / value.** Let a project's prompt explicitly request
[UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
(NextLevelBuilder, open-source MIT) for user journeys, visual direction,
design systems, typography/colors/spacing, accessibility, platform-specific
UI design and review of implemented interfaces. Support any relevant web,
mobile or business application; do not specialize for the Morpion project.

**Functional scope.**

- Activate only when the user explicitly asks for **UI UX Pro Max** in
  that project's prompt, and only for relevant UX/UI tasks. A generic
  UI request alone must not activate it. Other projects remain unchanged.
- Verify real availability, an approved pinned version and compatibility
  with the selected provider before use. Missing/unsupported means a
  clear limitation, not simulated skill execution.
- Preserve useful design artifacts in the project, available to the
  development agents and an actual UX/UI review of implemented screens.
  Keep existing independent DEV B, deterministic QA, Git governance and
  permissions intact.

**Integration study required before a separate implementation GO.**

- Review existing `aido.yaml` `initial_prompt`, `ROADMAP.md` and
  `resources/` (`docs/PROJECT_CONTRACT.md`), agent selection and
  public engine boundary (`ARCHITECTURE.md`, `docs/ENGINE_CONTRACT.md`).
  REUSE FIRST, KISS, YAGNI: no new generic skills framework or second
  orchestrator unless an evidenced gap warrants it.
- Check native project-scoped Claude Code and Codex skill mechanisms.
  Upstream documents both and provides `uipro init --ai claude` and
  `--ai codex`, but this is evidence to study, **not** an instruction
  to install now. Its default auto-activation for generic UI/UX prompts
  must not violate AIDO's stricter explicit opt-in policy.
- Upstream MIT license verified. Its search scripts require Python 3
  (standard library); its optional installer is a Node/npm CLI. Audit
  source, third-party instructions, scripts, dependencies, side effects
  and permissions. Pin the verified release/commit and record actual
  origin/version for each activation; skill and CLI versions may differ.
- Prefer native providers and existing project/task configuration over
  installing globally or fetching floating latest assets. Never copy
  the skill logic into AIDO. No required Figma, Mobbin or paid service.

**Acceptance criteria (future, not yet approved for execution).**

- Explicit opt-in demonstrated with at least one supported LLM provider;
  no implicit activation, even on UI/UX work, without opt-in.
- Scoped activation, reproducible version and traceable origin; honest
  errors for missing/incompatible skills or providers.
- Useful UX/UI design artifacts consumed by developers and independent
  review of actually implemented screens.
- Tests prove both opt-in and opt-out, safety boundaries and no
  regression for ordinary projects.

**Suggested future slices, subject to validation:** (1) scoped ecosystem,
security and integration study; (2) minimal optional provider handoff;
(3) design artifact/review flow and regression/acceptance tests. Keep this
proposal `À VOTER`; do not install the skill, change production code,
create a new agent, launch a development cycle, or reorder M4-M6 now.

### Known constraints

- Engine v0.2.2 and AIDO Code v0.2.3 are published as GitHub Releases
  with wheel, sdist and verified checksums. AIDO Code requires
  `ai-dev-orchestrator>=0.2.2,<0.3`. BMAX activation and actual rollback
  are verified in [deployment evidence](docs/M36_ACCEPTANCE.json).
  PyPI publication remains a separate, undecided step.

## Next milestone to discuss

M3.6, engine v0.2.2 and AIDO Code v0.2.3 are DONE: governed implementation,
full offline suites, green CI, two real sequential Qwen sessions, deterministic
QA, governed merge, published artifacts, deployment and exercised rollback.
The current milestone contract below is preserved to match persisted state.
Installed AIDO Code v0.2.3 / engine v0.2.2 report `m3.6` as the current
persisted MVP with aggregate status `running` and both M3.6 WorkItems
`completed`. WI-M3.6-02 retains a historical wait record and there are zero
executions recorded as `running`. The read-only check found no persisted
`m4` or proposed M4 WorkItem IDs. The historical records and all SQLite
files remain intact. See [M3.6 evidence](docs/BMAX_DEPLOYMENT.md).

M4 awaits explicit approval. Its draft lives under a separate heading,
which the roadmap parser ignores. Engine v0.2.2 bootstrap can create a
fresh MVP ID and set it as current while retaining previous MVPs. It
does not require the previous MVP to be `validating` or `released`.
This was checked against the engine source. `aido validate` checks the
document and configuration, while `aido status` reads the configured
MVP. A later approved `aido run` is what bootstraps the new MVP. Preserve
M3.6 and its state until the separate activation review and leave the
aggregate lifecycle unchanged.

After explicit approval, use a separate roadmap change to make `m4` the
sole approved current milestone and archive the M3.6 block intact. On
updated, clean `main`, use the installed stable AIDO runner outside this
checkout, verify its AIDO Code and engine import paths, then run
`aido validate` and unprobed `aido status`. A new `m4` should appear as
configured and not yet created before the operator starts `aido run`.
Review DEV A, distinct DEV B, mandatory SHA-bound QA and the governed Git
merge for each WorkItem in dependency order. Keep the global worker
registry and its existing local-first policy and cloud fallback.

The interruption defect found during the M3.3 real acceptance (a surviving
`ralph` kept working and committing after Ctrl+C) is fixed in
`ai-dev-orchestrator` `bd176c3`: the engine now terminates the whole worker
session and returns only once no worker process is left.

## M4 — Non-interactive mode (draft)

Status: DRAFT

### ID

m4

### Objective

Accept one request per `aido -p` invocation to read project status or
start or resume governed project execution. Scope is AIDO Code, with
indicative target v0.2.4 and engine v0.2.2. Use the existing CLI, intent
router and public engine client. Apply REUSE FIRST, KISS and YAGNI.

### Acceptance criteria

- `aido -p "status"`, `aido -p "continue le projet"` and `echo "status" | aido -p` work with the modern `aido.yaml` in the current directory. `aido-code` and `python -m aido_code` exercise the same entry point.
- Status uses the existing unprobed, read-only snapshot, including `NOT_INITIALIZED` when appropriate. Run uses the existing approval gate and engine run/recovery path. The engine retains worker selection, independent corrective review, QA and Git decisions.
- stdout carries the status report or final text run summary with WorkItem states. stderr carries flushed public progress events, diagnostics, usage errors and the interruption notice. There are no prompts or terminal controls. Automation uses the exit code.
- For `-p`, exit `0` means a status report was produced or the nonempty run snapshot contains only `completed` WorkItems, including an already-completed run. Exit `1` means a project, configuration, I/O or engine error, a `failed` or `blocked` WorkItem, or an incomplete result other than the waiting case below. Exit `2` means invalid usage or an unknown, ambiguous or unsupported request. Exit `3` means a run has a `waiting` WorkItem, with no `failed` or `blocked` WorkItem and no unknown status. Exit `130` means interruption by Ctrl+C, after engine cleanup when a run was active.
- Decide the run outcome from final WorkItem states. Fail closed for empty results or unknown statuses and report other incomplete results, including cycle exhaustion without completion or waiting, with code `1`. A final `failed` or `blocked` state takes precedence over `waiting`. Neither `all_terminal` nor an exception-free call establishes success. Historical wait records, intermediate diagnostics and aggregate MVP `running` are not final WorkItem states.
- Keep the existing command behavior, including the exit semantics and live stdout of explicit `aido run`. The status report itself may include failed or waiting WorkItems and still return `0` when the read succeeds. Offline QA and CI pass on Python 3.10 and 3.12.

### WorkItems

#### WI-M4-01 — CLI entry point and stdin

Dependencies: none
Capabilities: development

Acceptance criteria:

- Recognize `-p` in the existing CLI before session, REPL or Textual setup. Accept either exactly one request argument or, when the argument is omitted, one request read to EOF from non-TTY stdin. An explicit argument takes precedence and stdin is left unread. Preserve the existing global `--lang` handling.
- Trim surrounding whitespace and accept one nonempty line. Empty, whitespace-only, multiline, extra arguments, unsupported flags after `-p` and bare `-p` with TTY stdin are usage errors (`2`, stderr, empty stdout). A stdin read or decoding error is an I/O error (`1`, stderr, empty stdout).
- Test argument/piped input, surrounding whitespace, argument precedence, empty/EOF and multiline input, TTY refusal, extra arguments and read errors. Check that this entry point never starts Textual or creates, loads or updates a session.

#### WI-M4-02 — Intent dispatch and governed execution

Dependencies: WI-M4-01
Capabilities: development

Acceptance criteria:

- Reuse `interpret()` for `STATUS` and `RUN`. Cover documented English requests such as `status` and `continue the project` and explicitly recognize French `continue le projet`, `lancer le projet`, `continuer le projet`, `démarrer le projet`, `reprendre le projet` and `l'état du projet` in the same deterministic router. Cover case, surrounding whitespace and terminal punctuation, including a typographic apostrophe in the French status phrase.
- Treat negations, mixed intents and unrecognized requests as unsupported. Keep `workers` and `why_waiting` in the interactive interface. Test that rejected requests and a run against a `DRAFT` plan do not reach engine execution or any provider.
- Reuse `build_status_output()` with probing disabled and keep the existing modern run path shared with explicit `aido run`. Use `load_project_command_context()`, the typed engine plan, `EngineClient.from_config()` and `run_interruptibly()`. Retain typed `RunResult` through the CLI decision. Interactive REPL/session behavior remains compatible.
- The v0.2.2 worker and QA launchers inherit fd 0. For `-p` runs, isolate it in the CLI once the request is read so child processes see EOF instead of the caller's TTY or pipe. Use the existing `/dev/null` approach and restore the descriptor on return, error and interruption. Verify EOF and restoration in an offline test.
- Test status parity with `aido status` and correct project selection from the current directory. Test that a run dispatches once through the typed engine client, including a second invocation that uses the same engine recovery path. No direct Ralph/provider calls, second orchestrator or new natural-language engine.

#### WI-M4-03 — Output, exit codes and regression coverage

Dependencies: WI-M4-02
Capabilities: development

Acceptance criteria:

- Reuse sanitized live event rendering, final summary and typed diagnostics. Route them to the specified streams. Report the reason for nonzero results on stderr, without tracebacks for expected errors or success wording for an incomplete run. On Ctrl+C, preserve already emitted progress and omit the final run summary.
- Test `0`, `1`, `2`, `3` and `130`, including all-completed with zero new work, `NOT_INITIALIZED`, a successful status read showing `waiting`, real `WAITING` from a scripted offline fixture, mixed waiting/failed and waiting/blocked, terminal failure, QA/Git refusal, cycle exhaustion, `recovery_required`, empty or unknown result, and interruption during stdin read or run.
- Use disposable Git repositories, isolated state and existing provider and subprocess doubles. Exercise DEV A, a different DEV B, required QA bound to the reviewed SHA and the governed merge. A failing QA or Git gate must prevent delivery and a success exit. Verify interrupt/recovery through the same engine entry point.
- Update `docs/CLI_SPEC.md` and run the full offline suite. Keep regression coverage for `init`, `validate`, `status [--probe]`, `run`, `version`/`v`, `resume`, `--continue`/`-c`, the default REPL/Textual path and existing aliases. Use the existing Python 3.10 and 3.12 CI matrix with the released v0.2.2 engine.

### QA

#### QA-M4-01 — Full offline frontend suite

Kind: unit_test
Required: true
Timeout: 600
Argv: [".venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

### Out of scope

- Engine, SQLite and MVP lifecycle changes, Qwen registry or service changes, parallel execution, and direct calls to Ralph or providers.
- M5 JSON/stream-json, M6 Doctor, P11 roadmap automation, UI redesign, new frameworks or dependencies, and release publication in the preparation step.

## Current milestone

Status: APPROVED

### ID

m3.6

### Objective

Implement the approved M3.6 global opt-in Qwen configuration after engine P2 compatibility is validated. Preserve the public engine boundary, cloud fallback, independent corrective review, offline QA and governed merge. Work only in this checkout. Do not modify installed environments or services, publish releases, push, or launch nested AIDO runs. Manual live acceptance and release publication are operator steps; never claim them without evidence.

### Acceptance criteria

- Two explicitly enabled local Qwen workers take priority only with global opt-in, using the engine selection policy.
- Existing cloud behavior and the full offline suite remain passing.
- Release requires real BMAX two-session Qwen acceptance and green CI.

### WorkItems

#### WI-M3.6-01 — Global Qwen workers and opt-in local-first wiring

Dependencies: none
Capabilities: development

Acceptance criteria:

- Use the existing schema and loading path; add/document two distinct Ollama worker identities with priority over cloud only in explicit BMAX configuration; no globally enabled Ollama for users who did not opt in.
- Reuse the engine's local-first selection policy once delivered; do not rebuild `WorkerSelector`, `QuotaManager`, or model detection inside the frontend.
- Offline tests cover global registry, two identities, precedence vs cloud, fallback, validation and unchanged behavior for non-opt-in installations.

#### WI-M3.6-02 — Integrate and verify BMAX release

Dependencies: WI-M3.6-01
Capabilities: development

Acceptance criteria:

- Verify compatible engine release is installed in a separate stable venv; never edit the active venv in place or import the editable checkout being modified as controller.
- Test existing frontend commands `/workers`, `/status`, `/status --probe`, `aido version`/`aido v`, plus full offline CI.
- Run real BMAX AIDO→Ralph→Qwen DEV A→different Qwen DEV B→deterministic QA PASS→governed Git merge on a disposable Git project. Verify BMAX/Ollama is the actual inference source; no false success.
- Publish only with passing tests, governed acceptance and documented rollback. Indicative target `v0.2.3` after engine v0.2.2 (confirm actual tags); GitHub wheel, sdist, checksums; no PyPI.

### QA

#### QA-M3.6-01 — Full offline frontend suite

Kind: unit_test
Required: true
Timeout: 600
Argv: [".venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider"]

### Out of scope

- UI redesign, project worker selection, service changes, PyPI.
