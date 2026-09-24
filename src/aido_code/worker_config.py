"""AIDO's own global worker configuration (WI-M1.4-01, see ROADMAP.md and
``docs/PROJECT_CONTRACT.md`` §4).

Workers belong to AIDO, never to a project — no project ever references
a worker/provider/model/``workers.yaml`` path (see
``aido_code.engine_client``'s M1.4 callers). This module answers exactly
one question: which ``orchestrator.worker_registry.WorkerRegistry``
applies, resolved in order:

1. ``$XDG_CONFIG_HOME/aido/workers.yaml``
2. ``~/.config/aido/workers.yaml`` (when ``XDG_CONFIG_HOME`` is unset or
   empty)
3. AIDO Code's own packaged default (``aido_code/resources/
   default_workers.yaml``), used directly, in memory — never
   auto-materialized to disk.

Every candidate is loaded with ``orchestrator.worker_registry.
WorkerRegistry.load(path)`` — no worker-parsing logic of this module's
own. A malformed override fails closed with that module's own
``WorkerRegistryError`` taxonomy, never a silent fallback to the
packaged default.

Never referenced here: ``ai-dev-orchestrator``'s own ``config/
workers.yaml``, ``../ai-dev-orchestrator/config/workers.yaml``, or
``~/.config/ai-dev-orchestrator/workers.yaml`` — those remain that
project's own legacy CLI concern, never this product's modern path.
"""

from __future__ import annotations

import os
from importlib.resources import as_file, files
from pathlib import Path

from orchestrator.worker_registry import WorkerRegistry

__all__ = ["load_worker_registry", "resolve_workers_override_path"]

_PACKAGED_DEFAULT_PACKAGE = "aido_code.resources"
_PACKAGED_DEFAULT_NAME = "default_workers.yaml"


def resolve_workers_override_path() -> Path | None:
    """Returns AIDO's own user-level ``workers.yaml`` override path if a
    real file exists there, else ``None`` (meaning: use the packaged
    default). Never checks any ``ai-dev-orchestrator``-owned location.
    """
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    config_home = Path(xdg_config_home) if xdg_config_home else Path.home() / ".config"
    candidate = config_home / "aido" / "workers.yaml"
    return candidate if candidate.is_file() else None


def load_worker_registry() -> WorkerRegistry:
    """Loads AIDO's global ``WorkerRegistry``: the user override when one
    exists on disk, else AIDO Code's own packaged default — always
    through ``WorkerRegistry.load(path)``, never a second parser.
    """
    override_path = resolve_workers_override_path()
    if override_path is not None:
        return WorkerRegistry.load(override_path)

    packaged_default = files(_PACKAGED_DEFAULT_PACKAGE).joinpath(_PACKAGED_DEFAULT_NAME)
    with as_file(packaged_default) as path:
        return WorkerRegistry.load(path)
