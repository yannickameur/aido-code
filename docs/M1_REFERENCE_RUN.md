# M1 reference run

A factual record of the real, governed build of MVP 0.1 (M1) — this
project's first real development. AIDO Code is the second real reference
project built by AI Dev Orchestrator, after Morpion Web 3D, and its first
substantial self-dogfooding case: the orchestrator built its own
independent terminal frontend through the governed WorkItem Flow. This
document does not hide anything found during that run, including a real
engine defect — that defect, and its fix, are themselves part of the
value this run produced.

## Summary

- **Result**: `DONE` — all 7 WorkItems reached `completed`.
- **WorkItems**: WI-01 through WI-07.
- **Workers**: Alice (DEV A), Victor (DEV B).
- **Tests**: 32 offline tests passing.
- **Important finding**: a real engine QA-determinism gap (WI-02): two
  QA attempts at the identical head SHA silently turned a `FAIL` into a
  trusted `PASS` after an environment-only fix.
- **Current correction status**: fixed in `ai-dev-orchestrator` PR #9
  (merged after this run); this run's own commits are unchanged and
  were not re-validated retroactively.

## What ran

Engine: `ai-dev-orchestrator` at `main`
(`d8384250db55267cba4615b2d784ac494a55c7df`, P13 `DONE`). AIDO Code at
`dc633e90b77dcbd52e961ba9238e9b729cbc5b81` (documentation-only, no
functional code) before this run.

A human GO was given, then `aido run` was executed against this
project's own `aido.yaml`, letting AI Dev Orchestrator govern WI-01
through WI-07 itself — DEV A implements, DEV B reviews/corrects,
deterministic QA decides, a governed merge lands the result. No
WorkItem content was ever executed manually on its behalf.

## Outcome

All 7 WorkItems reached `completed` in 8 orchestrator cycles:

| WorkItem | DEV A | DEV B | Final SHA |
|---|---|---|---|
| WI-01 | Alice (anthropic) | Victor (openai) | `51eaf35` |
| WI-02 | Alice (anthropic) | Victor (openai), then a DEV FIX by Alice | `06c79d9` |
| WI-03 | Alice (anthropic) | Victor (openai) | `141d621` |
| WI-04 | Alice (anthropic) | Victor (openai) | `119f41d` |
| WI-05 | Alice (anthropic) | Victor (openai) | `254f242` |
| WI-06 | Alice (anthropic) | Victor (openai) | `83bef76` |
| WI-07 | Alice (anthropic) | Victor (openai) | `feb64d4` |

Final result: a Python package (`src/aido_code/`), a REPL with
`/help`/`/status`/`/workers`/`/config`/`/validate`/`/run`/`/exit`, each
backed by a real `orchestrator.engine.OrchestratorEngine` call, 32
offline tests passing, and a passing read-only smoke test
(`python -m aido_code` and the `aido-code` console script, exercising
every command except `/run`). No manual code correction was made by any
human/assistant at any point; the governed WorkItem Flow's own DEV
A/DEV B/QA/merge cycle is the entire authorship of the functional code.

## A real recovery: WI-01

An operator-side process interruption (unrelated to this project or the
engine) left WI-01 in a stale `running` state with no live execution
behind it. The engine's own designed recovery mechanism
(`RECOVERY_REQUIRED`) picked this up on the next `aido run` and
re-orchestrated WI-01 normally — no manual state edit, no special
handling. This is the engine's recovery path working exactly as
designed, not an anomaly of this project.

## A real engine defect found by this run: WI-02

WI-02's QA ran twice against the **identical** head SHA (`06c79d9…`)
with the **identical** command (`pytest -q`):

1. **Attempt 1**: `FAIL` — `ModuleNotFoundError: No module named
   'orchestrator'` (the engine dependency was not importable from
   whatever Python environment resolved `pytest` at that moment).
2. A DEV FIX execution ran (Alice) — it made **no Git change at all**
   (SHA before == SHA after).
3. **Attempt 2**: `PASS` — 9 tests passed, same SHA, same command.

Forensic analysis established the cause precisely: the DEV FIX execution
installed the missing `orchestrator` engine dependency into the ambient
user Python environment (following this project's own `CONTRIBUTING.md`
bootstrap instructions) — a real, useful action, but one invisible to
Git and, at the time, invisible to the engine's own QA evidence too. The
engine recorded a SHA and a command per QA attempt, but never the
*environment* that actually ran them, so this exact "same SHA, different
environment" case was indistinguishable from a genuinely deterministic
re-run.

This was **not** a defect in this project (AIDO Code's own code and
tests were correct throughout), and **not** a "blind retry" (the DEV FIX
action was real and causally sufficient) — it was a genuine gap in the
engine's own QA determinism guarantee.

## The engine fix

`ai-dev-orchestrator` was fixed (branch `fix/qa-environment-determinism`,
[PR #9](https://github.com/yannickameur/ai-dev-orchestrator/pull/9),
merged as `e3bd2e48bdf08512aedc65e5ca19e70e41e62272`, after this run) to
close this gap: every validation command now records
its actual resolved executable, the underlying Python interpreter
(generic — never a `pytest`-specific rule), its version, and an installed-
package fingerprint. Two QA attempts at the same head SHA whose recorded
environments genuinely differ can no longer silently turn a prior
`FAIL`/`INCONCLUSIVE` into a trusted `PASS` — the verdict becomes
`INCONCLUSIVE` (`VALIDATION_ENVIRONMENT_CHANGED`) instead. See that
project's own `docs/QA_STRATEGY.md` §8.3 and `ROADMAP.md`'s "P13.1" for
the full account.

This project's own real WI-01 through WI-07 commits, made before that
fix, are unchanged and were not re-validated retroactively — they remain
exactly what they were: real, governed, historical execution evidence.

## Honest status

AIDO Code is a second real reference project for AI Dev Orchestrator,
alongside Morpion Web 3D — with the honest caveat that its first real
run is also what proved the engine's own QA-determinism guarantee had a
real gap, now closed. M1 is functionally `DONE`. M2 (sessions/resume)
and later milestones remain `PLANNED`, not started; no `aido run`
against this project has happened since this run completed.
