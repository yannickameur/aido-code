"""AIDO's own resources resolution/confinement + ``initial_prompt``
combination (WI-M1.4-04, see ``docs/PROJECT_CONTRACT.md`` §5).

Ties together a loaded ``aido_code.project_manifest.ProjectManifest`` and a
parsed ``aido_code.roadmap.RoadmapDocument``: resolves each ``## Sources``
entry relative to ``workspace`` (the same base the manifest's own
``resources`` field uses, §2/§5), confines it inside ``workspace`` — no
``..`` traversal, no symlink escape anywhere along the resolved path —
and requires it to exist on disk, fail closed. ``## Sources`` is the
*only* mechanism that marks a file under ``resources/`` as normative; an
unreferenced file there is never auto-discovered. Nothing in this module
ever opens a resource file for writing.

Also builds the combined MVP objective string: ``initial_prompt`` + the
current milestone's own ``### Objective`` + the resolved ``## Sources``
list, via the exact, fixed, ``---``-delimited template §5 defines — never
a second template, never a per-WorkItem duplication of ``initial_prompt``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from aido_code.project_manifest import ProjectManifest
from aido_code.roadmap import RoadmapDocument

__all__ = [
    "ProjectResourcesError",
    "InvalidSourceError",
    "ResolvedProjectResources",
    "resolve_sources",
    "build_mvp_objective",
    "resolve_project_resources",
]


class ProjectResourcesError(Exception):
    """Base for resources resolution domain errors."""


class InvalidSourceError(ProjectResourcesError):
    """Raised for any ``## Sources`` entry that fails to resolve, confine,
    or exist."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"invalid '## Sources' entry: {detail}")


def _resolve_confined_source(raw: str, *, workspace: Path) -> Path:
    """Same resolution/confinement shape as
    ``project_manifest._resolve_confined_path``: relative to ``workspace``
    (never the caller's cwd). Sources must be workspace-relative and
    contain no ``..`` segments. Symlinks are then followed and the result
    must still be a file inside ``workspace``."""
    source = Path(raw)
    if source.is_absolute() or ".." in source.parts:
        raise InvalidSourceError(f"{raw!r} must be a workspace-relative path without '..' traversal")
    candidate = workspace / source
    resolved = candidate.resolve()
    if resolved != workspace and workspace not in resolved.parents:
        raise InvalidSourceError(
            f"{raw!r} resolves to {str(resolved)!r}, which is outside workspace "
            f"{str(workspace)!r} — no '..' traversal or symlink escape out of workspace is allowed"
        )
    if not resolved.is_file():
        raise InvalidSourceError(f"{raw!r} (resolved to {str(resolved)!r}) is not an existing file on disk")
    return resolved


def resolve_sources(sources: Sequence[str], *, workspace: Path) -> tuple[Path, ...]:
    """Resolves every ``## Sources`` bullet relative to ``workspace``,
    fail closed on the first invalid entry — never a partial list."""
    return tuple(_resolve_confined_source(raw, workspace=workspace) for raw in sources)


def build_mvp_objective(
    *,
    initial_prompt: str,
    milestone_id: str,
    milestone_objective: str,
    resolved_sources: Sequence[Path],
    workspace: Path,
) -> str:
    """The exact, fixed, ``---``-delimited three-section template
    ``docs/PROJECT_CONTRACT.md`` §5 defines — no second template, no
    rewriting of either input string. Each declared source is listed as a
    workspace-relative path, one per line, in the same order §3.1 parsed
    them; an empty list renders as ``"(none)"``."""
    sources_block = (
        "\n".join(path.relative_to(workspace).as_posix() for path in resolved_sources)
        if resolved_sources
        else "(none)"
    )
    return (
        f"{initial_prompt}\n"
        "\n"
        f"--- Current milestone objective (ROADMAP.md, {milestone_id}) ---\n"
        f"{milestone_objective}\n"
        "\n"
        "--- Declared sources (ROADMAP.md, ## Sources) ---\n"
        f"{sources_block}"
    )


class ResolvedProjectResources:
    __slots__ = ("sources", "mvp_objective")

    def __init__(self, *, sources: tuple[Path, ...], mvp_objective: str) -> None:
        self.sources = sources
        self.mvp_objective = mvp_objective


def resolve_project_resources(
    manifest: ProjectManifest, roadmap: RoadmapDocument,
) -> ResolvedProjectResources:
    """The whole §5 path in one call: resolve+confine the roadmap's
    ``## Sources`` entries against the manifest's ``workspace``, then
    build the combined MVP objective string from ``manifest.
    initial_prompt`` + ``roadmap.milestone`` + those resolved sources."""
    sources = resolve_sources(roadmap.sources, workspace=manifest.project.workspace)
    mvp_objective = build_mvp_objective(
        initial_prompt=manifest.initial_prompt,
        milestone_id=roadmap.milestone.id,
        milestone_objective=roadmap.milestone.objective,
        resolved_sources=sources,
        workspace=manifest.project.workspace,
    )
    return ResolvedProjectResources(sources=sources, mvp_objective=mvp_objective)
