from __future__ import annotations
import subprocess, uuid, time, re
from typing import Dict, List

__all__ = ["Session", "get"]

_SESS_CACHE: Dict[str, "Session"] = {}
_PATH_RE = re.compile(r'^/?([\w.\-]+/?)*$')    # quick unix path checker

def get(name: str = "default") -> "Session":
    """Idempotent factory – always returns the same Session object."""
    if name not in _SESS_CACHE:
        _SESS_CACHE[name] = Session(name)
    return _SESS_CACHE[name]


class Session:
    """Tiny wrapper around a persistent tmux session."""
    PROMPTS = (">", "➜", "$")                 # tweak if your shell differs

    def __init__(self, name: str) -> None:
        self.name = name
        self._ensure()

    # -------------- public API ---------------- #

    @property
    def pwd(self) -> str:
        return self.exec_wait("pwd").strip()

    def exec_wait(self, cmd: str, split: bool = False, timeout: int = 60):
        """Run *cmd* synchronously; return str or {"stdout", "stderr"}."""
        pre = self._capture()
        self._send(cmd)

        start, last_seen = time.time(), None
        while time.time() - start < timeout:
            lines = self._capture()
            if lines != last_seen:
                last_seen = lines
            if lines and any(lines[-1].strip().endswith(p) for p in self.PROMPTS):
                break
            time.sleep(0.2)
        else:
            raise TimeoutError(f"{cmd!r} timed out in session {self.name!r}")

        new = lines[len(pre):]
        while new and not new[-1].strip():
            new.pop()
        if new and any(new[-1].strip().endswith(p) for p in self.PROMPTS):
            new.pop()
        if new and cmd.strip() in new[0]:
            new = new[1:]
        out = "\n".join(new).rstrip()
        return {"stdout": out, "stderr": ""} if split else out

    def exec(self, cmd: str) -> None:
        """Fire-and-forget command (non-blocking)."""
        self._send(cmd)

    # slice operator – eg. session[-30:]
    def __getitem__(self, key):
        if isinstance(key, slice) or isinstance(key, int):
            lines = self._capture()
            while lines and not lines[-1].strip():
                lines.pop()
            return lines[key]
        raise TypeError("Session only supports int/slice indexing")

    # -------------- internals ----------------- #

    def _ensure(self):
        if subprocess.run(["tmux", "has-session", "-t", self.name]).returncode:
            subprocess.run(["tmux", "new-session", "-d", "-s", self.name], check=True)
            subprocess.run(["tmux", "send-keys", "-t", self.name, "clear", "C-m"], check=True)

    def _send(self, *keys: str):
        subprocess.run(["tmux", "send-keys", "-t", self.name, *keys, "C-m"], check=True)

    def _capture(self) -> List[str]:
        out = subprocess.check_output(
            ["tmux", "capture-pane", "-pS", "-10000", "-t", self.name],
            text=True
        )
        return out.splitlines()

    @staticmethod
    def _strip_until(lines: List[str], marker: str) -> List[str]:
        try:
            idx = next(i for i, l in enumerate(lines) if marker in l)
            return lines[:idx]
        except StopIteration:
            return lines
