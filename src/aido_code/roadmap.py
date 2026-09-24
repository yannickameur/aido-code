"""AIDO's own ``ROADMAP.md`` parser (WI-M1.4-03, see ``docs/
PROJECT_CONTRACT.md`` §3).

Parses the one deterministic Markdown grammar a project's ``ROADMAP.md``
must follow — the executable source of truth, never the launch manifest
(``aido.yaml``, §2, parsed by ``aido_code.project_manifest``). **No LLM
parses this file. No heuristic/free-form understanding. Fail closed on
any structural violation** — a malformed ``ROADMAP.md`` is always a
parse error here, never a best-effort partial read.

The dependency-cycle check mirrors the exact fail-closed DFS
(white/gray/black) algorithm shape ``ai-dev-orchestrator``'s own
``orchestrator.project_config._validate_work_items`` already implements
— reproduced, not imported: this module is parsed entirely inside
``aido_code``, and this package's own structural test
(``tests/test_structural.py``) forbids importing
``orchestrator.project_config``/``orchestrator.validation`` internals
here. Likewise, the QA ``Kind:`` taxonomy mirrors
``orchestrator.validation.ValidationKind``'s values verbatim rather than
importing that enum.

This module only ever *parses and validates structure*. It never applies
the ``run``-only ``Status: APPROVED`` gate itself (§3.2) — it exposes the
parsed ``status``/``is_executable`` fields so a later WorkItem (the
``validate``/``run`` commands, WI-M1.4-07) can apply that gate.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Sequence

__all__ = [
    "RoadmapError",
    "InvalidRoadmapError",
    "WorkItemSpec",
    "QACommandSpec",
    "CurrentMilestone",
    "RoadmapDocument",
    "parse_roadmap",
]

# Same character-safety pattern ai-dev-orchestrator's own
# project_config._PROJECT_ID_PATTERN uses (and aido_code.project_manifest
# reproduces for project.id) — reused here for the milestone ### ID and
# every WorkItem/QA #### id, since they all feed downstream typed ids
# (MVPConfig.id, WorkItemConfig.id, ...) verbatim.
_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Matches any Markdown ATX heading line, capturing the '#' run (its level)
# and the heading text (trailing whitespace stripped). Heading levels
# other than the one currently being scanned for are left as ordinary
# content lines by _split_by_heading_level below.
_HEADING_RE = re.compile(r"^(#+)\s+(.*?)\s*$")

# '#### <id> — <title>' — an em dash (U+2014), exactly one space on each
# side, byte-exact per docs/PROJECT_CONTRACT.md §3.1. Never a plain
# hyphen, never guessed/normalized.
_ID_TITLE_HEADING_RE = re.compile(r"^#### (\S+) — (\S(?:.*\S)?)$")

_BULLET_RE = re.compile(r"^- (.+)$")
_NUMBER_RE = re.compile(r"^\d+(\.\d+)?$")

# Mirrors orchestrator.validation.ValidationKind's values verbatim —
# reproduced, not imported (see module docstring).
_KNOWN_VALIDATION_KINDS = frozenset(
    {"unit_test", "integration_test", "lint", "typecheck", "build", "smoke", "custom"}
)

_MILESTONE_SUBSECTION_TITLES = frozenset(
    {"ID", "Objective", "Acceptance criteria", "WorkItems", "QA", "Out of scope"}
)


class RoadmapError(Exception):
    """Base for ROADMAP.md domain errors."""


class InvalidRoadmapError(RoadmapError):
    """Raised for any structurally invalid ``ROADMAP.md`` content."""

    def __init__(self, detail: str) -> None:
        super().__init__(f"invalid ROADMAP.md: {detail}")


class WorkItemSpec:
    __slots__ = ("id", "title", "dependencies", "capabilities", "acceptance_criteria")

    def __init__(
        self, *, id: str, title: str, dependencies: tuple[str, ...],
        capabilities: tuple[str, ...], acceptance_criteria: tuple[str, ...],
    ) -> None:
        self.id = id
        self.title = title
        self.dependencies = dependencies
        self.capabilities = capabilities
        self.acceptance_criteria = acceptance_criteria


class QACommandSpec:
    __slots__ = ("id", "title", "kind", "required", "timeout_seconds", "argv")

    def __init__(
        self, *, id: str, title: str, kind: str, required: bool,
        timeout_seconds: float, argv: tuple[str, ...],
    ) -> None:
        self.id = id
        self.title = title
        self.kind = kind
        self.required = required
        self.timeout_seconds = timeout_seconds
        self.argv = argv


class CurrentMilestone:
    __slots__ = (
        "status", "id", "objective", "acceptance_criteria",
        "work_items", "qa_commands", "out_of_scope",
    )

    def __init__(
        self, *, status: str, id: str, objective: str, acceptance_criteria: tuple[str, ...],
        work_items: tuple[WorkItemSpec, ...], qa_commands: tuple[QACommandSpec, ...],
        out_of_scope: tuple[str, ...],
    ) -> None:
        self.status = status
        self.id = id
        self.objective = objective
        self.acceptance_criteria = acceptance_criteria
        self.work_items = work_items
        self.qa_commands = qa_commands
        self.out_of_scope = out_of_scope

    @property
    def is_executable(self) -> bool:
        """``run``'s own §3.2 gate reads this — never re-derived downstream."""
        return self.status == "APPROVED"


class RoadmapDocument:
    __slots__ = ("milestone", "sources", "source_path")

    def __init__(
        self, *, milestone: CurrentMilestone, sources: tuple[str, ...], source_path: Path,
    ) -> None:
        self.milestone = milestone
        self.sources = sources
        self.source_path = source_path


def _heading_level(line: str) -> tuple[int, str] | None:
    match = _HEADING_RE.match(line)
    if match is None:
        return None
    return len(match.group(1)), match.group(2)


def _split_by_heading_level(lines: list[str], *, level: int) -> list[tuple[str, list[str]]]:
    """Splits ``lines`` into ``(raw_heading_line, content_lines)`` pairs,
    using only headings at exactly ``level`` as boundaries. Headings at
    other levels (e.g. a '####' entry while scanning for '###') are left
    as ordinary content lines belonging to whichever section they fall
    under. Content before the first matching heading is dropped — callers
    only ever care about named sections."""
    boundaries = [idx for idx, line in enumerate(lines) if (_heading_level(line) or (0,))[0] == level]
    sections = []
    for position, idx in enumerate(boundaries):
        end = boundaries[position + 1] if position + 1 < len(boundaries) else len(lines)
        sections.append((lines[idx], lines[idx + 1 : end]))
    return sections


def _titled_sections(lines: list[str], *, level: int) -> list[tuple[str, list[str]]]:
    return [(_heading_level(raw)[1], content) for raw, content in _split_by_heading_level(lines, level=level)]


def _sections_by_title(sections: list[tuple[str, list[str]]], title: str) -> list[list[str]]:
    return [content for section_title, content in sections if section_title == title]


def _require_single_section(sections: list[tuple[str, list[str]]], title: str) -> list[str]:
    matches = _sections_by_title(sections, title)
    if len(matches) != 1:
        raise InvalidRoadmapError(
            f"'### {title}' must appear exactly once inside 'Current milestone', found {len(matches)}"
        )
    return matches[0]


def _optional_single_section(sections: list[tuple[str, list[str]]], title: str) -> list[str] | None:
    matches = _sections_by_title(sections, title)
    if len(matches) > 1:
        raise InvalidRoadmapError(
            f"'### {title}' must appear at most once inside 'Current milestone', found {len(matches)}"
        )
    return matches[0] if matches else None


def _validate_id_like(value: str, *, field_name: str) -> None:
    if not value or not _ID_PATTERN.fullmatch(value) or ".." in value:
        raise InvalidRoadmapError(
            f"{field_name} {value!r} is invalid — only letters, digits, '.', '_', '-' are "
            "allowed, must start with a letter or digit, and must never contain '..' or a path "
            "separator"
        )


def _non_blank(lines: list[str]) -> list[str]:
    return [line for line in lines if line.strip() != ""]


def _parse_bullet_line(line: str, *, context: str) -> str:
    match = _BULLET_RE.match(line)
    if match is None:
        raise InvalidRoadmapError(f"{context}: expected a '- ' bullet line, got {line!r}")
    content = match.group(1).strip()
    if not content:
        raise InvalidRoadmapError(f"{context}: bullet must be non-empty")
    return content


def _parse_bullets(lines: list[str], *, context: str) -> tuple[str, ...]:
    return tuple(_parse_bullet_line(line, context=context) for line in _non_blank(lines))


def _parse_comma_list(raw: str, *, field: str) -> tuple[str, ...]:
    parts = [part.strip() for part in raw.split(",")]
    if any(not part for part in parts):
        raise InvalidRoadmapError(f"{field} must be a comma-separated list of non-empty values, got {raw!r}")
    return tuple(parts)


def _parse_status_line(lines: list[str]) -> tuple[str, int]:
    for index, line in enumerate(lines):
        if line.strip() == "":
            continue
        if line in ("Status: APPROVED", "Status: DRAFT"):
            return line[len("Status: ") :], index
        raise InvalidRoadmapError(
            f"'Current milestone' must begin with 'Status: APPROVED' or 'Status: DRAFT', got {line!r}"
        )
    raise InvalidRoadmapError("'Current milestone' must begin with a 'Status:' line")


def _parse_id_section(lines: list[str]) -> str:
    non_blank = _non_blank(lines)
    if len(non_blank) != 1:
        raise InvalidRoadmapError("'### ID' must contain exactly one non-empty line")
    value = non_blank[0].strip()
    _validate_id_like(value, field_name="milestone '### ID'")
    return value


def _parse_objective_section(lines: list[str]) -> str:
    text = "\n".join(lines).strip()
    if not text:
        raise InvalidRoadmapError("'### Objective' must be non-empty")
    return text


def _parse_id_title_heading(raw_line: str, *, context: str) -> tuple[str, str]:
    match = _ID_TITLE_HEADING_RE.match(raw_line)
    if match is None:
        raise InvalidRoadmapError(
            f"malformed {context} heading {raw_line!r} — expected '#### <id> — <title>' "
            "(em dash, one space on each side)"
        )
    item_id, title = match.group(1), match.group(2)
    _validate_id_like(item_id, field_name=f"{context} id")
    return item_id, title


def _parse_dependencies_value(raw: str, *, item_id: str) -> tuple[str, ...]:
    value = raw.strip()
    if value == "none":
        return ()
    if not value:
        raise InvalidRoadmapError(
            f"WorkItem {item_id!r}: 'Dependencies:' must be 'none' or a comma-separated list of WorkItem ids"
        )
    return _parse_comma_list(value, field=f"WorkItem {item_id!r} 'Dependencies:'")


def _parse_work_item_body(
    lines: list[str], *, item_id: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    non_blank_lines = _non_blank(lines)
    if len(non_blank_lines) < 3:
        raise InvalidRoadmapError(
            f"WorkItem {item_id!r}: body must contain 'Dependencies:', 'Capabilities:', and "
            "'Acceptance criteria:' lines, in that order"
        )
    dependencies_line, capabilities_line, acceptance_label, *bullet_lines = non_blank_lines

    dependencies_match = re.match(r"^Dependencies:\s*(.*)$", dependencies_line)
    if dependencies_match is None:
        raise InvalidRoadmapError(
            f"WorkItem {item_id!r}: expected 'Dependencies:' as the first body line, got {dependencies_line!r}"
        )
    dependencies = _parse_dependencies_value(dependencies_match.group(1), item_id=item_id)

    capabilities_match = re.match(r"^Capabilities:\s*(.*)$", capabilities_line)
    if capabilities_match is None:
        raise InvalidRoadmapError(
            f"WorkItem {item_id!r}: expected 'Capabilities:' as the second body line, got {capabilities_line!r}"
        )
    capabilities = _parse_comma_list(capabilities_match.group(1), field=f"WorkItem {item_id!r} 'Capabilities:'")

    if acceptance_label != "Acceptance criteria:":
        raise InvalidRoadmapError(
            f"WorkItem {item_id!r}: expected 'Acceptance criteria:' as the third body line, got {acceptance_label!r}"
        )
    capabilities_index = lines.index(capabilities_line)
    acceptance_index = lines.index(acceptance_label, capabilities_index + 1)
    if not any(not line.strip() for line in lines[capabilities_index + 1 : acceptance_index]):
        raise InvalidRoadmapError(f"WorkItem {item_id!r}: expected a blank line before 'Acceptance criteria:'")
    if not bullet_lines:
        raise InvalidRoadmapError(
            f"WorkItem {item_id!r}: 'Acceptance criteria:' must have at least one '- ' bullet"
        )
    acceptance_criteria = tuple(
        _parse_bullet_line(line, context=f"WorkItem {item_id!r} 'Acceptance criteria:'")
        for line in bullet_lines
    )

    return dependencies, capabilities, acceptance_criteria


def _detect_dependency_cycle(items: Sequence[WorkItemSpec]) -> None:
    """Same fail-closed DFS (white/gray/black) shape as
    ai-dev-orchestrator's own orchestrator.project_config.
    _validate_work_items — mirrored, not imported."""
    by_id = {item.id: item for item in items}
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {item.id: WHITE for item in items}
    path: list[str] = []

    def visit(work_item_id: str) -> None:
        color[work_item_id] = GRAY
        path.append(work_item_id)
        for dependency_id in by_id[work_item_id].dependencies:
            if color[dependency_id] == GRAY:
                cycle_start = path.index(dependency_id)
                cycle = path[cycle_start:] + [dependency_id]
                raise InvalidRoadmapError(f"dependency cycle detected: {' -> '.join(cycle)}")
            if color[dependency_id] == WHITE:
                visit(dependency_id)
        path.pop()
        color[work_item_id] = BLACK

    for item in items:
        if color[item.id] == WHITE:
            visit(item.id)


def _parse_work_items(lines: list[str]) -> tuple[WorkItemSpec, ...]:
    sections = _split_by_heading_level(lines, level=4)
    if not sections:
        raise InvalidRoadmapError("'### WorkItems' must contain at least one '#### <id> — <title>' entry")
    if any(line.strip() for line in lines[:lines.index(sections[0][0])]):
        raise InvalidRoadmapError("'### WorkItems' must begin with a '#### <id> — <title>' entry")

    items: list[WorkItemSpec] = []
    seen_ids: set[str] = set()
    for raw_heading, content in sections:
        item_id, title = _parse_id_title_heading(raw_heading, context="WorkItem")
        if item_id in seen_ids:
            raise InvalidRoadmapError(f"duplicate WorkItem id {item_id!r}")
        seen_ids.add(item_id)
        dependencies, capabilities, acceptance_criteria = _parse_work_item_body(content, item_id=item_id)
        items.append(
            WorkItemSpec(
                id=item_id, title=title, dependencies=dependencies,
                capabilities=capabilities, acceptance_criteria=acceptance_criteria,
            )
        )

    known_ids = {item.id for item in items}
    for item in items:
        for dependency_id in item.dependencies:
            if dependency_id not in known_ids:
                raise InvalidRoadmapError(
                    f"WorkItem {item.id!r} depends on unknown WorkItem id {dependency_id!r}"
                )

    _detect_dependency_cycle(items)
    return tuple(items)


def _parse_qa_body(non_blank_lines: list[str], *, qa_id: str, title: str) -> QACommandSpec:
    if len(non_blank_lines) != 4:
        raise InvalidRoadmapError(
            f"QA {qa_id!r}: body must contain exactly four labeled lines ('Kind:', 'Required:', "
            f"'Timeout:', 'Argv:'), found {len(non_blank_lines)}"
        )
    kind_line, required_line, timeout_line, argv_line = non_blank_lines

    kind_match = re.match(r"^Kind:\s*(.*)$", kind_line)
    if kind_match is None:
        raise InvalidRoadmapError(f"QA {qa_id!r}: expected 'Kind:' as the first body line, got {kind_line!r}")
    kind = kind_match.group(1).strip()
    if kind not in _KNOWN_VALIDATION_KINDS:
        raise InvalidRoadmapError(
            f"QA {qa_id!r}: unknown Kind {kind!r} — must be one of {sorted(_KNOWN_VALIDATION_KINDS)!r}"
        )

    required_match = re.match(r"^Required:\s*(.*)$", required_line)
    if required_match is None:
        raise InvalidRoadmapError(
            f"QA {qa_id!r}: expected 'Required:' as the second body line, got {required_line!r}"
        )
    required_value = required_match.group(1).strip()
    if required_value not in ("true", "false"):
        raise InvalidRoadmapError(f"QA {qa_id!r}: 'Required:' must be 'true' or 'false', got {required_value!r}")
    required = required_value == "true"

    timeout_match = re.match(r"^Timeout:\s*(.*)$", timeout_line)
    if timeout_match is None:
        raise InvalidRoadmapError(
            f"QA {qa_id!r}: expected 'Timeout:' as the third body line, got {timeout_line!r}"
        )
    timeout_value = timeout_match.group(1).strip()
    if not _NUMBER_RE.match(timeout_value):
        raise InvalidRoadmapError(f"QA {qa_id!r}: 'Timeout:' must be a positive number, got {timeout_value!r}")
    timeout_seconds = float(timeout_value)
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise InvalidRoadmapError(f"QA {qa_id!r}: 'Timeout:' must be positive, got {timeout_value!r}")

    argv_match = re.match(r"^Argv:\s*(.*)$", argv_line)
    if argv_match is None:
        raise InvalidRoadmapError(f"QA {qa_id!r}: expected 'Argv:' as the fourth body line, got {argv_line!r}")
    argv = _parse_argv_json(argv_match.group(1), qa_id=qa_id)

    return QACommandSpec(
        id=qa_id, title=title, kind=kind, required=required,
        timeout_seconds=timeout_seconds, argv=argv,
    )


def _parse_argv_json(raw: str, *, qa_id: str) -> tuple[str, ...]:
    """Parsed via the stdlib ``json`` module only — never a shell string,
    never a Python literal eval (docs/PROJECT_CONTRACT.md §3.1)."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InvalidRoadmapError(f"QA {qa_id!r}: 'Argv:' must be valid JSON, got {raw!r} ({exc})") from exc
    if not isinstance(parsed, list):
        raise InvalidRoadmapError(f"QA {qa_id!r}: 'Argv:' must be a JSON array, got {raw!r}")
    for element in parsed:
        if not isinstance(element, str) or not element:
            raise InvalidRoadmapError(
                f"QA {qa_id!r}: 'Argv:' elements must all be non-empty strings, got {element!r}"
            )
    return tuple(parsed)


def _parse_qa_commands(lines: list[str]) -> tuple[QACommandSpec, ...]:
    sections = _split_by_heading_level(lines, level=4)
    if not sections:
        raise InvalidRoadmapError("'### QA', if present, must contain at least one '#### <id> — <title>' entry")
    if any(line.strip() for line in lines[:lines.index(sections[0][0])]):
        raise InvalidRoadmapError("'### QA' must begin with a '#### <id> — <title>' entry")

    commands: list[QACommandSpec] = []
    seen_ids: set[str] = set()
    for raw_heading, content in sections:
        qa_id, title = _parse_id_title_heading(raw_heading, context="QA")
        if qa_id in seen_ids:
            raise InvalidRoadmapError(f"duplicate QA id {qa_id!r}")
        seen_ids.add(qa_id)
        commands.append(_parse_qa_body(_non_blank(content), qa_id=qa_id, title=title))
    return tuple(commands)


def _parse_current_milestone(lines: list[str]) -> CurrentMilestone:
    status, status_index = _parse_status_line(lines)
    remainder = lines[status_index + 1 :]
    sections = _titled_sections(remainder, level=3)
    if sections:
        first_heading = next(i for i, line in enumerate(remainder) if _heading_level(line) and _heading_level(line)[0] == 3)
        if any(line.strip() for line in remainder[:first_heading]):
            raise InvalidRoadmapError("unexpected content between 'Status:' and the first milestone subsection")

    for title, _content in sections:
        if title not in _MILESTONE_SUBSECTION_TITLES:
            raise InvalidRoadmapError(f"unrecognized '### {title}' heading inside 'Current milestone'")

    milestone_id = _parse_id_section(_require_single_section(sections, "ID"))
    objective = _parse_objective_section(_require_single_section(sections, "Objective"))

    acceptance_content = _optional_single_section(sections, "Acceptance criteria")
    acceptance_criteria = (
        _parse_bullets(acceptance_content, context="milestone '### Acceptance criteria'")
        if acceptance_content is not None else ()
    )

    work_items = _parse_work_items(_require_single_section(sections, "WorkItems"))

    qa_content = _optional_single_section(sections, "QA")
    qa_commands = _parse_qa_commands(qa_content) if qa_content is not None else ()

    out_of_scope_content = _optional_single_section(sections, "Out of scope")
    out_of_scope = (
        _parse_bullets(out_of_scope_content, context="'### Out of scope'")
        if out_of_scope_content is not None else ()
    )

    return CurrentMilestone(
        status=status, id=milestone_id, objective=objective, acceptance_criteria=acceptance_criteria,
        work_items=work_items, qa_commands=qa_commands, out_of_scope=out_of_scope,
    )


def parse_roadmap(path: str | Path) -> RoadmapDocument:
    """Fail-closed: any structural problem raises before a single field is
    trusted — never a partially-parsed document."""
    source_path = Path(path).expanduser().resolve()
    try:
        text = source_path.read_text()
    except OSError as exc:
        raise InvalidRoadmapError(f"could not read {source_path}: {exc}") from exc

    lines = text.splitlines()
    top_level_sections = _titled_sections(lines, level=2)

    milestone_matches = _sections_by_title(top_level_sections, "Current milestone")
    if len(milestone_matches) != 1:
        raise InvalidRoadmapError(
            f"document must contain exactly one '## Current milestone' heading, found {len(milestone_matches)}"
        )
    milestone = _parse_current_milestone(milestone_matches[0])

    sources_matches = _sections_by_title(top_level_sections, "Sources")
    if len(sources_matches) > 1:
        raise InvalidRoadmapError("document must contain at most one '## Sources' heading")
    sources = _parse_bullets(sources_matches[0], context="'## Sources'") if sources_matches else ()

    return RoadmapDocument(milestone=milestone, sources=sources, source_path=source_path)
