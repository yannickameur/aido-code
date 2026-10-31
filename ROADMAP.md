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
| M3.6 — Two priority local Qwen workers (BMAX / Ollama / Ralph) | `APPROVED FOR GOVERNED IMPLEMENTATION` (2026-10-31), depends on engine P2; not yet run |
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

### M3.6 — Two priority local Qwen workers (approved, not yet executed)

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

**State gate:** the `## Current milestone` block below still describes historical M3.5, although M3.5 is DONE. Do not replace it or edit persisted SQLite merely to start M3.6. First check local AIDO state on BMAX, prepare the compatible new current milestone in the required `docs/PROJECT_CONTRACT.md` grammar, run `aido validate`, then explicitly approve/start its governed run. This roadmap preparation alone does not attest a running engine or completed QA.

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

- The engine is published as GitHub Release v0.2.1 and AIDO Code as
  v0.2.2 (wheel and sdist); AIDO Code requires `ai-dev-orchestrator>=0.2.0,<0.3`. PyPI
  publication is a separate, undecided step. Development still uses two
  sibling checkouts with `pip install -e ../ai-dev-orchestrator`.

## Next milestone to discuss

M3.5 and release v0.2.2 are DONE. M3.6 (two local Qwen priority workers) is the approved next scope, dependent on engine P2. The current milestone below remains historical M3.5 until the local BMAX runtime/persisted state is inspected and the next governed milestone can be switched without conflict; M4 remains deferred.

The interruption defect found during the M3.3 real acceptance (a surviving
`ralph` kept working and committing after Ctrl+C) is fixed in
`ai-dev-orchestrator` `bd176c3`: the engine now terminates the whole worker
session and returns only once no worker process is left.

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
