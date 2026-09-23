"""WI-M1.3-01: CLI launch argument validation.

An unrecognized CLI launch argument (flag or positional) is rejected
with a clear message and a standard non-zero exit code, never silently
ignored and never a traceback. A normal, no-argument launch is
unchanged. No M2 flag (--resume/-r/--continue/-c) is implemented or
recognized here (see docs/CLI_SPEC.md, ROADMAP.md "M1.3").

Offline only: EngineClient.open()/repl.run() are stubbed so no real
project/provider/Ralph call happens anywhere in this file.
"""

from __future__ import annotations

from aido_code import __main__ as entrypoint


class _FakeEngineClient:
    def __enter__(self) -> "_FakeEngineClient":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False


def test_main_valid_no_argument_launch_is_unchanged(monkeypatch, capsys) -> None:
    monkeypatch.setattr(entrypoint.EngineClient, "open", lambda *a, **k: _FakeEngineClient())
    ran: dict[str, bool] = {}
    monkeypatch.setattr(entrypoint, "run", lambda *a, **k: ran.__setitem__("called", True))

    exit_code = entrypoint.main([])

    assert exit_code == 0
    assert ran.get("called") is True
    assert capsys.readouterr().err == ""


def test_main_rejects_unrecognized_flag(capsys) -> None:
    exit_code = entrypoint.main(["--bogus"])

    assert exit_code != 0
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "--bogus" in err


def test_main_rejects_unrecognized_positional_argument(capsys) -> None:
    exit_code = entrypoint.main(["frobnicate"])

    assert exit_code != 0
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "frobnicate" in err
