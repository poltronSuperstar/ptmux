#!/usr/bin/env python3
"""
Demo for ptmux: shows basic usage of the library API.

- Creates a session "demo"
- Prints its working directory
- Runs a command and prints output
- Shows last 5 lines of the buffer
"""

from ptmux import get

def main():
    sess = get("demo1")
    
    if 1:
        c = "ls -la"
        r=sess.exec_wait(c)
        print("\n".join(r))    
        
    print('\n'.join(sess[-20:]))
    quit()
    print(f"Session name: {sess.name}")

    print("Current working directory in tmux session:")
    print(sess.pwd)

    print("\nRunning 'echo Hello from tmux!' in the session...")
    output = sess.exec_wait("echo Hello from tmux!")
    print("Output:")
    print(output)

    print("\nLast 5 lines of the session buffer:")
    for line in sess[-5:]:
        print(line)

    print("\nNow try: ptmux attach demo  # to interact with the session in your terminal")

if __name__ == "__main__":
    main()
