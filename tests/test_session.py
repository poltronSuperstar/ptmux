import inspect
import subprocess
from ptmux import get, clear, Session


def cleanup(name: str):
    subprocess.run(["tmux", "kill-session", "-t", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    clear(name)


def test_cache_and_clear():
    cleanup("t1")
    s1 = get("t1")
    s2 = get("t1")
    assert s1 is s2
    clear("t1")
    s3 = get("t1")
    assert s3 is not s1


def test_clear_all():
    cleanup("a")
    cleanup("b")
    a = get("a")
    b = get("b")
    clear()
    assert get("a") is not a
    assert get("b") is not b


def test_exec_wait_output():
    cleanup("exec")
    sess = get("exec")
    out = sess.exec_wait("echo hello")
    assert out.strip() == "hello"


def test_exec_wait_split():
    cleanup("split")
    sess = get("split")
    res = sess.exec_wait("echo hi", split=True)
    assert isinstance(res, dict)
    assert res["stdout"].strip() == "hi"
    assert res["stderr"] == ""


def test_getitem_filters_markers():
    cleanup("getitem")
    sess = get("getitem")
    sess.exec_wait("echo marker-test")
    lines = sess[-5:]
    assert all("__IKO__" not in l and not l.startswith("_OKI_") for l in lines)


def test_exec_wait_default_timeout():
    sig = inspect.signature(Session.exec_wait)
    assert sig.parameters["timeout"].default == 600


def test_start_marker_and_clear_history():
    cleanup("start")
    sess = get("start")
    out = sess.exec_wait("echo first")
    assert out.strip() == "first"
    lines = sess[-5:]
    assert "___STARTS_HERE___" not in "\n".join(lines)
