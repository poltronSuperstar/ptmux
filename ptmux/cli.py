#!/usr/bin/env python3
"""Minimal CLI – exposes `ptmux` helper commands."""
import subprocess, argparse
from pathlib import Path

def list_sessions() -> None:
    try:
        out = subprocess.check_output(["tmux", "list-sessions", "-F", "#S"], text=True, stderr=subprocess.DEVNULL)
        sessions = sorted(out.strip().splitlines())
        if sessions:
            print("\n".join(sessions))
        else:
            print("(no tmux sessions found)")
    except subprocess.CalledProcessError:
        print("(no tmux server running or no sessions found)")

def attach(name: str) -> None:
    subprocess.run(["tmux", "attach-session", "-t", name])

def kill_session(name: str) -> None:
    """Kill the given tmux session."""
    subprocess.run(["tmux", "kill-session", "-t", name], check=True)

def split(direction: str, size: str | None = None) -> None:
    args = ["tmux", "split-window"]
    if direction in ("u", "up"):
        args += ["-v", "-b"]
    elif direction in ("d", "down"):
        args += ["-v"]
    elif direction in ("l", "left"):
        args += ["-h", "-b"]
    elif direction in ("r", "right"):
        args += ["-h"]
    else:
        raise SystemExit("Usage: ptmux split [u|d|l|r] [size]")
    if size:
        args += ["-l", size]
    subprocess.run(args, check=True)

def save_session(name: str) -> None:
    dir_ = Path.home() / ".tmux-sessions"
    dir_.mkdir(parents=True, exist_ok=True)
    session = subprocess.check_output(
        ["tmux", "display-message", "-p", "#S"], text=True
    ).strip()
    win_idxs = subprocess.check_output(
        ["tmux", "list-windows", "-t", session, "-F", "#{window_index}"], text=True
    )
    lines = []
    for win_idx in win_idxs.strip().splitlines():
        out = subprocess.check_output(
            [
                "tmux",
                "list-panes",
                "-t",
                f"{session}:{win_idx}",
                "-F",
                f"{win_idx}\t#{pane_index}\t#{pane_current_path}",
            ],
            text=True,
        )
        lines.extend(out.strip().splitlines())
    file = dir_ / f"{name}.tmuxsession"
    file.write_text("\n".join(lines) + "\n")
    print(f"Session sauvegardée dans {file}")

def restore_session(name: str) -> None:
    dir_ = Path.home() / ".tmux-sessions"
    file = dir_ / f"{name}.tmuxsession"
    if not file.is_file():
        print(f"Fichier {file} introuvable.")
        return
    subprocess.run(["tmux", "new-session", "-d", "-s", name, "-c", "/"], check=True)
    last_win = -1
    pane_created = False
    for line in file.read_text().splitlines():
        win_idx, pane_idx, cwd = line.split("\t")
        win_idx = int(win_idx)
        if win_idx != last_win:
            if last_win != -1:
                subprocess.run(["tmux", "new-window", "-t", name, "-c", cwd], check=True)
            else:
                subprocess.run(["tmux", "rename-window", "-t", f"{name}:0", f"win{win_idx}"], check=True)
                subprocess.run(["tmux", "send-keys", "-t", f"{name}:0", f"cd '{cwd}'", "C-m"], check=True)
            last_win = win_idx
            pane_created = True
        if pane_created:
            pane_created = False
        else:
            subprocess.run(["tmux", "split-window", "-t", f"{name}:{win_idx}", "-c", cwd], check=True)
    print(f"Session tmux {name} restaurée. Lance : tmux attach -t {name}")

def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="ptmux", description="Tiny tmux helper")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    a = sub.add_parser("attach")
    a.add_argument("name")
    s = sub.add_parser("split")
    s.add_argument("direction")
    s.add_argument("size", nargs="?")
    sv = sub.add_parser("save")
    sv.add_argument("name")
    rs = sub.add_parser("restore")
    rs.add_argument("name")
    k = sub.add_parser("kill")
    k.add_argument("name")
    ns = p.parse_args(argv)

    if ns.cmd == "list":
        list_sessions()
    elif ns.cmd == "attach":
        attach(ns.name)
    elif ns.cmd == "split":
        split(ns.direction, ns.size)
    elif ns.cmd == "save":
        save_session(ns.name)
    elif ns.cmd == "restore":
        restore_session(ns.name)
    elif ns.cmd == "kill":
        kill_session(ns.name)

if __name__ == "__main__":
    main()
