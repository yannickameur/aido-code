# Contributing

## Core rule

Functional AIDO Code code is produced through AI Dev Orchestrator's own
governed WorkItem Flow, never by a human or an assistant editing files
directly in this repository. This mirrors how `ai-dev-orchestrator`
built its own first external reference project, Morpion Web 3D: DEV A
implements, an independent DEV B reviews and corrects, deterministic QA
decides PASS/FAIL, and a governed Git merge lands the result — never a
single developer's own claim that "it works."

1. `ai-dev-orchestrator` governs this repository via `aido.yaml` (start
   from `aido.example.yaml`, copied to a local, untracked `aido.yaml`;
   see "Local configuration" below).
2. `aido validate` checks the config before anything runs.
3. `aido run` drives the governed WorkItem Flow: DEV A, DEV B
   corrective review, deterministic QA, then a governed merge/tag —
   exactly as documented in `ai-dev-orchestrator`'s own `ROADMAP.md`,
   section "WorkItem Flow".
4. **No functional AIDO Code code** lands on `main` except through that
   governed flow — absolute.

## What maintainers may edit directly

Documentation, roadmap, governance, acceptance specs, and WorkItem
preparation — this repository's own history already shows the
maintainer committing all of these directly (e.g. this repository's
initial commit, and every milestone-preparation commit since). Those
changes are legitimate as long as they never implement functionality
indirectly: describing, specifying, or preparing WorkItems for the
governed flow to build is not the same as building it.

## Local development

**Normal installation** (using AIDO Code, or contributing docs/specs
only): `pip install -e .` from this repository pulls in
`ai-dev-orchestrator` as an ordinary dependency — no sibling checkout,
no manual worker registry; see `README.md`, "Quick start".

**Dual-repo engine development** (changing `ai-dev-orchestrator` itself
and testing those changes against AIDO Code before a new engine version
is published):

1. Create/use a Python environment for this work (e.g. a venv).
2. Install the engine from a sibling checkout in editable mode:
   ```bash
   python -m pip install -e ../ai-dev-orchestrator
   ```
   (adjust the path if your checkout layout differs; this makes
   `orchestrator.engine` importable against your local engine changes —
   the distribution name (`ai-dev-orchestrator`) and the importable
   package name (`orchestrator`) differ on purpose, see that project's
   own `pyproject.toml`).
3. Install this project too: `python -m pip install -e .`.
4. To run AIDO Code's own governed WorkItem Flow (the "Core rule"
   above) locally, copy `aido.example.yaml` to `aido.yaml` (already in
   `.gitignore`; never commit a real `aido.yaml`, since it may
   reference machine-specific paths):
   ```bash
   cp aido.example.yaml aido.yaml
   ```
   It references the sibling checkout's own `config/workers.yaml`
   (`../ai-dev-orchestrator/config/workers.yaml`), never a copy of the
   worker pool. Edit that one path if your checkout layout differs.

**Never add a machine-specific path dependency to a tracked
`pyproject.toml`** — no `file:///home/...`, no `../ai-dev-orchestrator`,
no local path of any kind committed as a dependency. The sibling
checkout above is a development convenience only; see `ROADMAP.md`,
"M8", for the packaging/distribution contract already proven for the
real, publishable path.

## Never commit

- API keys, tokens, or credentials — not in `aido.yaml`,
  `aido.example.yaml`, or anywhere else. Authentication stays entirely
  with the provider CLI/environment, exactly like `ai-dev-orchestrator`
  itself.
- Machine-specific configuration, including a real `aido.yaml` (see
  above) or a path dependency in `pyproject.toml`.

## Tests

This project's own `pytest -q` suite must always stay offline: it must
never call a real Claude/Codex/Vibe/DeepSeek/Kimi/Ralph provider, and
no real provider consumption may ever come from this project's own QA
either; see `MVP_SPEC.yaml`. This does not restrict real governed
development itself — once WorkItems are scheduled, `aido run` driving
DEV A, DEV B, QA, and governed merge is expected and required to use
real workers/providers.

## Questions about the engine itself

This repository only consumes `orchestrator.engine.OrchestratorEngine`
(see `docs/ENGINE_CONTRACT.md`). Anything about the engine's own
internals, invariants, or roadmap belongs in `ai-dev-orchestrator`'s
own `ROADMAP.md`/`CONTRIBUTING.md`, not here.
