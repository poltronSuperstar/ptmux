from __future__ import annotations
import subprocess, time
from typing import Dict, List

__all__ = ["Session", "get", "clear"]

_START_MARK = "___STARTS_HERE___"

_SESS_CACHE: Dict[str, "Session"] = {}

def get(name: str = "default") -> "Session":
    """Idempotent factory – always returns the same ``Session`` object."""
    if name not in _SESS_CACHE:
        _SESS_CACHE[name] = Session(name)
    return _SESS_CACHE[name]


def clear(name: str | None = None) -> None:
    """Clear cached sessions.

    If *name* is ``None`` all cached sessions are removed, otherwise only the
    session with the given name is discarded.
    """
    if name is None:
        _SESS_CACHE.clear()
    else:
        _SESS_CACHE.pop(name, None)


class Session:
    """Tiny wrapper around a persistent tmux session."""
    PROMPTS = (">", "➜", "$", "#")             # tweak if your shell differs

    def __init__(self, name: str) -> None:
        self.name = name
        self.start_marker = _START_MARK
        self._ensure()

    # -------------- public API ---------------- #

    @property
    def pwd(self) -> str:
        return self.exec_wait("pwd").strip()
    def exec_wait(self, cmd: str, split: bool = False, timeout: int = 600):
        """Run *cmd* synchronously and return its output."""
        pre = self._capture()
        self._send(cmd)
        start = time.time()

        while time.time() - start < timeout:
            lines = self._capture()
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

        new = [
            l for l in new
            if l.strip()
            and self.start_marker not in l
            and l.strip() != "__IKO__"
            and not l.strip().startswith("_OKI_")
        ]

        out = "\n".join(new).rstrip()
        return {"stdout": out, "stderr": ""} if split else out

    def exec(self, cmd: str) -> None:
        """Fire-and-forget command (non-blocking)."""
        self._send(cmd)

    # slice operator – eg. session[-30:]
    def __getitem__(self, key):
        if isinstance(key, slice) or isinstance(key, int):
            lines = self._capture()
            if self.start_marker:
                try:
                    idx = next(i for i, l in enumerate(lines) if self.start_marker in l)
                    lines = lines[idx + 1 :]
                except StopIteration:
                    pass
            filtered = [
                l for l in lines
                if l.strip()
                and self.start_marker not in l
                and l.strip() != "__IKO__"
                and not l.strip().startswith("_OKI_")
            ]
            return filtered[key]
        raise TypeError("Session only supports int/slice indexing")

    # -------------- internals ----------------- #

    def _ensure(self):
        if subprocess.run(["tmux", "has-session", "-t", self.name]).returncode:
            subprocess.run([
                "tmux",
                "new-session",
                "-d",
                "-s",
                self.name,
            ], check=True)
            
            subprocess.run(["tmux", "send-keys", "-t", self.name, "clear", "C-m"], check=True)
            time.sleep(.1)
            hook = (
                '''_iko_before_command() { echo "__IKO__"; }; '''
                '''_oki_after_command() { '''
                '''if [ -n "$BASH_VERSION" ]; then '''
                '''  if [ "$BASH_COMMAND" = "clear" ]; then tmux clear-history -t $TMUX_PANE >/dev/null 2>&1; return; fi; '''
                '''  ts=$(($(date +%s%N)/1000000)); '''
                '''  echo "_OKI_${ts}"; '''
                '''elif [ -n "$ZSH_VERSION" ]; then '''
                '''  if [[ "$PREV_CMD" = "clear" ]]; then tmux clear-history -t $TMUX_PANE >/dev/null 2>&1; return; fi; '''
                '''  ts=$(($(date +%s%N)/1000000)); '''
                '''  echo "_OKI_${ts}"; '''
                '''fi; '''
                '''}; '''
                '''if [ -n "$ZSH_VERSION" ]; then '''
                '''  preexec_functions+=(_iko_before_command); '''
                '''  precmd() { PREV_CMD=$history[$HISTCMD] }; '''
                '''  autoload -Uz add-zsh-hook; '''
                '''  add-zsh-hook preexec precmd; '''
                '''  add-zsh-hook precmd _oki_after_command; '''
                '''elif [ -n "$BASH_VERSION" ]; then '''
                '''  trap _iko_before_command DEBUG; '''
                '''  PROMPT_COMMAND="_oki_after_command${PROMPT_COMMAND:+; $PROMPT_COMMAND}"; '''
                '''fi'''
            )
            subprocess.run(["tmux", "send-keys", "-t", self.name, hook, "C-m"], check=True)

            time.sleep(.1)
            subprocess.run(["tmux", "send-keys", "-t", self.name, "clear", "C-m"], check=True)
            subprocess.run(["tmux", "clear-history", "-t", self.name], check=True)
            subprocess.run(["tmux", "send-keys", "-t", self.name, f"echo {_START_MARK}", "C-m"], check=True)
            time.sleep(.1)



    def _send(self, *keys: str):
        subprocess.run(["tmux", "send-keys", "-t", self.name, *keys, "C-m"], check=True)

    def _capture(self) -> List[str]:
        out = subprocess.check_output(
            ["tmux", "capture-pane", "-pS", "-10000", "-t", self.name],
            text=True
        )
        lines = out.splitlines()
        while len(lines)and lines[-1].strip() == '':
            lines.pop()
        return lines
            

    @staticmethod
    def _strip_until(lines: List[str], marker: str) -> List[str]:
        try:
            idx = next(i for i, l in enumerate(lines) if marker in l)
            return lines[:idx]
        except StopIteration:
            return lines
