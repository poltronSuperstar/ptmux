#!/usr/bin/env python3
"""Minimal CLI – exposes `ptmux list` and `ptmux attach NAME`."""
import sys, subprocess, argparse
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

def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="ptmux", description="Tiny tmux helper")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    a = sub.add_parser("attach")
    a.add_argument("name")
    ns = p.parse_args(argv)

    if ns.cmd == "list":
        list_sessions()
    elif ns.cmd == "attach":
        attach(ns.name)

if __name__ == "__main__":
    main()
