# ptmux

Tiny, Pythonic wrapper around **tmux** to keep named sessions alive and easy to use  
from scripts *and* the command line.

## Install

```bash
pip install -e .
```

Or, for editable development install:

```bash
pip install -e .
```

Requires `tmux` reachable in `$PATH`.

## Library usage

```python
from ptmux import get   # or: from ptmux import session as get

sess = get("build")

print(sess.pwd)                       # current working dir inside the pane
sess.exec_wait("make test")           # run & wait, combined stdout/stderr
out = sess.exec_wait("ls -1", True)   # ⇒ {"stdout": "...", "stderr": ""}
sess.exec("tail -f log.txt")          # non-blocking
print(sess[-20:])                     # last 20 lines of buffer
```

## CLI

```bash
ptmux list            # show all tmux session names
ptmux attach build    # shortcut for: tmux attach -t build
```

## Development

Run tests with:

```bash
pytest
```

## License

MIT License. See [LICENSE](LICENSE) for details.
