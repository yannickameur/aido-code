# M1.1 reference run

A factual record of the real, governed build of MVP 0.1.1 (M1.1) — a
small technical increment between M1 (`DONE`) and M2 (not started),
never part of M2. This document does not hide anything found during
this run, including a real engine defect it found (Git commit identity
attribution) — see "A real engine defect found by this run" below.

## What ran

Engine: `ai-dev-orchestrator` at `main`
(`175dd0d290912fb40fec4212820daa751b2813a0`, after the distribution
rename to `ai-dev-orchestrator` 0.1.2, [PR #10](https://github.com/yannickameur/ai-dev-orchestrator/pull/10)).
AIDO Code at `fa7eb935c60b9f9ec474ab2fb82742e485431f59`
(`M1_1_SPEC.yaml`/`aido.m1_1.example.yaml` prepared, no functional
code) before this run.

A human GO was given, then `aido run` was executed against a local,
untracked config copied from `aido.m1_1.example.yaml` (same
`project.id`/`state_dir` as M1/M2, `mvp.id: mvp-0.1.1`), letting AI Dev
Orchestrator govern WI-M1.1-01 through WI-M1.1-04 itself. No WorkItem
content was ever executed manually on its behalf.

## Outcome

All 4 WorkItems reached `completed` in 4 orchestrator cycles
(`cycles_run=4 all_terminal=True`):

| WorkItem | DEV A | DEV B | Final SHA |
|---|---|---|---|
| WI-M1.1-01 | Alice (anthropic) | Victor (openai) | `7ae6037` |
| WI-M1.1-02 | Alice (anthropic) | Victor (openai) | `adbf9f4` |
| WI-M1.1-03 | Alice (anthropic) | Victor (openai) | `990c37d` |
| WI-M1.1-04 | Alice (anthropic) | Victor (openai) | `9d13b2b` |

Final result: `pyproject.toml` depends on `ai-dev-orchestrator>=0.1.2`
(never the third-party `orchestrator` package),
`EngineClient.probe_workers()` delegates directly to
`OrchestratorEngine.probe_workers()`, `/status`/`/workers` gained a
shared `--probe` opt-in, and `/status` (no flags) now also renders the
full worker list — 47 offline tests passing (was 32). No manual code
correction was made by any human/assistant at any point; the governed
WorkItem Flow's own DEV A/DEV B/QA/merge cycle is the entire authorship
of the functional code.

## A real engine defect found by this run: WI-M1.1-01 commit identity

`ai-dev-orchestrator`'s `RalphExecutionEngine` injects the worker's Git
identity (`GIT_AUTHOR_NAME`/`_EMAIL`, `GIT_COMMITTER_NAME`/`_EMAIL`) into
the Ralph subprocess's own environment for every WorkItem loop (see that
project's `b0d0ca0`, "Attribute worker Git commits by display name").
For WI-M1.1-01, Ralph's own internal safety commit
(`7ae6037`, "chore: auto-commit before merge (loop primary)") correctly
carries Alice's identity — but the substantive implementation commit the
`claude_code` backend agent itself made in that same loop
(`0e9eb9676ba806a66e79689baaf16168699cc471`, "Fix engine dependency
metadata to reference ai-dev-orchestrator package" — WI-M1.1-01's actual
`pyproject.toml` change) landed under the ambient/maintainer identity
(`yannickameur <yannick.ameur@gmail.com>`) instead, 8 seconds before
`7ae6037`. Both `executions.sqlite3` rows for WI-M1.1-01 (Alice/DEV A,
Victor/DEV B) resolve `git_sha_after` to `7ae6037`, not `0e9eb96` — the
commit exists in history but is not itself tracked as an execution
record.

This is **not** a defect in this project (AIDO Code's own code and
tests are correct: the dependency change is exactly what WI-M1.1-01
required), and every later WorkItem in this same run (WI-M1.1-02
through WI-M1.1-04) shows fully correct Alice/Victor attribution — it is
an intermittent gap in identity inheritance specifically for a `git
commit` the coding agent itself invokes via its own shell tool inside
the `claude_code` backend, not for Ralph's own wrapper commit. Per
governance, this history is not rewritten to relabel `0e9eb96`'s
authorship (that would be a manual history edit); it is recorded here as
real, historical execution evidence, and left for a future
`ai-dev-orchestrator` fix, analogous to how M1's own QA-determinism gap
(`docs/M1_REFERENCE_RUN.md`) was found, documented, and fixed afterward
in a separate PR.

**The engine fix**: `ai-dev-orchestrator` was fixed (branch
`fix/worker-commit-identity`,
[PR #11](https://github.com/yannickameur/ai-dev-orchestrator/pull/11),
merged as `bd5fa858af8bf0e265ea31b5b2b04aceabaaf62a`, after this run) to
close this gap — see that project's `ROADMAP.md`, "P13.2", for the full
account. In summary: a second, independent defense
(`scoped_worker_git_identity`) now sets the governed workspace's own
LOCAL `git config` (`--local`, never `--global`/`--system`) to the
worker's identity for the duration of a real execution, so a nested
`git commit` lands on the worker's identity even without inheriting any
environment variable — exactly the failure mode this run exposed. A
deterministic, fail-closed post-execution audit
(`WorkerCommitIdentityMismatchError`) now also verifies every commit an
execution introduces before its result can ever reach QA/merge. This
project's own real WI-M1.1-01 through WI-M1.1-04 commits, made before
that fix — including `0e9eb96` — are unchanged and were not
re-validated retroactively; they remain exactly what they were: real,
governed, historical execution evidence.

## Honest status

M1.1 is functionally `DONE`: WI-M1.1-01 through WI-M1.1-04 all
`completed`, 47/47 offline tests passing, `/status`/`/workers --probe`
manually verified end to end from a clean-room `pip install` (no sibling
checkout, no editable install) — see the packaging/install verification
this same task performed. M2 (sessions/resume) remains `PLANNED`, not
started; no `aido run` against this project has happened since this run
completed.
