"""Re-verifies M1_1_SPEC.yaml's WI-M1.1-01 packaging acceptance criteria
as part of this WorkItem's (WI-M1.1-04) own QA gate: the engine
dependency is declared against the renamed ``ai-dev-orchestrator``
distribution, never the old ``orchestrator`` PyPI name.
"""

from __future__ import annotations

import re
from pathlib import Path

PYPROJECT_TEXT = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text()


class TestEngineDependencyMetadata:
    def test_declares_ai_dev_orchestrator_at_or_above_0_1_2(self) -> None:
        match = re.search(r'dependencies\s*=\s*\[([^\]]*)\]', PYPROJECT_TEXT)
        assert match is not None, "pyproject.toml has no [project.dependencies] list"
        dependencies = match.group(1)
        assert re.search(r'"ai-dev-orchestrator\s*>=\s*0\.1\.2"', dependencies), (
            f"expected an 'ai-dev-orchestrator>=0.1.2' dependency, found: {dependencies!r}"
        )

    def test_never_declares_the_old_orchestrator_pypi_package_name(self) -> None:
        match = re.search(r'dependencies\s*=\s*\[([^\]]*)\]', PYPROJECT_TEXT)
        assert match is not None
        dependencies = match.group(1)
        assert not re.search(r'"orchestrator\s*[>=<~!]', dependencies), (
            f"a dependency on the old 'orchestrator' package name remains: {dependencies!r}"
        )
