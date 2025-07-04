from __future__ import annotations
import subprocess, uuid, time, re
from typing import Dict, List

__all__ = ["Session", "get"]

_SESS_CACHE: Dict[str, "Session"] = {}
_PATH_RE = re.compile(r'^/?([\w.\-]+/?)*$')    # quick unix path checker
_OKI = "_OKI_"

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
        self.last_oki = 0

    # -------------- public API ---------------- #

    @property
    def pwd(self) -> str:
        return self.exec_wait("pwd").strip()
    def extract_ts(self, s):
        
        m = re.match(r"_OKI_(\d+)", s)
        return int(m.group(1)) if m else -1
    
    def find_last_oki(self):
        lines =self._capture()
        for l in lines[::-1]:
            o = self.extract_ts(l)
            if o>0:
                self.last_oki = o
                return o
    
    
    def exec_wait(self, cmd: str, split: bool = False, timeout: int = 60):
        """Run *cmd* synchronously; return str or {"stdout", "stderr"}."""
        pre = self._capture()
        self._send(cmd)
        now = time.time()
        end = now + timeout
        
        success = False
        output_buffer = []
       
        while time.time() < end:
            time.sleep(.1)
            lines = self._capture()
            OKI = 0
            for line in lines[::-1]:
                if not success:
                    OKI = self.extract_ts(line)
                    if OKI> self.last_oki:
                        self.last_oki=OKI
                        success=True
                        continue
                if success:
                    if line == "__IKO__": return output_buffer
                    output_buffer = [line] + output_buffer
        return 'nope'
                
    
                
        
        
        start, last_seen = time.time(), None
        while time.time() - start < timeout:
            lines = self._capture()
            if lines != last_seen:
                last_seen = lines
            if len(lines) >= 2 and lines[-2].strip() == _OKI and any(
                lines[-1].strip().endswith(p) for p in self.PROMPTS
            ):
                break
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
        if new and new[-1].strip() == _OKI:
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
            def is_sep(l:str)->bool:
                return l=='__IKO__' or self.extract_ts(l)>0                
            while lines and (not lines[-1].strip() or is_sep(lines[-1].strip())):
                lines.pop()
            return lines[key]
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
                '''  [ "$BASH_COMMAND" = "clear" ] && return; '''
                '''  ts=$(($(date +%s%N)/1000000)); '''
                '''  echo "_OKI_${ts}"; '''
                '''elif [ -n "$ZSH_VERSION" ]; then '''
                '''  [[ "$PREV_CMD" = "clear" ]] && return; '''
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
            self.find_last_oki()



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
