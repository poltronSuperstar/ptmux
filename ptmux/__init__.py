"""Public façade – importables are exposed here."""
from .session import get as get               # idempotent session fetch
from .session import clear as clear           # clear cached sessions
from .session import Session                  # direct use if needed
