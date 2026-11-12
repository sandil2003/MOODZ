"""Mood Agent package initialization for Google ADK."""

import sys
from pathlib import Path

# Ensure backend root is on sys.path for Google ADK discovery
backend_dir = str(Path(__file__).resolve().parents[3])
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from .agent import root_agent

__all__ = ["root_agent"]
