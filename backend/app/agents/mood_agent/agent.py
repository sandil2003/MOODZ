"""Google ADK discovery entrypoint for the Mood Agent.

Used by the Google ADK CLI ('adk web app/agents/mood_agent') to locate and serve the root agent.
"""

import sys
from pathlib import Path

# Ensure the backend root directory is in sys.path for Google ADK discovery
backend_dir = str(Path(__file__).resolve().parents[3])
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.agents.mood_adk import mood_adk_agent

# Mandatory variable name for Google ADK agent discovery
root_agent = mood_adk_agent
