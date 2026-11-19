"""Global pytest configuration for MOODZ backend."""

import sys
import os
from dotenv import load_dotenv

backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

env_path = os.path.join(backend_dir, ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)
