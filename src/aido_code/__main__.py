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
from aido_code.session import SessionError, SessionStore
from aido_code.session_commands import pick_session, resume_selected
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

    if argv and (argv[0] == "resume" or argv[0] in ("--continue", "-c")):
        if (argv[0] == "resume" and len(argv) > 2) or (argv[0] != "resume" and len(argv) != 1):
            print(f"Error: usage: {prog} resume [session-id] | {prog} --continue", file=sys.stderr)
            return 2
        store = SessionStore()
        try:
            if argv[0] == "resume":
                session_id = argv[1] if len(argv) == 2 else pick_session(store, sys.stdin, sys.stdout)
                if session_id is None:
                    return 0
            else:
                latest = store.latest()
                if latest is None:
                    print("Error: no sessions found to continue.", file=sys.stderr)
                    return 1
                session_id = latest.session_id
            session = resume_selected(store, session_id)
        except (SessionError, OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Resumed session {session.session_id}")
        run(sys.stdin, sys.stdout, session=session, session_store=store)
        return 0

    if argv:
        print(
            "Error: unrecognized argument(s): "
            f"{' '.join(argv)}. {prog} only accepts "
            "'init <parent-path> <project-name>', 'validate', 'run', 'resume', or '--continue'; "
            "run it with none to start the REPL.",
            file=sys.stderr,
        )
        return 2

    project_path = None
    if Path("aido.yaml").is_file():
        try:
            load_project_command_context("aido.yaml")
        except (ProjectManifestError, RoadmapError, ProjectResourcesError,
                WorkerRegistryError, OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        project_path = Path.cwd()
    store = SessionStore()
    try:
        session = store.create(project_path)
    except (SessionError, OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    run(sys.stdin, sys.stdout, session=session, session_store=store)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
