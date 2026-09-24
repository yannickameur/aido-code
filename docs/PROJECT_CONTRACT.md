# Project contract (M1.4) — manifest, ROADMAP.md, resources, workers

Full, authoritative grammar/schema for M1.4 ("Autonomous AIDO project
contract"). `ROADMAP.md`'s own M1.4 section stays short and points here,
the same way M2's section points to `docs/SESSION_CONTRACT.md`. This
document does not itself execute anything; the governed WorkItems that
implement it are `ROADMAP.md`'s WI-M1.4-01 through WI-M1.4-08, built by
AI Dev Orchestrator's real WorkItem Flow (`CONTRIBUTING.md`), never
written directly into `src/aido_code/*` by a human or an assistant.

## 1. Why this exists

Before M1.4, a user project's `aido.yaml` was a copy of
`ai-dev-orchestrator`'s own schema v1 (`docs/PROJECT_CONFIG.md` in that
project): `project`/`workers.registry`/`execution`/`git`/`mvp`/
`work_items`/`qa`. A user had to know the engine's own worker/provider
model, hand-write WorkItems in YAML, and reference a `workers.yaml` file
— exactly the coupling `ai-dev-orchestrator`'s own P13.5 (see that
project's `ROADMAP.md` §13) closed on the engine side by making
`workers:` optional and adding `OrchestratorEngine`/`ProjectRuntime`
injection seams (`worker_registry=`).

M1.4 is AIDO Code's own side of that same boundary: a user project no
longer knows any worker, provider, model, or `workers.yaml` path at all.
It knows exactly four things — **which project, which roadmap, which
resources, which first instruction** — and AIDO (this product) resolves
everything else: its own global worker pool, and a typed engine plan
built from parsing the project's own `ROADMAP.md`.

```
AIDO
├── CLI / UX
├── AIDO global configuration (workers)      -- §4 below
├── aido.yaml parser (manifest)              -- §2 below
├── ROADMAP.md parser (deterministic)        -- §3 below
├── resources/ resolution + initial_prompt   -- §5 below
│
└── OrchestratorEngine(plan, worker_registry=...)   -- §6 below
       ↓
   ai-dev-orchestrator
```

A user project's own `aido.yaml`/`ROADMAP.md`/`resources/` never
reference a worker, a provider, a model, or a path into
`ai-dev-orchestrator`.

## 2. The manifest (`aido.yaml`)

The launch manifest only — never the executable contract itself (that is
`ROADMAP.md`, §3).

```yaml
schema_version: 1

project:
  id: myproject
  name: MyProject
  workspace: "."

roadmap: "./ROADMAP.md"

resources: "./resources"

initial_prompt: >
  Read ROADMAP.md and the project resources referenced by it before doing
  any work. Execute only the currently approved milestone. Respect its
  scope, dependencies, acceptance criteria and explicit out-of-scope
  decisions. Apply REUSE FIRST, KISS and YAGNI.
```

**Allowed top-level keys, exhaustively**: `schema_version`, `project`
(`id`/`name`/`workspace`), `roadmap`, `resources`, `initial_prompt`. Any
other top-level key — `workers`, `providers`, `models`, `mvp`,
`work_items`, `qa`, `execution`, `git`, or anything else — is rejected,
fail-closed, before a single field is trusted (mirrors
`ai-dev-orchestrator`'s own `project_config._reject_unknown_keys`
pattern; WI-M1.4-02 reproduces the same fail-closed shape, never a
second, looser parser).

- `schema_version` must be `1`.
- `project.id`/`project.name` are required, non-empty strings.
  `project.id` is validated by the same conservative character pattern
  `ai-dev-orchestrator`'s own `project_config._PROJECT_ID_PATTERN` uses
  (letters/digits/`.`/`_`/`-`, starting with a letter or digit, never
  `..` or a path separator) — it feeds a default `state_dir`, so it can
  never escape it.
- `project.workspace` is required, resolved relative to the directory
  containing `aido.yaml` (never the caller's cwd), `~` expanded, and
  must be an existing directory. Whether it must already be a Git work
  tree is checked later, once, right before the typed engine plan is
  handed to the engine (§6) — not by this parser itself.
- `roadmap` is required: a path (same resolution rule) to the project's
  `ROADMAP.md`. It must resolve to a location **inside `workspace`** —
  no `..` traversal, no symlink escaping `workspace` (mirrors the
  path-safety rule M2's own `docs/SESSION_CONTRACT.md` already documents
  for session file paths, DR-4 — same principle, new location).
- `resources` is required: a path (same resolution rule) to the
  project's resources directory, also confined inside `workspace`, same
  rule. It must exist and be a directory.
- `initial_prompt` is required, a non-empty string.
- **No secrets**: the same substring guard-rail
  `ai-dev-orchestrator`'s `project_config`/`worker_registry` modules
  already use (`api_key`, `token`, `secret`, `password`, `credential`,
  ...) applies here too — never a general secret scanner, just the same
  cheap guard-rail, reproduced, not imported (this manifest is parsed
  entirely inside `aido_code`, before any `ProjectConfig` exists).

`aido.yaml` never contains `execution.permission_mode` or
`git.base_branch` (dropped from the manifest, not just made optional —
see §6 for where these now come from). A manifest with either key is
rejected as an unknown field, exactly like `workers`/`mvp`/etc.

## 3. `ROADMAP.md` — the executable source of truth

One deterministic Markdown grammar. **No LLM parses this file. No
heuristic/free-form understanding. Fail closed on any structural
violation** — a malformed `ROADMAP.md` is a `validate` error, never a
best-effort partial read.

```markdown
# ROADMAP — My Project

## Vision

Free text. Not parsed structurally.

## Sources

- resources/specification.md
- resources/decisions.md

## Current milestone

Status: APPROVED

### ID

m1

### Objective

Free text — this milestone's own objective.

### Acceptance criteria

- The feature works as described.
- ...

### WorkItems

#### WI-01 — First task

Dependencies: none
Capabilities: development

Acceptance criteria:

- ...

#### WI-02 — Second task

Dependencies: WI-01
Capabilities: development

Acceptance criteria:

- ...

### QA

#### QA-01 — Tests

Kind: unit_test
Required: true
Timeout: 300
Argv: ["pytest", "-q"]

### Out of scope

- Anything explicitly not built by this milestone.

## Future milestones

Free text. Not parsed structurally.
```

### 3.1 Structural rules (fail closed)

- The document is scanned for `##` (h2) headings. **Exactly one** must
  be titled `Current milestone` (byte-exact, case-sensitive) — zero or
  more than one is a fail-closed parse error. `Vision`/`Sources`/
  `Future milestones` are optional, never structurally validated beyond
  §3.2's `Sources` rule; any other `##` heading is allowed and ignored
  (a project may add its own free-form sections) as long as it is not a
  second `Current milestone`.
- Inside `Current milestone`, the first non-blank line must be exactly
  `Status: APPROVED` or `Status: DRAFT` (byte-exact value, case-
  sensitive) — any other value (`Status: approved`, `Status: WIP`, a
  missing `Status:` line, ...) is a fail-closed parse error, never
  coerced/guessed.
- `### ID`: exactly one, required, non-empty. Validated with the same
  character-safety pattern as `project.id` (§2) — it becomes
  `MVPConfig.id` verbatim (§6), and must never contain a path separator.
- `### Objective`: exactly one, required, non-empty free text (may span
  multiple lines/paragraphs).
- `### Acceptance criteria` (milestone-level): optional section; if
  present, a list of `- ` bullets, each non-empty.
- `### WorkItems`: required, exactly one. Contains one or more `####`
  sub-headings, each of the exact shape `#### <id> — <title>` (em dash
  `—`, one space on each side — byte-exact separator, never a plain
  hyphen, never guessed). `<id>` must be non-empty, unique across the
  whole `WorkItems` section, and pass the same character-safety pattern
  as `project.id` (no requirement to start with `WI-`, but every
  existing milestone in this project's own history uses `WI-<slug>`
  IDs, e.g. `WI-M1.4-01`, and a future project should keep doing the
  same for readability). `<title>` is free text.
  - Each WorkItem body has two required labeled lines, in this exact
    order: `Dependencies: none` or a comma-separated list of other
    WorkItem ids declared in this same `WorkItems` section (a dependency
    on an id from a different milestone, or a nonexistent id, is a
    fail-closed error); `Capabilities:` a comma-separated list of
    non-empty capability names (free-form strings, mirrors
    `ai-dev-orchestrator`'s own `required_capabilities`, e.g.
    `development`).
  - Followed by a blank line, then `Acceptance criteria:` and at least
    one `- ` bullet (a WorkItem with zero acceptance criteria is a
    fail-closed error — this is the sole normative contract a real DEV
    A/DEV B/QA cycle executes against; it can never be empty).
  - **Dependency cycle detection**: the exact same fail-closed DFS
    (white/gray/black) algorithm `ai-dev-orchestrator`'s own
    `orchestrator.project_config._validate_work_items` already
    implements and has already been tested against — WI-M1.4-03
    reproduces that same algorithm shape here (this parser cannot import
    that private function directly; it mirrors the algorithm, never
    invents a different one).
- `### QA`: optional at parse time (a `DRAFT` milestone may have none
  yet). If present, one or more `####` sub-headings, same `<id> —
  <title>` shape and uniqueness/character rules as WorkItems (a QA id
  and a WorkItem id may share the same namespace or not — this contract
  does not require them to be disjoint, since they are never cross-
  referenced). Each QA body has four required labeled lines: `Kind:` one
  of `ai-dev-orchestrator`'s own `orchestrator.validation.ValidationKind`
  values (currently `unit_test`; unknown value fails closed);
  `Required: true` or `Required: false`; `Timeout: <number>` (seconds,
  positive); `Argv: [...]` a JSON array of non-empty strings (parsed
  with the stdlib `json` module, never a shell string, never a Python
  literal eval — malformed JSON, a non-array, or a non-string element
  all fail closed).
- `### Out of scope`: optional, a list of `- ` bullets. Purely
  descriptive/documentation — never parsed into acceptance criteria,
  never fed to the engine plan (§6). Still structurally validated if
  present (must be a well-formed bullet list, never silently ignored if
  malformed).
- `## Sources`: optional, top-level (not nested under `Current
  milestone`), a list of `- ` bullets, each a workspace-relative path.
  Confinement/existence rules: §5.

### 3.2 The APPROVED/DRAFT gate

- `validate` (`aido-code validate`) succeeds for **both** `DRAFT` and
  `APPROVED`, as long as the document is structurally valid per §3.1 —
  reports which one, and whether the milestone is executable.
- `run` (`aido-code run`) additionally requires `Status: APPROVED`. A
  `DRAFT` milestone is refused cleanly, before any provider/engine
  construction, non-zero exit, never a traceback (see §7).

## 4. AIDO global worker configuration

Workers belong to AIDO, never to a project. Canonical location:

```
$XDG_CONFIG_HOME/aido/workers.yaml
```

Fallback (when `XDG_CONFIG_HOME` is unset):

```
~/.config/aido/workers.yaml
```

Resolution, in order:

1. If that file exists, load it with `ai-dev-orchestrator`'s own
   `orchestrator.worker_registry.WorkerRegistry.load(path)` — the exact
   same `WorkerRegistry`-shaped YAML this project already knows (no new
   parser). A malformed override fails closed with the same
   `WorkerRegistryError` taxonomy that module already raises.
2. Otherwise, use AIDO Code's own **packaged default workers** —
   bundled as a real file inside this package's own distribution (e.g.
   `aido_code/resources/default_workers.yaml`, resolved through
   `importlib.resources`/`importlib.resources.as_file` for a real
   filesystem path even from a zipped wheel, then loaded through the
   same `WorkerRegistry.load(path)`). This is a **self-contained copy**,
   never a read of `ai-dev-orchestrator`'s own packaged
   `orchestrator/resources/default_workers.yaml` — that file is
   documented (P13.5, that project's own `resources/__init__.py`) as
   legacy/CLI-only, never the modern product's worker source of truth.
   AIDO Code owns its own defaults.

**No file is ever auto-materialized** just to make this work — unlike
`ai-dev-orchestrator`'s own legacy `aido init` (which writes a starter
`~/.config/ai-dev-orchestrator/workers.yaml` on first use), AIDO Code
uses its packaged defaults directly, in memory, when no override exists.
A user who wants to customize workers creates
`~/.config/aido/workers.yaml` (or sets `XDG_CONFIG_HOME`) themselves; a
fresh install works immediately either way.

**Never referenced by the new product path**: a project's own
`config/workers.yaml`, `../ai-dev-orchestrator/config/workers.yaml`, or
`~/.config/ai-dev-orchestrator/workers.yaml`. Those remain
`ai-dev-orchestrator`'s own legacy CLI concern (P13.5), never looked up
by `aido-code`'s modern command path. Credentials stay exactly where
they already are — provider CLIs/environment, never this file.

## 5. Resources and `initial_prompt`

- `resources` (from the manifest, §2) is resolved once, confined inside
  `workspace`; a symlink at that path, or anywhere along a resolved
  `## Sources` entry, that would escape `workspace` is refused, fail
  closed — never silently followed.
- `## Sources` (from `ROADMAP.md`, §3.1) is the **only** mechanism that
  marks a file as an actually-relevant resource. AIDO never assumes
  every file under `resources/` is normative just because it exists
  there — an unreferenced file under `resources/` is inert. Each `##
  Sources` entry is resolved relative to `workspace` (the same base as
  `resources` itself) and must exist; a missing declared source is a
  fail-closed `validate`/`run` error, never silently skipped.
- AIDO never writes to a resource file. Resources are read-only inputs
  to the plan; DEV A/DEV B may of course read/reference them as part of
  real WorkItem execution (via the resolved `resources`
  path in the workspace), but the manifest/roadmap/resources loading
  path itself never mutates them.
- `initial_prompt` becomes part of the engine plan's MVP objective (§6),
  never duplicated into every WorkItem's own acceptance criteria. The
  combination is a fixed, deterministic template — never re-derived or
  reworded per WorkItem — with clear provenance (a human reading
  `aido-code status`/the resulting `ProjectSnapshot`/`RunResult` can
  tell which part came from `initial_prompt` vs. the current milestone's
  own `### Objective`):

  ```
  <initial_prompt, verbatim>

  --- Current milestone objective (ROADMAP.md, <milestone id>) ---
  <milestone Objective, verbatim>

  --- Declared sources (ROADMAP.md, ## Sources) ---
  <one resolved, workspace-relative path per line, or "(none)">
  ```

  This exact three-section, `---`-delimited template is the whole
  transformation — no second orchestration, no LLM call, no rewriting
  of either input string.

## 6. Building the typed engine plan

Reuses `ai-dev-orchestrator`'s own `orchestrator.project_config.
ProjectConfig` **plain Python constructor** directly (never `.load()` —
there is no more `ProjectConfig`-shaped YAML file to read; never a
second, parallel "engine plan" type — REUSE FIRST, per that project's
own P13.5, `ROADMAP.md` §13, which built exactly this seam for this
purpose):

| `ProjectConfig` field | Source |
|---|---|
| `project` (`ProjectIdentity`) | `id`/`name`/`workspace` from the manifest (§2); `state_dir` computed with the **same formula** `ai-dev-orchestrator`'s own `project_config._default_state_dir(project_id)` uses (`~/.local/state/ai-dev-orchestrator/projects/<project.id>/`) — same convention, same location, so a project already governed under M1-M1.3 is never orphaned or duplicated under M1.4 (this must be verified by an offline test with a fixed, fake `HOME`) |
| `workers_registry_path` | always `None` — never set, never derived from anything in the manifest |
| `execution` (`ExecutionConfig`) | `permission_mode=ExecutionPermissionMode.STANDARD` — an explicit, documented default (the manifest carries no `execution:` section at all, §2); `unrestricted` is out of scope for M1.4 (no per-project override mechanism yet — a real, separate, explicitly-voted future increment if ever needed, never invented here) |
| `git` (`GitConfig`) | `base_branch="main"` — the same default `ProjectConfig.load()` already uses when a legacy `aido.yaml`'s own `git:` section is omitted |
| `mvp` (`MVPConfig`) | `id=<ROADMAP.md's Current milestone ### ID, verbatim>`; `objective=<the combined template from §5>`; `acceptance_criteria=<Current milestone's own ### Acceptance criteria bullets, verbatim, never merged with WorkItem-level criteria>` |
| `work_items` (`tuple[WorkItemConfig, ...]`) | one `WorkItemConfig` per parsed WorkItem (§3.1), fields copied verbatim (`id`, `title`, `required_capabilities` from `Capabilities:`, `dependencies` from `Dependencies:`, `acceptance_criteria` from its own bullets) |
| `qa_commands` (`tuple[ValidationCommand, ...]`) | one `ValidationCommand` per parsed QA entry (§3.1), fields copied verbatim |
| `qa_protected_paths` | `()` — M1.4 does not yet give a project a way to declare protected test paths from `ROADMAP.md`; a real, separate future increment if a real need is established (À VOTER), never invented here |
| `source_path` | the resolved `roadmap` path (the actual normative source, more meaningful here than the manifest path itself) |

Before this plan is ever handed to the engine, `workspace` is confirmed
to be inside a real Git work tree — the same fail-closed check
`ai-dev-orchestrator`'s own `ProjectConfig.load()` already performs
(`MissingGitWorkspaceError`-equivalent) — reproduced here since this
path never calls `.load()`.

The `WorkerRegistry` built in §4 is injected directly:

```python
from orchestrator.engine import OrchestratorEngine

engine = OrchestratorEngine(config, worker_registry=registry)
# or, for the eager-validation constructor call shape:
# OrchestratorEngine.open(...) is legacy/file-path-only (P13.5) and is
# never used by this path — the plain constructor is the modern seam.
```

`WorkerSelector` remains the sole owner of *which* worker is picked —
this plan only supplies *what's available* and *what to do*; nothing in
`aido_code` re-implements selection, QA verdicts, or merge decisions
(`ARCHITECTURE.md`, unchanged).

## 7. Command behavior

- **`aido-code init . roadmaplab`** (current, pre-M8 binary name):
  scaffolds `README.md`, `ROADMAP.md` (one placeholder milestone,
  `Status: DRAFT`, structurally valid per §3.1), `aido.yaml` (§2 shape),
  `resources/` (empty, tracked via a short `resources/README.md` stub —
  Git does not track empty directories), then `git init -b main && git
  add . && git commit -m "Initialize AIDO project"` — identical
  behavior to `ai-dev-orchestrator`'s own P1.1 guided bootstrap
  (`docs/PROJECT_CONFIG.md` in that project): Git absent or any step
  failing keeps the scaffold, returns a non-zero exit status, prints the
  exact manual commands, installs nothing automatically. `aido-code
  validate` succeeds against the fresh `DRAFT` scaffold; `aido-code run`
  refuses cleanly (§3.2) until the milestone is edited to `Status:
  APPROVED`.
- **`aido-code validate`**: provider-free. Validates, in order: the
  manifest (§2); `ROADMAP.md`'s structure (§3.1); resources
  confinement/existence (§5); that the AIDO global `WorkerRegistry`
  (§4) itself resolves cleanly (still zero provider calls — loading a
  registry is pure local YAML parsing). Prints, e.g.:

  ```
  VALID
  Current milestone: DRAFT
  Not executable.
  ```

  or

  ```
  VALID
  Current milestone: APPROVED
  Executable.
  ```

- **`aido-code run`**: (1) validate as above; (2) require `Status:
  APPROVED`, refuse cleanly otherwise, before any provider/engine
  construction; (3) load the AIDO global `WorkerRegistry` (§4); (4)
  build the typed engine plan (§6); (5) inject the `WorkerRegistry`;
  (6) call `OrchestratorEngine(...).run()`. No orchestration is ever
  duplicated — this is exactly `MVPManager.run_next_work_item`'s
  existing loop, reached the same way `.run()` already reaches it today.
- **`/workers`, `/workers --probe`**: unchanged code path — because the
  engine is now always constructed with the AIDO global registry
  injected (§6), these commands already show AIDO's own workers with
  zero additional rendering logic. WI-M1.4-07 must not invent a second,
  parallel "AIDO workers" view — REUSE FIRST.
- **`/config`**: shows the manifest facts (`project.id`/`name`/
  `workspace`, resolved `roadmap`/`resources` paths, `initial_prompt`),
  the current milestone's id/status, and the same engine-derived facts
  already shown today (`enabled_worker_count`, `providers`,
  `permission_mode`, `base_branch`, `qa_command_count`) — never a raw
  file dump, never a secret (none exist in this manifest by
  construction, §2).
- **`/status`**: combines the roadmap-level facts (current milestone
  id/status) with the real, unchanged `OrchestratorEngine.status()`
  snapshot — never fabricates a WorkItem/MVP status the engine has not
  actually persisted.

## 8. What this contract does not cover (explicitly out of scope for M1.4)

- M2 sessions (`/resume`, `/new`, `--resume`/`-r`, `--continue`/`-c`) —
  entirely separate, unstarted; see `ROADMAP.md`, M2.
- `qa_protected_paths` authored from `ROADMAP.md`.
- A per-project override of `execution.permission_mode`/
  `git.base_branch`.
- Any migration of `M2_SPEC.yaml`/`aido.m2.example.yaml`'s own content
  into this grammar — real, separate work required before a future GO
  M2 (`ROADMAP.md`, M2), not started by M1.4.
- Multiple simultaneously-`APPROVED` milestones, or any notion of
  milestone sequencing beyond "exactly one `Current milestone`" — a
  project advances by editing `ROADMAP.md` to make its next milestone
  the new `Current milestone` (out of scope to automate in M1.4).
