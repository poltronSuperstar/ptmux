import pytest
import types
from unittest.mock import patch, MagicMock

import ptmux
from ptmux.session import Session, get

@pytest.fixture
def mock_subprocess():
    with patch("ptmux.session.subprocess") as mock_subp:
        # Default behaviors for subprocess
        mock_subp.run.return_value.returncode = 0
        mock_subp.check_output.return_value = "/home/user\n"
        yield mock_subp

def test_get_returns_same_session(mock_subprocess):
    s1 = get("foo")
    s2 = get("foo")
    assert s1 is s2
    assert isinstance(s1, Session)
    assert s1.name == "foo"

def test_session_pwd(mock_subprocess):
    sess = get("bar")
    # Simulate exec_wait("pwd") returns "/home/user"
    sess.exec_wait = MagicMock(return_value="/home/user")
    assert sess.pwd == "/home/user"

def test_exec_wait_returns_output(mock_subprocess):
    sess = get("baz")
    # Patch _capture to simulate tmux output
    marker = "__PTMUX_marker__"
    lines = ["output line 1", "output line 2", marker]
    with patch.object(sess, "_capture", return_value=lines):
        with patch("uuid.uuid4", return_value=types.SimpleNamespace(hex="marker")):
            out = sess.exec_wait("echo hi")
            assert "output line 1" in out
            assert "output line 2" in out

def test_exec_wait_split(mock_subprocess):
    sess = get("baz2")
    marker = "__PTMUX_marker__"
    lines = ["stdout here", marker]
    with patch.object(sess, "_capture", return_value=lines):
        with patch("uuid.uuid4", return_value=types.SimpleNamespace(hex="marker")):
            out = sess.exec_wait("echo hi", split=True)
            assert isinstance(out, dict)
            assert "stdout" in out
            assert out["stderr"] == ""

def test_exec_nonblocking(mock_subprocess):
    sess = get("qux")
    with patch.object(sess, "_send") as send:
        sess.exec("ls -l")
        send.assert_called_with("ls -l")

def test_session_slice_and_index(mock_subprocess):
    sess = get("slice")
    with patch.object(sess, "_capture", return_value=["a", "b", "c", "d"]):
        assert sess[-2:] == ["c", "d"]
        assert sess[1] == "b"

def test_session_invalid_index(mock_subprocess):
    sess = get("slice2")
    with pytest.raises(TypeError):
        _ = sess["not an int"]

def test_strip_until():
    lines = ["a", "b", "c", "MARK", "d"]
    out = Session._strip_until(lines, "MARK")
    assert out == ["a", "b", "c"]
    # If marker not found, returns all lines
    assert Session._strip_until(["x", "y"], "Z") == ["x", "y"]
