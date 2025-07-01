import pytest
import types
from unittest.mock import patch, MagicMock, ANY

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
    pre = ["$"]
    final = ["$", "echo hi", "output line 1", "output line 2", "$"]
    with patch.object(sess, "_capture", side_effect=[pre, final, final]):
        with patch.object(sess, "_send") as send:
            out = sess.exec_wait("echo hi")
            send.assert_called_with("echo hi")
            assert out == "output line 1\noutput line 2"

def test_exec_wait_split(mock_subprocess):
    sess = get("baz2")
    pre = ["$"]
    final = ["$", "echo hi", "stdout here", "$"]
    with patch.object(sess, "_capture", side_effect=[pre, final, final]):
        with patch.object(sess, "_send") as send:
            out = sess.exec_wait("echo hi", split=True)
            send.assert_called_with("echo hi")
            assert isinstance(out, dict)
            assert out["stdout"] == "stdout here"
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

def test_trailing_empty_lines_trimmed(mock_subprocess):
    sess = get("trim")
    with patch.object(sess, "_capture", return_value=["x", "y", "", "", ""]):
        assert sess[-10:] == ["x", "y"]

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

def test_ensure_clears_on_create():
    with patch("ptmux.session.subprocess") as sp:
        sp.run.side_effect = [
            types.SimpleNamespace(returncode=1),
            types.SimpleNamespace(returncode=0),
            types.SimpleNamespace(returncode=0),
            types.SimpleNamespace(returncode=0),
        ]
        sp.check_output.return_value = ""
        Session("new")
        sp.run.assert_any_call([
            "tmux",
            "new-session",
            "-d",
            "-s",
            "new",
        ], check=True)
        sp.run.assert_any_call(["tmux", "send-keys", "-t", "new", "clear", "C-m"], check=True)
        sp.run.assert_any_call(["tmux", "send-keys", "-t", "new", ANY, "C-m"], check=True)
