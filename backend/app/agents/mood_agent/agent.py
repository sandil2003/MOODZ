import sys
from pathlib import Path

# Ensure the backend root directory is in sys.path for Google ADK discovery
_backend_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.agents.mood_adk import mood_adk_agent


# Mandatory variable name for Google ADK discovery
root_agent = mood_adk_agent

