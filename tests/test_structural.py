"""Structural proof for the MVP_SPEC.yaml acceptance criterion that no
command in this MVP ever constructs ``MVPManager``, ``WorkerSelector``,
``QuotaManager``, a ``ProviderAdapter``, or reads a Store/SQLite file
directly (analogous to ai-dev-orchestrator's own
``test_cli.py::TestStatus::test_status_never_instantiates_any_provider_adapter``).

``aido_code``'s source is small enough that the strongest proof is
static: walk every module's imports and assert the only ``orchestrator``
submodule ever named is ``orchestrator.engine`` itself, and that
``sqlite3`` is never imported at all. Anything reaching a
``MVPManager``/``WorkerSelector``/``QuotaManager``/``ProviderAdapter``/
``*Store`` would have to do so through one of those forbidden imports
first.
"""

from __future__ import annotations

import ast
from pathlib import Path

import aido_code

FORBIDDEN_MODULE_PREFIXES = ("sqlite3",)
ALLOWED_ORCHESTRATOR_MODULES = {"orchestrator", "orchestrator.engine"}


def _imported_module_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


class TestNeverReachesInternalOrchestratorState:
    def test_package_source_only_ever_imports_orchestrator_engine(self) -> None:
        package_dir = Path(aido_code.__file__).parent
        for path in sorted(package_dir.rglob("*.py")):
            tree = ast.parse(path.read_text(), filename=str(path))
            for module_name in _imported_module_names(tree):
                if module_name == "orchestrator" or module_name.startswith("orchestrator."):
                    assert module_name in ALLOWED_ORCHESTRATOR_MODULES, (
                        f"{path}: imports {module_name!r}, but this package must reach "
                        "orchestrator internals (MVPManager/WorkerSelector/QuotaManager/"
                        "ProviderAdapter/Store) only through orchestrator.engine"
                    )
                for forbidden in FORBIDDEN_MODULE_PREFIXES:
                    assert not (module_name == forbidden or module_name.startswith(forbidden + ".")), (
                        f"{path}: imports {module_name!r} directly; no command in this MVP "
                        "may read a Store/SQLite file directly"
                    )
