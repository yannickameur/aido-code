# Contributing

This project's functional code is written by **AI Dev Orchestrator
itself**, not by a human or an assistant editing files directly in this
repository. This mirrors how `ai-dev-orchestrator` built its own first
external reference project, Morpion Web 3D: DEV A implements, an
independent DEV B reviews and corrects, deterministic QA decides
PASS/FAIL, and a governed Git merge lands the result, never a single
developer's own claim that "it works."

## How development actually happens

1. `ai-dev-orchestrator` governs this repository via `aido.yaml` (start
   from `aido.example.yaml`, copied to a local, untracked `aido.yaml`;
   see below).
2. `aido validate` (from the `ai-dev-orchestrator` checkout) checks the
   config before anything runs.
3. `aido run` drives the governed WorkItem Flow: DEV A, then DEV B
   corrective review, then deterministic QA, then a governed merge/tag,
   exactly as documented in `ai-dev-orchestrator`'s own `ROADMAP.md`,
   section "WorkItem Flow".
4. **No functional AIDO Code code** lands on `main` except through that
   governed flow — that rule is absolute. It does not extend to
   documentation: this project's own history already shows the
   maintainer committing documentation, governance, roadmap, acceptance
   specs, and WorkItem preparation directly (e.g. this repository's own
   initial commit, and every M1/M2 preparation commit since). Those
   changes are legitimate as long as they never implement functionality
   indirectly — describing, specifying, or preparing WorkItems for the
   governed flow to build is not the same as building it.

## Local configuration

`aido.example.yaml` is the tracked, portable template. Copy it to
`aido.yaml` (already in `.gitignore`; never commit a real `aido.yaml`,
since it may reference machine-specific paths):

```bash
cp aido.example.yaml aido.yaml
```

It references the sibling `ai-dev-orchestrator` checkout's own
`config/workers.yaml` (`../ai-dev-orchestrator/config/workers.yaml`),
never a copy of the worker pool. If your checkout layout differs, edit
that one path.

## Never in this repository

- No functional CLI code written directly by a human or an assistant
  outside the governed WorkItem Flow described above; see
  `ai-dev-orchestrator`'s ROADMAP.md P13 and this project's own
  `ROADMAP.md` for why.
- No API keys, tokens, or credentials in `aido.yaml`,
  `aido.example.yaml`, or anywhere else in this repository.
  Authentication stays entirely with the provider CLI/environment,
  exactly like `ai-dev-orchestrator` itself.
- No `aido run` against this repository as part of documentation/spec
  work (like the one that produced this file). This does not restrict
  real governed development itself: once WorkItems are actually
  scheduled, AI Dev Orchestrator's own `aido run` driving DEV A, DEV B,
  QA, and governed merge is expected and required to use real
  workers/providers. What must always stay offline is this project's own
  pytest suite: it must never call a real Claude/Codex/Vibe/DeepSeek/
  Kimi/Ralph provider, and no real provider consumption may ever come
  from this project's own QA (`pytest -q`) either; see `MVP_SPEC.yaml`.

## Local development bootstrap (engine dependency)

This repository is a separate project from `ai-dev-orchestrator` but
depends directly on `orchestrator.engine.OrchestratorEngine` at runtime
(see `docs/ENGINE_CONTRACT.md`). For the current development phase, the
engine is a sibling Git checkout, not yet a published package:

1. Create/use a Python environment suited to this work (e.g. a venv).
2. Install the engine from the sibling checkout in editable mode:
   ```bash
   python -m pip install -e ../ai-dev-orchestrator
   ```
   (adjust the path if your checkout layout differs; this installs the
   `orchestrator` distribution and makes `orchestrator.engine` importable).
3. Once WI-01 creates this project's own package, install it too:
   ```bash
   python -m pip install -e .
   ```

**Never add a machine-specific path dependency to a tracked
`pyproject.toml`** — no `file:///home/...`, no `../ai-dev-orchestrator`,
no local path of any kind committed as a dependency. The sibling checkout
above is only today's development convention, not something the shipped
product may depend on. See `ROADMAP.md`, "M8", for the packaging/
distribution contract this must resolve into before this project claims
the `aido` command name.

## Questions about the engine itself

This repository only consumes `orchestrator.engine.OrchestratorEngine`
(see `docs/ENGINE_CONTRACT.md`). Anything about the engine's own
internals, invariants, or roadmap belongs in `ai-dev-orchestrator`'s own
`ROADMAP.md`/`CONTRIBUTING.md`, not here.
