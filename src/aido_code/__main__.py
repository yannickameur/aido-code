"""AIDO Code's process entry point.

WI-M1.3-01 scope: reject any unrecognized CLI launch argument (flag or
positional) with a clear message and a non-zero exit code, never
silently ignore it. No CLI launch flag is implemented yet — M1/M1.1/M1.2
only ever added REPL-level commands/flags (e.g. ``/status --probe``),
never a ``sys.argv`` one — so a normal, no-argument launch is the only
recognized invocation; this is deliberately just the validation
groundwork a future M2 WorkItem builds real flags (``--resume``/``-r``/
``--continue``/``-c``) on top of, not those flags themselves.
"""

from __future__ import annotations

import sys

from aido_code.engine_client import EngineClient, EngineError
from aido_code.repl import run


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv:
        print(
            "Error: unrecognized argument(s): "
            f"{' '.join(argv)}. aido-code does not accept any CLI launch "
            "arguments yet; run it with none to start the REPL.",
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
