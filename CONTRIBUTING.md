# Contributing

## Core rule

Functional AIDO Code code is produced through AI Dev Orchestrator's own
governed WorkItem Flow, never by a human or an assistant editing files
directly in this repository. This mirrors how `ai-dev-orchestrator`
built its own first external reference project, Morpion Web 3D: DEV A
implements, an independent DEV B reviews and corrects, deterministic QA
decides PASS/FAIL, and a governed Git merge lands the result — never a
single developer's own claim that "it works."

## Self-hosted governed development

AIDO Code must never govern the same checkout from which the running
`aido` executable is editable-imported. This protects the controller from
changes made by its own workers, including imports performed later in a run.
Use a separate stable checkout and environment, for example:

- controller: `~/projects/aido-runner/.venv/bin/aido`;
- governed target: `~/projects/aido-code`;
- during dual-repo development, the runner may import the sibling editable
  engine at `~/projects/ai-dev-orchestrator`.

Verify the actual `aido_code.__file__` and `orchestrator.__file__` with the
runner's Python before starting. Updating target source files must never
change the controller's imported checkout. Refresh the stable runner only
between runs, after the governed target commits have landed; start a fresh
Python process to load the new frontend. No hot reload.

1. From the target directory, use its local, untracked modern `aido.yaml`
   manifest and the current approved milestone in `ROADMAP.md`, following
   `docs/PROJECT_CONTRACT.md`. The global worker registry remains authoritative.
2. Run the separate stable runner's `aido validate`, then `aido status`.
3. Run that runner's `aido run` from the target directory. The existing
   engine drives DEV A, independent DEV B corrective review, deterministic
   QA, and governed Git merge/tag.
4. **No functional AIDO Code code** lands on `main` except through that
   governed flow.

For a staged bootstrap such as M3.1, an ephemeral invocation of the existing
modern loader (`load_project_command_context`), `build_engine_plan`, and
`EngineClient.from_config` may call `EngineClient.run(max_cycles=1)` from the
stable runner environment. This limits the caller to one governed engine
cycle; it changes neither worker selection nor WorkItem state semantics.
Inspect the result before refreshing the runner and continuing in a fresh
process. Never manually reopen terminal WorkItems or edit persisted state.
Never add a project-specific provider/worker selection override to force a
particular developer.

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
3. For self-hosted governed development, install AIDO Code editably from
   the separate stable runner checkout into its environment, not from the
   governed target. Keep the target's local modern `aido.yaml` manifest
   untracked and follow `docs/PROJECT_CONTRACT.md`; do not substitute the
   historical legacy engine CLI/configuration path.

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
never call a real Claude/Codex/Vibe/Gravity/Ralph provider, and
no real provider consumption may ever come from this project's own QA
either; see `MVP_SPEC.yaml`. This does not restrict real governed
development itself — once WorkItems are scheduled, the separate stable runner's
`aido run` driving DEV A, DEV B, QA, and governed merge is expected and
required to use real workers/providers.

## Questions about the engine itself

This repository only consumes `orchestrator.engine.OrchestratorEngine`
(see `docs/ENGINE_CONTRACT.md`). Anything about the engine's own
internals, invariants, or roadmap belongs in `ai-dev-orchestrator`'s
own `ROADMAP.md`/`CONTRIBUTING.md`, not here.
