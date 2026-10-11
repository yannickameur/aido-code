"""Read actual installed runtime versions; no project, probe or external command."""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version


def _installed_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "not installed"


def format_versions() -> str:
    """One renderer shared by CLI and interactive commands."""
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return "\n".join((
        f"AIDO Code           : {_installed_version('aido-code')}",
        f"AI Dev Orchestrator : {_installed_version('ai-dev-orchestrator')}",
        f"Python              : {python_version}",
    ))
