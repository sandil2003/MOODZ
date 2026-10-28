import sys
from pathlib import Path

_backend_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)


from .agent import root_agent

__all__ = ["root_agent"]

