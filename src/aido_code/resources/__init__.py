"""Packaged, non-Python resources shipped inside the ``aido-code`` wheel.

Currently just ``default_workers.yaml`` (WI-M1.4-01, see ROADMAP.md and
``docs/PROJECT_CONTRACT.md`` §4) — AIDO's own global worker registry,
used directly, in memory, whenever no ``$XDG_CONFIG_HOME/aido/
workers.yaml``/``~/.config/aido/workers.yaml`` override exists.

CANONICAL, not legacy: this is a self-contained copy, never a read of
``ai-dev-orchestrator``'s own packaged ``orchestrator/resources/
default_workers.yaml`` (that file stays that project's legacy, CLI-only
concern). AIDO Code owns its own worker defaults; see
``aido_code.worker_config``, the only module allowed to read this file.
"""
