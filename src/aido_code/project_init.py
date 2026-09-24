"""AIDO Code's own project bootstrap ``init`` (WI-M1.4-06, see
``docs/PROJECT_CONTRACT.md`` §7 and ``ROADMAP.md``, WI-M1.4-06).

Scaffolds a brand new AIDO project at ``<parent-path>/<project-name>``:
``.gitignore``, ``README.md``, ``ROADMAP.md`` (one placeholder milestone,
``Status: DRAFT``, structurally valid per ``aido_code.roadmap``'s own
grammar), ``aido.yaml`` (the ``aido_code.project_manifest`` shape),
``resources/`` (a short ``resources/README.md`` stub, since Git does not
track empty directories) — then ``git init -b main && git add . && git
commit -m "Initialize AIDO project"``.

Git behavior mirrors ``ai-dev-orchestrator``'s own P1.1 guided bootstrap
(that project's ``orchestrator.cli._scaffold_project``/
``_initialize_project_git``) verbatim in shape, reproduced here rather
than imported — this package's own structural test
(``tests/test_structural.py``) forbids importing ``orchestrator.cli``
internals, and this product path never depends on that legacy CLI
module. Git absent, or any Git step failing, keeps the scaffold on disk,
returns a non-zero exit status, prints the exact manual recovery
commands, and installs nothing automatically.

Target-path validation mirrors that same P1.1 contract: the target must
be absent or an empty directory (no ``--force`` escape hatch is ever
offered), ``~`` is expanded in ``parent-path``, and ``project-name`` must
be a single, safe directory-name component — never a path, never ``..``,
never a symlink.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

__all__ = ["run_init"]

# Same "one safe directory-name component" shape ai-dev-orchestrator's
# own orchestrator.cli._scaffold_project uses: the first character must
# be a letter or digit (excludes '.', '_', and any other symbol — this
# alone rules out '.', '..', and hidden/control-ish names), the
# remainder is limited to word characters/space/dot/hyphen (excludes
# '/', so a path is not even expressible), and the whole name may never
# end in '.' or a trailing space.
_PROJECT_NAME_RE = re.compile(r"[^\W_][\w .-]*")

_GITIGNORE = "/.ralph/\n.env\n.env.*\n"

_README_TEMPLATE = """# {name}

## Purpose

TODO: What problem does this project solve?

## Users

TODO: Who is this project for?

## Main constraints

TODO: Technical, functional, or operational constraints.

## Development

This project is developed through AIDO.

See:
- ROADMAP.md
- aido.yaml
"""

_RESOURCES_README = """# Resources

Files referenced by ``ROADMAP.md``'s own "## Sources" section live here.
A file placed in this directory but never referenced from "## Sources"
is inert — AIDO never treats it as normative just because it exists on
disk (see the AIDO Code repository's docs/PROJECT_CONTRACT.md, §5).
"""

_ROADMAP_TEMPLATE = """# ROADMAP — {name}

## Current milestone

Status: DRAFT

### ID

m1

### Objective

TODO: describe the objective of this milestone.

### WorkItems

#### wi-1 — TODO: describe the first WorkItem

Dependencies: none
Capabilities: development

Acceptance criteria:
- TODO: state, concretely, what "done" means for this WorkItem.
"""


def _sanitize_project_id(name: str) -> str:
    """Same slugification as ``ai-dev-orchestrator``'s own
    ``orchestrator.cli._sanitize_id`` — reproduced, not imported. Always
    yields a string that satisfies ``aido_code.project_manifest``'s own
    ``project.id`` pattern (letters/digits/hyphens only here, a strict
    subset of what that pattern allows)."""
    slug = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    return slug or "project"


def _manifest_content(*, project_id: str, project_name: str) -> str:
    """Built as real YAML data and dumped, never a hand-quoted string
    template — this is the only robust way to embed an arbitrary
    ``project_name`` safely (docs/PROJECT_CONTRACT.md §2 manifest
    shape, WI-M1.4-02)."""
    document = {
        "schema_version": 1,
        "project": {"id": project_id, "name": project_name, "workspace": "."},
        "roadmap": "./ROADMAP.md",
        "resources": "./resources",
        "initial_prompt": (
            "Read ROADMAP.md and the project resources referenced by it before doing "
            "any work. Execute only the currently approved milestone. Respect its "
            "scope, dependencies, acceptance criteria and explicit out-of-scope "
            "decisions. Apply REUSE FIRST, KISS and YAGNI."
        ),
    }
    return yaml.safe_dump(document, sort_keys=False)


def _validate_project_name(name: str) -> bool:
    return bool(_PROJECT_NAME_RE.fullmatch(name)) and not name.endswith((".", " "))


def _print_git_recovery(target: Path) -> None:
    print(
        f"\nFrom {target} run:\n\n"
        f"  cd {shlex.quote(str(target))}\n"
        "  git init -b main\n"
        "  git add .\n"
        '  git commit -m "Initialize AIDO project"\n',
        file=sys.stderr,
    )


def _run_git_bootstrap(target: Path) -> bool:
    git = shutil.which("git")
    if git is None:
        print("Error: Git is not installed or is not available in PATH.", file=sys.stderr)
        print(
            "\nAIDO requires a Git repository before governed development can start.",
            file=sys.stderr,
        )
        print("After installing Git:", file=sys.stderr)
        _print_git_recovery(target)
        return False

    for command in (["init", "-b", "main"], ["add", "."], ["commit", "-m", "Initialize AIDO project"]):
        try:
            subprocess.run(
                [git, *command], cwd=target, check=True, capture_output=True, text=True, timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"Error: Git step '{command[0]}' failed. Scaffold preserved.", file=sys.stderr)
            detail = str(getattr(exc, "stderr", "") or exc)
            print(detail, file=sys.stderr)
            if any(
                marker in detail.lower()
                for marker in ("identity", "user.email", "user.name", "auto-detect email", "who you are")
            ):
                print("Configure your Git identity before retrying the commit.", file=sys.stderr)
            _print_git_recovery(target)
            return False
    return True


def run_init(parent_path: str, project_name: str) -> int:
    """Scaffolds and Git-bootstraps a new AIDO project. Returns a process
    exit code — ``0`` on full success, non-zero (never a traceback) on
    any validation or Git failure. Fail-closed: a rejected target is
    never partially written to."""
    if not _validate_project_name(project_name):
        print(
            f"Error: project-name {project_name!r} must be a single, safe directory name "
            "(letters, digits, spaces, dots, hyphens; must start with a letter or digit; "
            "no path separators; no trailing dot or space). No file was modified.",
            file=sys.stderr,
        )
        return 1

    parent = Path(parent_path).expanduser().resolve()
    target = parent / project_name

    if target.is_symlink():
        print(f"Error: {target} is a symlink. No file was modified.", file=sys.stderr)
        return 1
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        print(f"Error: {target} already exists and is not empty.\nNo file was modified.", file=sys.stderr)
        return 1

    target.mkdir(parents=True, exist_ok=True)
    resources_dir = target / "resources"
    resources_dir.mkdir(exist_ok=True)

    project_id = _sanitize_project_id(project_name)
    (target / ".gitignore").write_text(_GITIGNORE, encoding="utf-8")
    (target / "README.md").write_text(_README_TEMPLATE.format(name=project_name), encoding="utf-8")
    (target / "ROADMAP.md").write_text(_ROADMAP_TEMPLATE.format(name=project_name), encoding="utf-8")
    (target / "aido.yaml").write_text(
        _manifest_content(project_id=project_id, project_name=project_name), encoding="utf-8",
    )
    (resources_dir / "README.md").write_text(_RESOURCES_README, encoding="utf-8")

    if not _run_git_bootstrap(target):
        return 1

    print(f"AIDO — project initialized\n\nProject: {project_name}\nDirectory: {target}")
    print("Git: initialized on branch main\nInitial commit: created")
    print("\nFiles created:\n  .gitignore\n  README.md\n  ROADMAP.md\n  aido.yaml\n  resources/README.md")
    print(
        f"\nNext steps:\n\n"
        f"1. cd {shlex.quote(str(target))}\n\n"
        "2. Edit README.md — describe the project, its purpose and its main constraints.\n"
        "3. Edit ROADMAP.md — define the first real milestone, then mark it Status: APPROVED "
        "when it is ready to execute.\n"
        "4. Edit aido.yaml if needed (project id/name/workspace/initial_prompt).\n"
    )
    return 0
