"""End-to-end, offline checks for the persisted frontend session boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest

from aido_code import __main__ as entrypoint
from aido_code.project_init import run_init
from aido_code.repl import run
from aido_code.session import SessionStore
from orchestrator.engine import OrchestratorEngine
from orchestrator.worker_selector import WorkerSelector


@pytest.mark.parametrize("bound", [False, True])
def test_process_restart_recovers_only_the_saved_session(
    tmp_path: Path, bound: bool,
) -> None:
    state = tmp_path / "state"
    if bound:
        assert run_init(str(tmp_path), "project") == 0
        cwd = tmp_path / "project"
    else:
        cwd = tmp_path
    env = {**os.environ, "XDG_STATE_HOME": str(state), "PYTHONPATH": os.pathsep.join(sys.path)}

    def launch(*args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, "-m", "aido_code", *args], input="/exit\n",
            cwd=cwd, env=env, capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0, result.stderr
        return result

    launch()
    files = list((state / "aido" / "sessions").glob("*.json"))
    assert len(files) == 1
    original = json.loads(files[0].read_text(encoding="utf-8"))
    assert original["project_path"] == (str(cwd) if bound else None)
    assert set(original) == {
        "schema_version", "session_id", "created_at", "updated_at", "project_path",
    }

    resumed = launch("resume", original["session_id"])
    assert f"Resumed session {original['session_id']}" in resumed.stdout
    persisted = json.loads(files[0].read_text(encoding="utf-8"))
    assert len(list(files[0].parent.glob("*.json"))) == 1
    for field in ("schema_version", "session_id", "created_at", "project_path"):
        assert persisted[field] == original[field]
    assert datetime.fromisoformat(persisted["updated_at"]) > datetime.fromisoformat(original["updated_at"])

    if bound:
        cwd.rename(tmp_path / "moved")
        missing_project = subprocess.run(
            [sys.executable, "-m", "aido_code", "resume", original["session_id"]],
            input="/status\n/exit\n", cwd=tmp_path, env=env,
            capture_output=True, text=True, timeout=15,
        )
        assert missing_project.returncode == 0, missing_project.stderr
        assert f"Resumed session {original['session_id']}" in missing_project.stdout
        assert "bound project is unavailable" in missing_project.stdout
        assert json.loads(files[0].read_text(encoding="utf-8"))["project_path"] == str(cwd)


def test_every_session_selection_path_stays_out_of_the_engine(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    store = SessionStore()
    first = store.create()

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("session selection reached engine, worker selection, or provider")

    monkeypatch.setattr(OrchestratorEngine, "run", forbidden)
    monkeypatch.setattr(OrchestratorEngine, "probe_workers", forbidden)
    monkeypatch.setattr(WorkerSelector, "select", forbidden)
    monkeypatch.setattr("aido_code.engine_client.EngineClient.open", forbidden)
    monkeypatch.setattr("aido_code.engine_client.EngineClient.from_config", forbidden)

    for args, answer in (
        (["resume", first.session_id], "/exit\n"),
        (["resume"], "1\n/exit\n"),
        (["--continue"], "/exit\n"),
        (["-c"], "/exit\n"),
    ):
        monkeypatch.setattr(entrypoint.sys, "stdin", StringIO(answer))
        assert entrypoint.main(args) == 0

    output = StringIO()
    run(StringIO("/resume\n1\n/new\n/exit\n"), output, session=first, session_store=store)
    assert "Resumed session" in output.getvalue()
    assert "Created session" in output.getvalue()


def test_session_errors_do_not_repair_or_replace_corrupt_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setattr(entrypoint.sys, "stdin", StringIO("/exit\n"))
    store = SessionStore()
    session = store.create()
    path = store.directory / f"{session.session_id}.json"
    cases = [
        ("{broken", "malformed JSON"),
        (json.dumps({**vars(session), "schema_version": 99}), "unsupported session schema_version"),
        (json.dumps({k: v for k, v in vars(session).items() if k != "project_path"}), "missing fields"),
    ]
    for payload, message in cases:
        path.write_text(payload, encoding="utf-8")
        assert entrypoint.main(["resume", session.session_id]) == 1
        assert message in capsys.readouterr().err
        assert path.read_text(encoding="utf-8") == payload

    path.unlink()
    assert entrypoint.main(["resume", str(uuid4())]) == 1
    assert "unknown session" in capsys.readouterr().err
    assert entrypoint.main(["resume", "../escape"]) == 1
    assert "invalid session id" in capsys.readouterr().err
