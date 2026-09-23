# Contributors

This project's functional code is written by AI Dev Orchestrator's
governed WorkItem Flow, never directly by a human or an assistant — see
`CONTRIBUTING.md`. This file credits who/what actually produced M1
(WI-01 through WI-07), M1.1 (WI-M1.1-01 through WI-M1.1-04), and M1.2
(WI-M1.2-01/02), factually, from the real runs' own persisted execution
records — nothing here is inferred or aspirational. One exception:
WI-M1.1-01's implementation commit landed under the maintainer's own
Git identity due to a real engine defect, not maintainer authorship;
see `docs/M1_1_REFERENCE_RUN.md`.

## Yannick Ameur

- Project owner / maintainer.
- Authored this repository's own documentation/governance commits
  (roadmap, architecture, acceptance specs, contributor docs) and
  authorized/triggered every real governed run.

## Alice

- AI Dev Orchestrator worker (`anthropic`/`claude_code`).
- DEV A for every WorkItem in M1 (WI-01 through WI-07), M1.1
  (WI-M1.1-01 through WI-M1.1-04), and M1.2 (WI-M1.2-01/02): first
  implementation of each WorkItem's acceptance criteria.
- Also performed the DEV FIX execution for WI-02 (M1), which changed
  the execution environment without producing a Git commit; see
  `docs/M1_REFERENCE_RUN.md`.
- WI-M1.1-01's actual implementation commit is Alice's real, governed
  work (confirmed by `executions.sqlite3`), but landed under the
  maintainer's ambient Git identity due to a real engine defect in
  identity inheritance for this specific commit; see
  `docs/M1_1_REFERENCE_RUN.md`.

## Victor

- AI Dev Orchestrator worker (`openai`/`codex`).
- DEV B corrective review for every WorkItem in M1, M1.1, and M1.2:
  independent review/correction of Alice's implementation before
  deterministic QA.

## Not contributors yet

`bob`/`oscar` (the `anthropic`/`openai` fallback pool), `milo`/`juno`
(`mistral`/`vibe`, enabled), and `dana`/`kai` (`deepseek`/`kimi`,
configured but **disabled** — no API key, no real execution evidence
yet) are configured workers (see `ai-dev-orchestrator`'s
`config/workers.yaml`) but have not produced a real, governed commit in
this project — `WorkerSelector` has not selected them. A display-name
or configuration change alone never makes a worker a contributor here;
this list is updated only when a worker actually produces one.
