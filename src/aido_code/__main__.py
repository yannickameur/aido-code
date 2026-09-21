from __future__ import annotations

import sys

from aido_code.engine_client import EngineClient, EngineError
from aido_code.repl import run


def main() -> int:
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
