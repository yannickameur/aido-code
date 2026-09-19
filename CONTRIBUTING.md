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
4. Nothing lands on `main` here except through that governed flow.

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
  work (like the one that produced this file); only as part of this
  project's own real, later governed development.

## Questions about the engine itself

This repository only consumes `orchestrator.engine.OrchestratorEngine`
(see `docs/ENGINE_CONTRACT.md`). Anything about the engine's own
internals, invariants, or roadmap belongs in `ai-dev-orchestrator`'s own
`ROADMAP.md`/`CONTRIBUTING.md`, not here.
