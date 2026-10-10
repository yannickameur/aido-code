"""Re-verifies M1.1's WI-M1.1-01 packaging acceptance criteria
as part of this WorkItem's (WI-M1.1-04) own QA gate: the engine
dependency is declared against the renamed ``ai-dev-orchestrator``
distribution, never the old ``orchestrator`` PyPI name.
"""

from __future__ import annotations

import re
from pathlib import Path

PYPROJECT_TEXT = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text()


class TestEngineDependencyMetadata:
    def test_declares_the_published_ai_dev_orchestrator_0_2_line(self) -> None:
        """0.2.0 is the first published engine release with the APIs this
        project uses: ``run(interrupt=...)`` (M3.2) and ``execution_times()``
        (M3.4), on top of the 0.1.3 quota snapshots (M1.2)."""
        match = re.search(r'dependencies\s*=\s*\[([^\]]*)\]', PYPROJECT_TEXT)
        assert match is not None, "pyproject.toml has no [project.dependencies] list"
        dependencies = match.group(1)
        assert re.search(r'"ai-dev-orchestrator\s*>=\s*0\.2\.0\s*,\s*<\s*0\.3"', dependencies), (
            f"expected an 'ai-dev-orchestrator>=0.2.0,<0.3' dependency, found: {dependencies!r}"
        )

    def test_never_declares_the_old_orchestrator_pypi_package_name(self) -> None:
        match = re.search(r'dependencies\s*=\s*\[([^\]]*)\]', PYPROJECT_TEXT)
        assert match is not None
        dependencies = match.group(1)
        assert not re.search(r'"orchestrator\s*[>=<~!]', dependencies), (
            f"a dependency on the old 'orchestrator' package name remains: {dependencies!r}"
        )
