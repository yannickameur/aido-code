"""AIDO's own project manifest parser (WI-M1.4-02, see ``docs/
PROJECT_CONTRACT.md`` §2).

Parses a project's ``aido.yaml`` — the launch manifest only, never the
executable contract itself (``ROADMAP.md``, §3, parsed by a different,
later WorkItem). A user project's manifest knows exactly four things —
which project, which roadmap, which resources, which first instruction —
and never a worker, a provider, a model, or a ``workers.yaml`` path
(that boundary belongs to ``aido_code.worker_config``, §4).

**Allowed top-level keys, exhaustively**: ``schema_version``, ``project``
(``id``/``name``/``workspace``), ``roadmap``, ``resources``,
``initial_prompt``. Any other top-level key — ``workers``, ``providers``,
``models``, ``mvp``, ``work_items``, ``qa``, ``execution``, ``git``, or
anything else — is rejected, fail-closed, before a single field is
trusted. This mirrors ``ai-dev-orchestrator``'s own
``orchestrator.project_config._reject_unknown_keys``/
``_PROJECT_ID_PATTERN``/secret-substring guard-rail shapes, but
**reproduces** them rather than importing that module: this manifest is
parsed entirely inside ``aido_code``, before any ``ProjectConfig``
exists, and this package's own structural test
(``tests/test_structural.py``) forbids importing any
``orchestrator.project_config`` internals here.

Path semantics: every relative path in ``aido.yaml`` (``project.workspace``,
``roadmap``, ``resources``) resolves relative to the *directory
containing that ``aido.yaml`` file*, never the caller's current working
directory. ``~`` is expanded. ``roadmap``/``resources`` must each resolve
to a location **inside** the resolved ``project.workspace`` — no ``..``
traversal, no symlink escaping ``workspace`` — using the same
fail-closed path-safety principle for project-contained files.

NO SECRETS — same guard-rail ``ai-dev-orchestrator``'s own
``project_config``/``worker_registry`` modules use: a handful of
obviously-wrong key name substrings (``api_key``, ``token``, ``secret``,
``password``, ``credential``, ...) anywhere in the document are
rejected. Provider authentication stays entirely with the provider
CLI/environment, never this manifest.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

import yaml

__all__ = [
    "SUPPORTED_SCHEMA_VERSION",
    "ProjectManifestError",
    "InvalidProjectManifestError",
    "UnsupportedSchemaVersionError",
    "ProjectIdentity",
    "ProjectManifest",
    "load_project_manifest",
]

SUPPORTED_SCHEMA_VERSION = 1
DEFAULT_MANIFEST_FILENAME = "aido.yaml"

# Same substrings ai-dev-orchestrator's own project_config/worker_registry
# modules use — reproduced verbatim, deliberately simple substring
# matching, never a general secret scanner.
_FORBIDDEN_KEY_SUBSTRINGS = ("api_key", "apikey", "token", "secret", "password", "passwd", "credential")

_TOP_LEVEL_KEYS = frozenset({"schema_version", "project", "roadmap", "resources", "initial_prompt"})
_PROJECT_KEYS = frozenset({"id", "name", "workspace"})

# Same pattern ai-dev-orchestrator's own project_config._PROJECT_ID_PATTERN
# uses — letters/digits/'.'/'_'/'-', must start with a letter or digit,
# never contains '..' or a path separator (it can feed a default
# state_dir downstream, so it can never escape it).
_PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class ProjectManifestError(Exception):
    """Base for ProjectManifest domain errors."""


class InvalidProjectManifestError(ProjectManifestError):
    """Raised for any structurally invalid ``aido.yaml`` content."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"invalid project manifest: {detail}")


class UnsupportedSchemaVersionError(ProjectManifestError):
    def __init__(self, version: Any) -> None:
        super().__init__(
            f"unsupported schema_version {version!r} — this version of AIDO only "
            f"supports {SUPPORTED_SCHEMA_VERSION!r}"
        )
        self.version = version


def _reject_secrets(data: Any, *, path: str = "") -> None:
    """Same guard-rail as ``orchestrator.worker_registry``/
    ``orchestrator.project_config`` — reproduced, not imported."""
    if isinstance(data, Mapping):
        for key, value in data.items():
            key_str = str(key).lower()
            if any(bad in key_str for bad in _FORBIDDEN_KEY_SUBSTRINGS):
                raise InvalidProjectManifestError(
                    f"field {(path + '.' + str(key)) if path else key!r} looks like a secret "
                    "(api keys/tokens/credentials never belong in aido.yaml — "
                    "authentication stays with the provider CLI)"
                )
            _reject_secrets(value, path=f"{path}.{key}" if path else str(key))
    elif isinstance(data, (list, tuple)):
        for index, item in enumerate(data):
            _reject_secrets(item, path=f"{path}[{index}]")


def _require_mapping(data: Any, *, context: str) -> Mapping:
    if not isinstance(data, Mapping):
        raise InvalidProjectManifestError(f"{context} must be a mapping")
    return data


def _reject_unknown_keys(data: Mapping, allowed: frozenset[str], *, context: str) -> None:
    unknown = set(data.keys()) - allowed
    if unknown:
        raise InvalidProjectManifestError(
            f"{context}: unknown field(s) {sorted(map(str, unknown))!r} — allowed: {sorted(allowed)!r}"
        )


def _require_str(data: Mapping, key: str, *, context: str) -> str:
    if key not in data:
        raise InvalidProjectManifestError(f"{context}: missing required field {key!r}")
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise InvalidProjectManifestError(f"{context}: field {key!r} must be a non-empty string, got {value!r}")
    return value


def _validate_project_id(project_id: str) -> None:
    if not _PROJECT_ID_PATTERN.fullmatch(project_id) or ".." in project_id:
        raise InvalidProjectManifestError(
            f"project.id {project_id!r} is invalid — only letters, digits, '.', '_', '-' are "
            "allowed, must start with a letter or digit, and must never contain '..' or a path "
            "separator"
        )


def _resolve_path(raw: str, *, base_dir: Path) -> Path:
    """Resolves ``raw`` relative to ``base_dir`` (the directory containing
    ``aido.yaml``, never the caller's cwd), expands ``~``, and fully
    resolves symlinks/``..`` segments — the same canonicalization needed
    both for a stable path and for the confinement check below."""
    expanded = Path(raw).expanduser()
    candidate = expanded if expanded.is_absolute() else base_dir / expanded
    return candidate.resolve()


def _resolve_confined_path(raw: str, *, base_dir: Path, workspace: Path, field: str) -> Path:
    """Same resolution as ``_resolve_path``, then verifies the resolved,
    symlink-followed path is still ``workspace`` itself or a descendant
    of it — fail closed on ``..`` traversal or a symlink escaping
    ``workspace`` (same fail-closed confinement principle)."""
    resolved = _resolve_path(raw, base_dir=base_dir)
    if resolved != workspace and workspace not in resolved.parents:
        raise InvalidProjectManifestError(
            f"{field} {raw!r} resolves to {str(resolved)!r}, which is outside project.workspace "
            f"{str(workspace)!r} — no '..' traversal or symlink escape out of workspace is allowed"
        )
    return resolved


class ProjectIdentity:
    __slots__ = ("id", "name", "workspace")

    def __init__(self, *, id: str, name: str, workspace: Path) -> None:
        self.id = id
        self.name = name
        self.workspace = workspace


class ProjectManifest:
    """A fully loaded, validated ``aido.yaml`` (schema v1, §2)."""

    __slots__ = ("schema_version", "project", "roadmap", "resources", "initial_prompt", "source_path")

    def __init__(
        self, *, schema_version: int, project: ProjectIdentity, roadmap: Path, resources: Path,
        initial_prompt: str, source_path: Path,
    ) -> None:
        self.schema_version = schema_version
        self.project = project
        self.roadmap = roadmap
        self.resources = resources
        self.initial_prompt = initial_prompt
        self.source_path = source_path


def load_project_manifest(path: str | Path) -> ProjectManifest:
    """Fail-closed: any structural problem raises before a single field is
    trusted — never a partially-loaded manifest."""
    source_path = Path(path).expanduser().resolve()
    try:
        text = source_path.read_text()
    except OSError as exc:
        raise InvalidProjectManifestError(f"could not read {source_path}: {exc}") from exc
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise InvalidProjectManifestError(f"invalid YAML: {exc}") from exc

    top = _require_mapping(document, context="aido.yaml")
    _reject_unknown_keys(top, _TOP_LEVEL_KEYS, context="aido.yaml")
    _reject_secrets(top)

    schema_version = top.get("schema_version")
    if type(schema_version) is not int or schema_version != SUPPORTED_SCHEMA_VERSION:
        raise UnsupportedSchemaVersionError(schema_version)

    base_dir = source_path.parent

    project_data = _require_mapping(top.get("project"), context="project")
    _reject_unknown_keys(project_data, _PROJECT_KEYS, context="project")
    project_id = _require_str(project_data, "id", context="project")
    _validate_project_id(project_id)
    project_name = _require_str(project_data, "name", context="project")
    workspace_raw = _require_str(project_data, "workspace", context="project")
    workspace = _resolve_path(workspace_raw, base_dir=base_dir)
    if not workspace.is_dir():
        raise InvalidProjectManifestError(f"project.workspace {str(workspace)!r} is not an existing directory")
    project = ProjectIdentity(id=project_id, name=project_name, workspace=workspace)

    roadmap_raw = _require_str(top, "roadmap", context="aido.yaml")
    roadmap = _resolve_confined_path(roadmap_raw, base_dir=base_dir, workspace=workspace, field="roadmap")

    resources_raw = _require_str(top, "resources", context="aido.yaml")
    resources = _resolve_confined_path(resources_raw, base_dir=base_dir, workspace=workspace, field="resources")
    if not resources.is_dir():
        raise InvalidProjectManifestError(f"resources {str(resources)!r} is not an existing directory")

    initial_prompt = _require_str(top, "initial_prompt", context="aido.yaml")

    return ProjectManifest(
        schema_version=schema_version, project=project, roadmap=roadmap, resources=resources,
        initial_prompt=initial_prompt, source_path=source_path,
    )
