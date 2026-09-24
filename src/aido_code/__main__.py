"""AIDO Code's process entry point."""

from __future__ import annotations

import sys

from aido_code.engine_client import EngineClient, EngineError
from aido_code.engine_plan import EnginePlanError, build_engine_plan
from aido_code.project_init import run_init
from aido_code.project_manifest import ProjectManifestError, load_project_manifest
from aido_code.project_resources import ProjectResourcesError, resolve_project_resources
from aido_code.roadmap import RoadmapError, parse_roadmap
from aido_code.worker_config import load_worker_registry
from aido_code.repl import format_run, run
from orchestrator.worker_registry import WorkerRegistryError


def _project_command(command: str) -> int:
    try:
        manifest = load_project_manifest("aido.yaml")
        roadmap = parse_roadmap(manifest.roadmap)
        resources = resolve_project_resources(manifest, roadmap)
        registry = load_worker_registry()
        if command == "validate":
            print("VALID")
            print(f"Current milestone: {roadmap.milestone.status}")
            print("Executable." if roadmap.milestone.is_executable else "Not executable.")
            return 0
        if not roadmap.milestone.is_executable:
            print("Error: Current milestone is DRAFT. Not executable.", file=sys.stderr)
            return 1
        plan = build_engine_plan(manifest, roadmap, resources)
        with EngineClient.from_config(plan, worker_registry=registry) as client:
            print(format_run(client.run()))
        return 0
    except (ProjectManifestError, RoadmapError, ProjectResourcesError,
            WorkerRegistryError, EnginePlanError, EngineError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if argv and argv[0] == "init":
        if len(argv) != 3:
            print(
                "Error: usage: aido-code init <parent-path> <project-name>",
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
            print(f"Error: usage: aido-code {argv[0]}", file=sys.stderr)
            return 2
        return _project_command(argv[0])

    if argv:
        print(
            "Error: unrecognized argument(s): "
            f"{' '.join(argv)}. aido-code only accepts "
            "'init <parent-path> <project-name>', 'validate', or 'run'; "
            "run it with none to start the REPL.",
            file=sys.stderr,
        )
        return 2

    try:
        with EngineClient.open("aido.yaml"):
            pass
    except EngineError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    run(sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
