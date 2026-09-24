"""AIDO's own typed engine plan builder (WI-M1.4-05, see ``docs/
PROJECT_CONTRACT.md`` §6).

Transforms a loaded ``aido_code.project_manifest.ProjectManifest`` + a
parsed ``aido_code.roadmap.RoadmapDocument`` + resolved
``aido_code.project_resources.ResolvedProjectResources`` into a real
``orchestrator.project_config.ProjectConfig`` — built through that
type's own plain Python constructor (``ProjectIdentity``/
``ExecutionConfig``/``GitConfig``/``MVPConfig``/``WorkItemConfig``/
``ValidationCommand``, all imported from ``ai-dev-orchestrator``
unchanged), never ``ProjectConfig.load(path)`` (there is no
``ProjectConfig``-shaped YAML file anywhere in this product path) and
never a second, parallel "engine plan" type (REUSE FIRST, the same seam
``ai-dev-orchestrator``'s own P13.5 built for this exact purpose).

``workers_registry_path`` stays ``None`` always: the caller (this
package's command layer) injects an already-built ``WorkerRegistry``
(``aido_code.worker_config.load_worker_registry``, §4) directly into
``OrchestratorEngine``'s own plain constructor
(``aido_code.engine_client.EngineClient.from_config``) — this module
never loads or references a worker registry itself.

Before this plan is ever handed to the engine, ``workspace`` is
confirmed to be inside a real Git work tree — the same fail-closed check
``orchestrator.project_config.ProjectConfig.load()`` already performs
(reproduced here, not imported, since it is a private module-level
function and this path never calls ``.load()``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from orchestrator.execution_policy import ExecutionPermissionMode
from orchestrator.project_config import (
    SUPPORTED_SCHEMA_VERSION,
    ExecutionConfig,
    GitConfig,
    MVPConfig,
    ProjectConfig,
    ProjectIdentity,
    WorkItemConfig,
)
from orchestrator.validation import ValidationCommand, ValidationKind

from aido_code.project_manifest import ProjectManifest
from aido_code.project_resources import ResolvedProjectResources
from aido_code.roadmap import QACommandSpec, RoadmapDocument, WorkItemSpec

__all__ = [
    "EnginePlanError",
    "MissingGitWorkspaceError",
    "build_engine_plan",
]

# Same default git.base_branch ProjectConfig.load() already uses when a
# legacy aido.yaml's own git: section is omitted (docs/PROJECT_CONTRACT.md
# §6) — aido.yaml never carries a git: section at all (§2), so this is
# never anything but "main" in the M1.4 product path.
_GIT_BASE_BRANCH = "main"


class EnginePlanError(Exception):
    """Base for typed-engine-plan domain errors."""


class MissingGitWorkspaceError(EnginePlanError):
    """An existing workspace needs Git setup before it can be governed —
    same meaning as ``orchestrator.project_config.
    MissingGitWorkspaceError``, reproduced here since this path never
    calls ``ProjectConfig.load()``."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        super().__init__(f"project.workspace {str(workspace)!r} is not inside a Git working tree")


def _default_state_dir(project_id: str) -> Path:
    """Identical formula to ``ai-dev-orchestrator``'s own
    ``orchestrator.project_config._default_state_dir(project_id)`` —
    reproduced, not imported (a private function): a project already
    governed under M1-M1.3 is never orphaned or duplicated under M1.4."""
    return Path.home() / ".local" / "state" / "ai-dev-orchestrator" / "projects" / project_id


def _is_inside_git_work_tree(path: Path) -> bool:
    """Same read-only Git check as ``orchestrator.project_config.
    _is_inside_git_work_tree`` — reproduced, not imported (a private
    function)."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(path), capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.strip() == "true"


def _ensure_git_workspace(workspace: Path) -> None:
    if not _is_inside_git_work_tree(workspace):
        raise MissingGitWorkspaceError(workspace)


def _build_work_item(spec: WorkItemSpec) -> WorkItemConfig:
    return WorkItemConfig(
        id=spec.id,
        title=spec.title,
        required_capabilities=spec.capabilities,
        dependencies=spec.dependencies,
        acceptance_criteria=spec.acceptance_criteria,
    )


def _build_qa_command(spec: QACommandSpec) -> ValidationCommand:
    return ValidationCommand(
        validation_id=spec.id,
        kind=ValidationKind(spec.kind),
        argv=spec.argv,
        timeout_seconds=spec.timeout_seconds,
        required=spec.required,
    )


def build_engine_plan(
    manifest: ProjectManifest,
    roadmap: RoadmapDocument,
    resolved_resources: ResolvedProjectResources,
) -> ProjectConfig:
    """The whole §6 path in one call: confirms ``workspace`` is a real Git
    work tree, fail closed, then builds a ``ProjectConfig`` field by
    field per the mapping table in ``docs/PROJECT_CONTRACT.md`` §6.
    ``workers_registry_path`` is always ``None`` — the caller injects a
    ``WorkerRegistry`` directly into the engine instead."""
    _ensure_git_workspace(manifest.project.workspace)

    milestone = roadmap.milestone
    project = ProjectIdentity(
        id=manifest.project.id,
        name=manifest.project.name,
        workspace=manifest.project.workspace,
        state_dir=_default_state_dir(manifest.project.id),
    )
    execution = ExecutionConfig(permission_mode=ExecutionPermissionMode.STANDARD)
    git = GitConfig(base_branch=_GIT_BASE_BRANCH)
    mvp = MVPConfig(
        id=milestone.id,
        objective=resolved_resources.mvp_objective,
        acceptance_criteria=milestone.acceptance_criteria,
    )
    work_items = tuple(_build_work_item(item) for item in milestone.work_items)
    qa_commands = tuple(_build_qa_command(qa) for qa in milestone.qa_commands)

    return ProjectConfig(
        schema_version=SUPPORTED_SCHEMA_VERSION,
        project=project,
        workers_registry_path=None,
        execution=execution,
        git=git,
        mvp=mvp,
        work_items=work_items,
        qa_commands=qa_commands,
        qa_protected_paths=(),
        source_path=roadmap.source_path,
    )
