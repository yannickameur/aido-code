"""WI-M1.4-03: deterministic ``ROADMAP.md`` parser (``aido_code.roadmap``).
See ``docs/PROJECT_CONTRACT.md`` §3.

Offline only: every case here uses a real ``tmp_path`` file — never a
network/provider call.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aido_code.roadmap import InvalidRoadmapError, parse_roadmap

BASE_ROADMAP = """\
# ROADMAP — My Project

## Vision

Free text. Not parsed structurally.

## Sources

- resources/specification.md
- resources/decisions.md

## Current milestone

Status: {status}

### ID

m1

### Objective

Free text — this milestone's own objective.

### Acceptance criteria

- The feature works as described.

### WorkItems

#### WI-01 — First task

Dependencies: none
Capabilities: development

Acceptance criteria:

- Criterion one.

#### WI-02 — Second task

Dependencies: WI-01
Capabilities: development

Acceptance criteria:

- Criterion two.

### QA

#### QA-01 — Tests

Kind: unit_test
Required: true
Timeout: 300
Argv: ["pytest", "-q"]

### Out of scope

- Anything explicitly not built by this milestone.

## Future milestones

Free text. Not parsed structurally.
"""


def _write_roadmap(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "ROADMAP.md"
    path.write_text(text)
    return path


def _valid_text(*, status: str = "APPROVED") -> str:
    return BASE_ROADMAP.format(status=status)


class TestValidRoadmap:
    def test_valid_draft_roadmap_parses(self, tmp_path: Path) -> None:
        path = _write_roadmap(tmp_path, _valid_text(status="DRAFT"))
        document = parse_roadmap(path)

        assert document.milestone.status == "DRAFT"
        assert document.milestone.is_executable is False
        assert document.milestone.id == "m1"
        assert "objective" in document.milestone.objective.lower()
        assert document.milestone.acceptance_criteria == ("The feature works as described.",)
        assert [item.id for item in document.milestone.work_items] == ["WI-01", "WI-02"]
        assert document.milestone.work_items[0].dependencies == ()
        assert document.milestone.work_items[0].capabilities == ("development",)
        assert document.milestone.work_items[0].acceptance_criteria == ("Criterion one.",)
        assert document.milestone.work_items[1].dependencies == ("WI-01",)
        assert len(document.milestone.qa_commands) == 1
        qa = document.milestone.qa_commands[0]
        assert qa.id == "QA-01"
        assert qa.kind == "unit_test"
        assert qa.required is True
        assert qa.timeout_seconds == 300.0
        assert qa.argv == ("pytest", "-q")
        assert document.milestone.out_of_scope == ("Anything explicitly not built by this milestone.",)
        assert document.sources == ("resources/specification.md", "resources/decisions.md")
        assert document.source_path == path.resolve()

    def test_valid_approved_roadmap_parses_and_is_executable(self, tmp_path: Path) -> None:
        path = _write_roadmap(tmp_path, _valid_text(status="APPROVED"))
        document = parse_roadmap(path)

        assert document.milestone.status == "APPROVED"
        assert document.milestone.is_executable is True


class TestCurrentMilestoneHeadingCount:
    def test_zero_current_milestone_headings_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace("## Current milestone", "## Not the current milestone")
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="exactly one"):
            parse_roadmap(path)

    def test_two_current_milestone_headings_rejected(self, tmp_path: Path) -> None:
        text = _valid_text() + "\n" + _valid_text()
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="exactly one"):
            parse_roadmap(path)


class TestStatusLine:
    @pytest.mark.parametrize("bad_status", ["approved", "Approved", "WIP", "APPROVED ", "DRAFT!"])
    def test_unrecognized_status_value_rejected(self, tmp_path: Path, bad_status: str) -> None:
        text = _valid_text().replace("Status: APPROVED", f"Status: {bad_status}")
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="Status"):
            parse_roadmap(path)

    def test_missing_status_line_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace("Status: APPROVED\n\n", "")
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="Status"):
            parse_roadmap(path)


class TestWorkItemIdUniqueness:
    def test_duplicate_work_item_id_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace("#### WI-02 — Second task", "#### WI-01 — Second task")
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="duplicate WorkItem id"):
            parse_roadmap(path)


@pytest.mark.parametrize(
    ("original", "replacement"),
    [
        ("### WorkItems\n\n", "### WorkItems\n\nUnexpected prose.\n\n"),
        ("### QA\n\n", "### QA\n\nUnexpected prose.\n\n"),
        ("Status: APPROVED\n\n", "Status: APPROVED\n\nUnexpected prose.\n\n"),
        ("#### WI-01 — First task", "#### WI-01 —  First task"),
        ("#### WI-01 — First task", "#### WI-01 — First task "),
        ("#### QA-01 — Tests", "#### QA-01 —  Tests"),
    ],
)
def test_unexpected_content_or_malformed_entry_heading_rejected(
    tmp_path: Path, original: str, replacement: str,
) -> None:
    path = _write_roadmap(tmp_path, _valid_text().replace(original, replacement))
    with pytest.raises(InvalidRoadmapError):
        parse_roadmap(path)


class TestDependencyValidation:
    def test_unknown_dependency_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace("Dependencies: WI-01", "Dependencies: WI-99")
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="unknown WorkItem id"):
            parse_roadmap(path)

    def test_two_node_dependency_cycle_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace("Dependencies: none", "Dependencies: WI-02")
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="dependency cycle"):
            parse_roadmap(path)

    def test_three_node_dependency_cycle_rejected(self, tmp_path: Path) -> None:
        work_items_block = """\
#### WI-01 — First task

Dependencies: WI-03
Capabilities: development

Acceptance criteria:

- Criterion one.

#### WI-02 — Second task

Dependencies: WI-01
Capabilities: development

Acceptance criteria:

- Criterion two.

#### WI-03 — Third task

Dependencies: WI-02
Capabilities: development

Acceptance criteria:

- Criterion three.
"""
        original_block = """\
#### WI-01 — First task

Dependencies: none
Capabilities: development

Acceptance criteria:

- Criterion one.

#### WI-02 — Second task

Dependencies: WI-01
Capabilities: development

Acceptance criteria:

- Criterion two.
"""
        text = _valid_text().replace(original_block, work_items_block)
        assert text != _valid_text()  # sanity: replacement actually matched
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="dependency cycle"):
            parse_roadmap(path)


class TestWorkItemAcceptanceCriteria:
    def test_zero_acceptance_criteria_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace(
            "Acceptance criteria:\n\n- Criterion two.", "Acceptance criteria:\n"
        )
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="at least one"):
            parse_roadmap(path)

    def test_missing_blank_line_before_acceptance_criteria_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace(
            "Capabilities: development\n\nAcceptance criteria:",
            "Capabilities: development\nAcceptance criteria:",
        )
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="blank line"):
            parse_roadmap(path)


class TestMalformedArgv:
    def test_argv_not_json_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace('Argv: ["pytest", "-q"]', "Argv: not-json")
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="valid JSON"):
            parse_roadmap(path)

    def test_argv_not_array_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace('Argv: ["pytest", "-q"]', 'Argv: {"cmd": "pytest"}')
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="JSON array"):
            parse_roadmap(path)

    def test_argv_non_string_element_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace('Argv: ["pytest", "-q"]', 'Argv: ["pytest", 5]')
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="non-empty strings"):
            parse_roadmap(path)

    def test_argv_empty_string_element_rejected(self, tmp_path: Path) -> None:
        text = _valid_text().replace('Argv: ["pytest", "-q"]', 'Argv: ["pytest", ""]')
        path = _write_roadmap(tmp_path, text)
        with pytest.raises(InvalidRoadmapError, match="non-empty strings"):
            parse_roadmap(path)


def test_non_finite_timeout_rejected(tmp_path: Path) -> None:
    text = _valid_text().replace("Timeout: 300", "Timeout: " + "9" * 400)
    path = _write_roadmap(tmp_path, text)
    with pytest.raises(InvalidRoadmapError, match="positive"):
        parse_roadmap(path)


class TestOutOfScopeAndSourcesParsed:
    def test_out_of_scope_and_sources_never_dropped(self, tmp_path: Path) -> None:
        path = _write_roadmap(tmp_path, _valid_text())
        document = parse_roadmap(path)

        assert document.milestone.out_of_scope == ("Anything explicitly not built by this milestone.",)
        assert document.sources == ("resources/specification.md", "resources/decisions.md")

    def test_missing_out_of_scope_and_sources_are_empty_tuples(self, tmp_path: Path) -> None:
        text = _valid_text()
        text = text.replace(
            "### Out of scope\n\n- Anything explicitly not built by this milestone.\n\n", ""
        )
        text = text.replace(
            "## Sources\n\n- resources/specification.md\n- resources/decisions.md\n\n", ""
        )
        path = _write_roadmap(tmp_path, text)
        document = parse_roadmap(path)

        assert document.milestone.out_of_scope == ()
        assert document.sources == ()
