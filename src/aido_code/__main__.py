from __future__ import annotations

import sys

from aido_code.repl import run


def main() -> int:
    run(sys.stdin, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
