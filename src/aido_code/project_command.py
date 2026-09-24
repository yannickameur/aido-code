"""AIDO's project-command context loading (WI-M1.4-07A, see ``docs/
PROJECT_CONTRACT.md`` §7).

The one cohesive loading path for aido-code's modern project commands:
loads the project manifest (§2, WI-M1.4-02), the deterministic
``ROADMAP.md`` (§3, WI-M1.4-03), resources (§5, WI-M1.4-04), and the AIDO
global ``WorkerRegistry`` (§4, WI-M1.4-01) — in that order, fail closed on
the first error, never a provider construction or probe. ``aido-code
validate`` (this WorkItem) and every later project command
(``run``/``status``/``workers``/``config``, WI-M1.4-07B/C/D) share this
exact path — none of them re-implements or parallels it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from orchestrator.worker_registry import WorkerRegistry

from aido_code.project_manifest import ProjectManifest, load_project_manifest
from aido_code.project_resources import ResolvedProjectResources, resolve_project_resources
from aido_code.roadmap import RoadmapDocument, parse_roadmap
from aido_code.worker_config import load_worker_registry

__all__ = ["ProjectCommandContext", "load_project_command_context"]


@dataclass(frozen=True)
class ProjectCommandContext:
    """Everything a project command needs, already loaded and validated."""

    manifest: ProjectManifest
    roadmap: RoadmapDocument
    resources: ResolvedProjectResources
    worker_registry: WorkerRegistry


def load_project_command_context(manifest_path: str | Path = "aido.yaml") -> ProjectCommandContext:
    """Loads and validates, in order: the manifest, the roadmap, resources,
    then the AIDO global ``WorkerRegistry``. Raises the first domain error
    encountered (``ProjectManifestError``/``RoadmapError``/
    ``ProjectResourcesError``/``orchestrator.worker_registry.
    WorkerRegistryError``) — later stages are never reached once an
    earlier one fails."""
    manifest = load_project_manifest(manifest_path)
    roadmap = parse_roadmap(manifest.roadmap)
    resources = resolve_project_resources(manifest, roadmap)
    worker_registry = load_worker_registry()
    return ProjectCommandContext(
        manifest=manifest, roadmap=roadmap, resources=resources, worker_registry=worker_registry,
    )
