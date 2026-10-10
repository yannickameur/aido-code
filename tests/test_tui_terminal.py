"""Terminal isolation (fd 0 -> /dev/null for workers) and reliable exits."""

from __future__ import annotations

import asyncio
import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import textwrap
import threading
import time
from pathlib import Path

import pytest

from aido_code import repl
from aido_code import tui
from aido_code.i18n import t
from aido_code.repl import ReplState
from aido_code.session import SessionStore
from aido_code.tui import AidoApp, Message, isolated_terminal

from tests.test_tui_live_run import FakeClient, _app, _type, _until

posix_pty = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="pty test is Linux only")


def _texts(app):
    return [str(m.render()) for m in app.query(Message)]


# -- context manager -------------------------------------------------------

def _pty_pair():
    master, slave = pty.openpty()
    return master, slave


@posix_pty
def test_child_sees_dev_null_while_private_fd_keeps_terminal():
    master, slave = _pty_pair()
    saved_fd0 = os.dup(0)
    saved_stdin = sys.__stdin__, sys.stdin
    os.dup2(slave, 0)
    before = termios.tcgetattr(0)
    try:
        with isolated_terminal():
            private = sys.__stdin__.fileno()
            assert private != 0 and not os.get_inheritable(private)
            assert sys.stdin is sys.__stdin__
            assert os.isatty(private) and not os.isatty(0)
            assert os.path.samestat(os.fstat(0), os.stat(os.devnull))
            out = subprocess.run(
                [sys.executable, "-c", "import os,sys;print(os.isatty(0), sys.stdin.read()=='')"],
                capture_output=True, text=True, check=True).stdout
            assert out.strip() == "False True"
            os.write(master, b"x\n")
            assert os.read(private, 1) == b"x"
            attrs = termios.tcgetattr(private)
            attrs[3] &= ~(termios.ECHO | termios.ICANON)
            termios.tcsetattr(private, termios.TCSANOW, attrs)
        assert (sys.__stdin__, sys.stdin) == saved_stdin
        assert os.isatty(0) and os.path.samestat(os.fstat(0), os.fstat(slave))
        assert termios.tcgetattr(0) == before
        with pytest.raises(RuntimeError):
            with isolated_terminal():
                attrs = termios.tcgetattr(sys.__stdin__.fileno())
                attrs[3] &= ~termios.ECHO
                termios.tcsetattr(sys.__stdin__.fileno(), termios.TCSANOW, attrs)
                raise RuntimeError("boom")
        assert (sys.__stdin__, sys.stdin) == saved_stdin
        assert os.isatty(0) and termios.tcgetattr(0) == before
    finally:
        os.dup2(saved_fd0, 0)
        os.close(saved_fd0)
        os.close(master)
        os.close(slave)


# -- reliable exits (pilot) -------------------------------------------------

def test_idle_ctrl_c_double_press_quits(tmp_path, monkeypatch):
    async def go():
        app = _app(tmp_path, monkeypatch, threading.Event())
        async with app.run_test() as pilot:
            await pilot.press("ctrl+c")
            await pilot.pause()
            assert t("run.ctrl_c_again", "en") in _texts(app) and not app._exit
            await pilot.press("ctrl+c")
            await pilot.pause()
            assert app._exit
    asyncio.run(go())


def test_idle_ctrl_c_second_press_after_delay_does_not_quit(tmp_path, monkeypatch):
    async def go():
        app = _app(tmp_path, monkeypatch, threading.Event())
        async with app.run_test() as pilot:
            await pilot.press("ctrl+c")
            app._last_idle_ctrl_c -= 3
            await pilot.press("ctrl+c")
            await pilot.pause()
            assert not app._exit
    asyncio.run(go())


def test_ctrl_c_with_text_clears_without_arming_quit(tmp_path, monkeypatch):
    async def go():
        app = _app(tmp_path, monkeypatch, threading.Event())
        async with app.run_test() as pilot:
            await pilot.press("a", "ctrl+c", "ctrl+c")
            await pilot.pause()
            assert not app._exit
    asyncio.run(go())


@pytest.mark.parametrize("how", ["ctrl+d", "/exit", "/quit", "f10"])
def test_idle_quit_methods(tmp_path, monkeypatch, how):
    async def go():
        app = _app(tmp_path, monkeypatch, threading.Event())
        async with app.run_test() as pilot:
            if how.startswith("/"):
                await _type(pilot, how)
            else:
                await pilot.press(how)
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app._exit
    asyncio.run(go())


@pytest.mark.parametrize("how", ["ctrl+d", "/exit", "/quit", "f10"])
def test_quit_during_run_waits_for_interrupted_engine(tmp_path, monkeypatch, how):
    release = threading.Event()

    async def go():
        app = _app(tmp_path, monkeypatch, release)
        async with app.run_test() as pilot:
            await _type(pilot, "/run")
            await _until(pilot, lambda: FakeClient.instances and FakeClient.instances[0].first_event.is_set())
            if how.startswith("/"):
                await _type(pilot, how)
            else:
                await pilot.press(how)
            assert FakeClient.instances[0].interrupt.is_set()
            await app.workers.wait_for_complete()
            await pilot.pause()
            await pilot.pause()
            assert app._exit
    try:
        asyncio.run(go())
    finally:
        release.set()


def test_help_lists_new_exits(tmp_path, monkeypatch):
    async def go():
        app = _app(tmp_path, monkeypatch, threading.Event())
        async with app.run_test() as pilot:
            await _type(pilot, "/help")
            await app.workers.wait_for_complete()
            await pilot.pause()
            joined = "\n".join(_texts(app))
            for key in ("help.cmd./quit", "help.quit_keys", "help.ctrl_c"):
                assert t(key, "en") in joined
            assert "F10" in joined and "/quit" in joined
    asyncio.run(go())


# -- real pseudo-terminal ---------------------------------------------------

_CHILD = textwrap.dedent('''
    import sys, subprocess, threading, time
    from pathlib import Path
    from types import SimpleNamespace
    from orchestrator.engine import RunResult
    from aido_code import repl
    from aido_code.repl import ReplState
    from aido_code.session import SessionStore
    from aido_code.tui import run_tui

    marks = Path(sys.argv[1])
    WORKER = (
        "import sys, termios\\n"
        "try:\\n"
        "    a = termios.tcgetattr(0); a[3] |= termios.ECHO | termios.ICANON | termios.ISIG\\n"
        "    termios.tcsetattr(0, termios.TCSANOW, a)\\n"
        "except Exception: pass\\n"
        "sys.stdin.read()\\n"
    )

    class Fake:
        def run(self, *, on_event=None, interrupt=None, **_):
            child = subprocess.Popen([sys.executable, "-c", WORKER])
            (marks / "started").write_text("1")
            while not interrupt.is_set():
                time.sleep(0.01)
            (marks / "interrupted").write_text("1")
            child.wait(10)
            raise KeyboardInterrupt
        def execution_times(self): raise RuntimeError("n/a")
        def close(self): pass
        def __enter__(self): return self
        def __exit__(self, *e): pass

    repl.EngineClient.open = classmethod(lambda cls, *a, **k: Fake())
    run_tui(ReplState(store=SessionStore(marks / "sessions")), "en")
    (marks / "exited").write_text("1")
''')


def _wait(pred, master, buf, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        if pred():
            return
        if select.select([master], [], [], 0.05)[0]:
            try:
                buf += os.read(master, 65536)
            except OSError:
                return
    raise AssertionError(f"timeout; output so far: {bytes(buf)[-400:]!r}")


@posix_pty
def test_real_pty_worker_restoring_cooked_mode_does_not_break_raw_mode(tmp_path):
    script = tmp_path / "child.py"
    script.write_text(_CHILD)
    marks = tmp_path / "marks"
    marks.mkdir()
    src = str(Path(tui.__file__).resolve().parents[1])
    pid, master = pty.fork()
    if pid == 0:
        os.environ.update(TERM="xterm-256color", PYTHONPATH=src + os.pathsep + os.environ.get("PYTHONPATH", ""))
        os.execv(sys.executable, [sys.executable, str(script), str(marks)])
    buf = bytearray()
    try:
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 160, 0, 0))
        _wait(lambda: b"/help" in buf or len(buf) > 2000, master, buf)
        time.sleep(0.5)
        os.write(master, b"/run\r")
        _wait(lambda: (marks / "started").exists(), master, buf)
        time.sleep(0.5)
        os.write(master, b"\x1b[<35;153;41M\x1b[<35;150;40Mabc")
        time.sleep(0.5)
        os.write(master, b"\x03")
        _wait(lambda: (marks / "interrupted").exists(), master, buf)
        time.sleep(1)
        os.write(master, b"\x04")
        _wait(lambda: (marks / "exited").exists(), master, buf)
        end = time.time() + 15
        while time.time() < end:
            done, status = os.waitpid(pid, os.WNOHANG)
            if done:
                break
            try:
                if select.select([master], [], [], 0.05)[0]:
                    buf += os.read(master, 65536)
            except OSError:
                pass
        else:
            raise AssertionError("process did not exit")
        assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0
        assert b"^[[<" not in buf
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        os.close(master)
