"""Services package initialization."""

from app.services.session_manager import SessionManager, get_session_manager
from app.services.vector_service import VectorService, get_vector_service
# Use agent-based implementation (mood_chain1.py) with backward-compatible aliases
from app.services.mood_chain1 import MoodAgentChainV2 as MoodAgentChain, get_mood_agent as get_mood_chain
from app.services.classifier import ConversationClassifier, get_classifier

__all__ = [
    "SessionManager", "get_session_manager",
    "VectorService", "get_vector_service",
    "MoodAgentChain", "get_mood_chain",
    "ConversationClassifier", "get_classifier"
]
