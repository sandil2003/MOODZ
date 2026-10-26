# Services Package
# Re-exporting public API for backward compatibility

from app.services.fallback_mocks import API_ERROR_WARNING, generate_mock_wellness_response, mock_classify
from app.services.custom_model import CustomModelLLM, get_custom_model
from app.services.session_manager import SessionManager, get_session_manager
from app.services.vector_service import VectorService, get_vector_service, get_vector_service_gemini, VectorServiceGemini
from app.services.crisis_detector import CrisisDetector
from app.services.mood_agent import MoodzAgentOutput, MoodAgentChainV2, get_mood_agent

__all__ = [
    "API_ERROR_WARNING",
    "generate_mock_wellness_response",
    "mock_classify",
    "CustomModelLLM",
    "get_custom_model",
    "SessionManager",
    "get_session_manager",
    "VectorService",
    "get_vector_service",
    "get_vector_service_gemini",
    "VectorServiceGemini",
    "CrisisDetector",
    "MoodzAgentOutput",
    "MoodAgentChainV2",
    "get_mood_agent"
]
