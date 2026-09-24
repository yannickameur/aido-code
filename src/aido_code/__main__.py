"""AIDO Code's process entry point.

WI-M1.3-01 scope: reject any unrecognized CLI launch argument (flag or
positional) with a clear message and a non-zero exit code, never
silently ignore it. WI-M1.4-06 adds the first real ``sys.argv``
subcommand, ``init <parent-path> <project-name>`` (``docs/CLI_SPEC.md``,
"M1.4") — project bootstrap, entirely provider-free (see
``aido_code.project_init``). A normal, no-argument launch is otherwise
unchanged; no M2 flag (``--resume``/``-r``/``--continue``/``-c``) is
implemented or recognized here yet.
"""

from __future__ import annotations

import sys

from aido_code.engine_client import EngineClient, EngineError
from aido_code.project_init import run_init
from aido_code.repl import run


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
        return run_init(argv[1], argv[2])

    if argv:
        print(
            "Error: unrecognized argument(s): "
            f"{' '.join(argv)}. aido-code only accepts "
            "'init <parent-path> <project-name>' as a CLI launch argument; "
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
