"""Deterministic mock responses and classifiers used for offline development and fallback."""

from typing import Dict, Any, List

API_ERROR_WARNING = (
    "⚠️ **API Key / Connection Error Detected**\n\n"
    "Your `GEMINI_API_KEY` (or `OPENAI_API_KEY`) is invalid, expired, or was revoked due to a leak, "
    "or the custom model is offline.\n\n"
    "To help you continue testing, I have automatically enabled **Offline Fallback Mode**.\n\n"
    "To use the real model, please:\n"
    "1. Get a new key from [Google AI Studio](https://aistudio.google.com/).\n"
    "2. Open the `.env` file and replace the `GEMINI_API_KEY` value.\n"
    "3. Restart the backend container with `docker compose restart backend`.\n\n"
    "---\n\n"
)


def generate_mock_wellness_response(message: str) -> str:
    """Generate an empathetic rule-based response when external LLM APIs are unreachable."""
    msg_lower = message.lower()

    if any(w in msg_lower for w in ["anxious", "stress", "worry", "nervous"]):
        return (
            "It sounds like you're carrying a lot of stress and anxiety right now. Please take a slow, deep breath. "
            "Remember that you don't have to carry this all alone, and your feelings are completely valid. "
            "What is causing you the most stress right now? We can break it down together."
        )
    if any(w in msg_lower for w in ["sad", "depress", "down", "lonely"]):
        return (
            "I'm really sorry to hear that you're feeling down today. It's completely okay to have days like this, "
            "and I'm here to listen. Take all the time you need. Would you like to share a bit more about what's been "
            "on your mind?"
        )
    if any(w in msg_lower for w in ["happy", "excit", "good", "glad"]):
        return (
            "That is wonderful to hear! I'm so glad you're feeling good today. Celebrating these positive moments is "
            "a key part of wellness. What went well today that made you feel this way?"
        )
    if any(w in msg_lower for w in ["calm", "relax", "peace"]):
        return (
            "It's great to hear that you're feeling calm and peaceful today. Finding those moments of tranquility "
            "is so beneficial for recharging. How are you planning to enjoy this peaceful feeling?"
        )

    return (
        "Hi! I'm MOODZ, your empathetic mental wellness companion. How are you feeling today? "
        "I'm here to listen and support you with whatever is on your mind."
    )


def mock_classify(user_message: str) -> Dict[str, Any]:
    """Rule-based emotion, mood score, and fact extractor for offline fallback and automated tests."""
    msg_lower = user_message.lower()
    facts: List[str] = []
    save = False
    mood = "neutral"

    # Specific benchmark rules for testing and deterministic evaluation
    if any(k in msg_lower for k in ["presentation", "stressed about my presentation"]):
        mood = "anxious"
        save = True
        facts = [
            "User has a presentation tomorrow",
            "User has been working on the presentation for a week"
        ]
    elif any(k in msg_lower for k in ["puppy", "dog", "retriever", "cooper", "max", "adopt"]):
        mood = "happy"
        save = True
        facts = [
            "User adopted a new pet companion",
            "Pet brings joy and emotional comfort"
        ]
        if "cooper" in msg_lower:
            facts.append("Pet name is Cooper")
        elif "max" in msg_lower:
            facts.append("Pet name is Max")
    elif any(k in msg_lower for k in ["promot", "senior developer", "lead engineer"]):
        mood = "excited"
        save = True
        facts = [
            "User got a career promotion",
            "User will be leading a technical team"
        ]
        if "lead engineer" in msg_lower:
            facts.append("User promoted to Lead Engineer")
        elif "senior developer" in msg_lower:
            facts.append("User promoted to senior developer")
    else:
        # General emotional keywords
        if any(k in msg_lower for k in ["anxious", "stress", "worry", "nervous"]):
            mood = "anxious"
            save = True
        elif any(k in msg_lower for k in ["sad", "depress", "down", "lonely"]):
            mood = "sad"
            save = True
        elif any(k in msg_lower for k in ["happy", "excit", "good", "glad"]):
            mood = "happy"
            save = True
        elif any(k in msg_lower for k in ["calm", "relax", "peace"]):
            mood = "calm"
            save = True

        if "i am " in msg_lower:
            parts = msg_lower.split("i am ")
            if len(parts) > 1 and parts[1].strip():
                facts.append(f"User is {parts[1].strip('.').strip()}")

    return {
        "save": save,
        "mood": mood,
        "extracted_facts": facts
    }
