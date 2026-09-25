"""AIDO Code's process entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from aido_code.engine_client import EngineClient, EngineError
from aido_code.engine_plan import EnginePlanError, build_engine_plan
from aido_code.project_command import load_project_command_context
from aido_code.project_init import run_init
from aido_code.project_manifest import ProjectManifestError
from aido_code.project_resources import ProjectResourcesError
from aido_code.roadmap import RoadmapError
from aido_code.repl import format_run, run
from orchestrator.worker_registry import WorkerRegistryError


def _project_command(command: str) -> int:
    try:
        context = load_project_command_context("aido.yaml")
        if command == "validate":
            print("VALID")
            print(f"Current milestone: {context.roadmap.milestone.status}")
            print("Executable." if context.roadmap.milestone.is_executable else "Not executable.")
            return 0
        if not context.roadmap.milestone.is_executable:
            print("Error: Current milestone is DRAFT. Not executable.", file=sys.stderr)
            return 1
        plan = build_engine_plan(context.manifest, context.roadmap, context.resources)
        with EngineClient.from_config(plan, worker_registry=context.worker_registry) as client:
            print(format_run(client.run()))
        return 0
    except (ProjectManifestError, RoadmapError, ProjectResourcesError,
            WorkerRegistryError, EnginePlanError, EngineError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def _program_name() -> str:
    return Path(sys.argv[0]).name or "aido"


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    prog = _program_name()

    if argv and argv[0] == "init":
        if len(argv) != 3:
            print(
                f"Error: usage: {prog} init <parent-path> <project-name>",
                file=sys.stderr,
            )
            return 2
        try:
            return run_init(argv[1], argv[2])
        except (OSError, ValueError) as exc:
            print(f"Error: could not initialize project: {exc}", file=sys.stderr)
            return 1

    if argv and argv[0] in ("validate", "run"):
        if len(argv) != 1:
            print(f"Error: usage: {prog} {argv[0]}", file=sys.stderr)
            return 2
        return _project_command(argv[0])

    if argv:
        print(
            "Error: unrecognized argument(s): "
            f"{' '.join(argv)}. {prog} only accepts "
            "'init <parent-path> <project-name>', 'validate', or 'run'; "
            "run it with none to start the REPL.",
            file=sys.stderr,
        )
        return 2

    try:
        load_project_command_context("aido.yaml")
    except (ProjectManifestError, RoadmapError, ProjectResourcesError,
            WorkerRegistryError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    run(sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
