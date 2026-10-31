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
- This file's `## Current milestone

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
