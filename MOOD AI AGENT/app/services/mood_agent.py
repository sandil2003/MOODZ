import os
import re
import json
import httpx
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from uuid import UUID
from pydantic import BaseModel, Field

# LangChain & Google GenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# SQLAlchemy & Database
from sqlalchemy import select, desc
from app.database import AsyncSessionLocal
from app.models import MoodHistory, UserFact
from config import settings

# Modular Imports
from app.services.fallback_mocks import API_ERROR_WARNING, generate_mock_wellness_response, mock_classify
from app.services.custom_model import CustomModelLLM, get_custom_model
from app.services.session_manager import SessionManager, get_session_manager
from app.services.vector_service import VectorService, get_vector_service_gemini
from app.services.crisis_detector import CrisisDetector


class MoodzAgentOutput(BaseModel):
    """
    Combined Pydantic schema for empathetic wellness response and conversation classification.
    """
    response: str = Field(
        description="Your warm, empathetic response message to the user."
    )
    save: bool = Field(
        description="Set to true if the user's message contains meaningful personal facts, goals, or strong emotional shifts. Set to false for casual greetings, small talk, test messages, or generic chatter."
    )
    extracted_facts: List[str] = Field(
        default_factory=list,
        description="Extract new personal facts about the user (e.g. hobbies, family members, jobs, events). Return empty list if no new facts are shared."
    )
    mood: str = Field(
        description="Detected mood/emotion of the user's current message (e.g. happy, sad, anxious, excited, calm, neutral)"
    )


class MoodAgentChainV2:
    """
    Empathetic agent companion consolidated to a single structured LLM call.
    """
    def __init__(
        self,
        session_manager: SessionManager,
        vector_service: VectorService,
        crisis_detector: CrisisDetector,
        model: str = "gpt-4o-mini"
    ):
        self.session_manager = session_manager
        self.vector_service = vector_service
        self.crisis_detector = crisis_detector
        
        if settings.use_custom_model and settings.custom_model_url:
            print(f"Using custom model from: {settings.custom_model_url} (Type: {settings.custom_model_type})")
            if settings.custom_model_type == "openai":
                from langchain_openai import ChatOpenAI
                self.llm = ChatOpenAI(
                    base_url=settings.custom_model_url if "/v1" in settings.custom_model_url else f"{settings.custom_model_url}/v1",
                    api_key="lm-studio",
                    model=model,
                    temperature=settings.custom_model_temperature,
                    max_tokens=settings.custom_model_max_tokens,
                    timeout=settings.custom_model_timeout,
                    model_kwargs={"response_format": {"type": "json_object"}}
                )
            else:
                self.llm = get_custom_model(
                    base_url=settings.custom_model_url,
                    temperature=settings.custom_model_temperature,
                    max_tokens=settings.custom_model_max_tokens,
                    timeout=settings.custom_model_timeout
                )
        else:
            print(f"Using Gemini model: {settings.gemini_model}")
            self.llm = ChatGoogleGenerativeAI(
                model=settings.gemini_model,
                temperature=0.7,
                google_api_key=settings.gemini_api_key,
                model_kwargs={"response_mime_type": "application/json"}
            )
            
    async def invoke(
        self,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        result_holder: Optional[dict] = None
    ) -> str:
        if result_holder is None:
            result_holder = {}
        chunks = []
        has_warning = False
        async for chunk in self.astream(user_id, session_id, user_message, result_holder):
            if chunk == "CRISIS":
                return "I am sorry i cant provide context"
            if chunk == API_ERROR_WARNING:
                has_warning = True
                continue
            chunks.append(chunk)
            
        response_text = "".join(chunks)
        if has_warning:
            return API_ERROR_WARNING + response_text
        return response_text
        
    async def astream(
        self,
        user_id: UUID,
        session_id: UUID,
        user_message: str,
        result_holder: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        if result_holder is None:
            result_holder = {}
            
        try:
            crisis_info = await self.crisis_detector.check_crisis(user_message)
            if crisis_info["score"] == 1.0:
                yield "CRISIS"
                return
                
            # 1. Fetch short-term history from Redis (last 5 messages)
            recent_history = await self.session_manager.get_recent_history(session_id, limit=5)
            formatted_history = []
            for msg in recent_history:
                role = msg.get("role", "user").upper()
                content = msg.get("content", "")
                formatted_history.append(f"{role}: {content}")
            history_str = "\n".join(formatted_history) if formatted_history else "No previous conversation history in this session."

            # 2. Fetch long-term semantic context from Pinecone (top 2 results)
            semantic_results = await self.vector_service.similarity_search(
                query=user_message,
                user_id=user_id,
                k=2
            )
            formatted_semantic = []
            for i, res in enumerate(semantic_results, 1):
                metadata = res.get("metadata", {})
                formatted_semantic.append(f"- [{metadata.get('data_type', 'experience')}] {res['text']} (mood: {metadata.get('mood_label', 'N/A')})")
            semantic_str = "\n".join(formatted_semantic) if formatted_semantic else "No related past experiences found."

            # 3. Fetch structured profile facts & mood history from PostgreSQL (last 3 moods, last 5 facts)
            async with AsyncSessionLocal() as db:
                mood_result = await db.execute(
                    select(MoodHistory)
                    .where(MoodHistory.user_id == user_id)
                    .order_by(desc(MoodHistory.created_at))
                    .limit(3)
                )
                moods = mood_result.scalars().all()
                
                facts_result = await db.execute(
                    select(UserFact)
                    .where(UserFact.user_id == user_id)
                    .order_by(desc(UserFact.created_at))
                    .limit(5)
                )
                facts = facts_result.scalars().all()
            
            profile_parts = []
            if moods:
                profile_parts.append("Recent Mood History:")
                for m in moods:
                    profile_parts.append(f"- {m.sentiment_label} (score: {m.mood_score}/10): {m.summary[:100]}")
            if facts:
                profile_parts.append("Known Facts:")
                for f in facts:
                    profile_parts.append(f"- [{f.category}] {f.fact_text}")
            profile_str = "\n".join(profile_parts) if profile_parts else "No structured user profile available."

            # 4. Construct consolidated prompt
            system_prompt = f"""You are MOODZ, an empathetic AI mental wellness companion.

Your goals:
- Understand and validate the user's emotions.
- Personalize responses using the user's history and profile details.
- Provide warm, non-judgmental support.

=== USER PROFILE ===
{profile_str}

=== LONG-TERM MEMORY (PAST EXPERIENCES) ===
{semantic_str}

=== SHORT-TERM MEMORY (RECENT CHAT) ===
{history_str}

You MUST return a JSON object strictly following this JSON schema:
{{
  "response": "Your warm, empathetic response message to the user.",
  "save": true or false, // Set to true if the user's message contains meaningful personal facts, goals, or strong emotional shifts. Set to false for casual greetings, small talk, test messages, or generic chatter.
  "extracted_facts": ["Fact 1", "Fact 2"], // Extract new personal facts about the user (e.g. hobbies, family members, jobs, events). Return empty list if no new facts are shared.
  "mood": "Detected mood/emotion of the user's current message (e.g. happy, sad, anxious, excited, calm, neutral)"
}}
"""
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Start LLM stream
            accumulated_json = ""
            inside_response = False
            escaped = False
            buffer = ""
            
            async for chunk in self.llm.astream(messages):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                accumulated_json += content
                buffer += content
                
                # Check for "response" start quote
                if not inside_response and "response" not in result_holder:
                    pos = buffer.find('"response"')
                    if pos != -1:
                        colon_pos = buffer.find(':', pos + 10)
                        if colon_pos != -1:
                            start_quote = buffer.find('"', colon_pos + 1)
                            if start_quote != -1:
                                inside_response = True
                                buffer = buffer[start_quote + 1:]
                                
                if inside_response:
                    yield_chunk = ""
                    i = 0
                    closing_quote_idx = -1
                    
                    while i < len(buffer):
                        char = buffer[i]
                        if escaped:
                            if char == 'n':
                                yield_chunk += '\n'
                            elif char == 't':
                                yield_chunk += '\t'
                            else:
                                yield_chunk += char
                            escaped = False
                            i += 1
                        elif char == '\\':
                            escaped = True
                            i += 1
                        elif char == '"':
                            closing_quote_idx = i
                            break
                        else:
                            yield_chunk += char
                            i += 1
                            
                    if yield_chunk:
                        yield yield_chunk
                        
                    if closing_quote_idx != -1:
                        inside_response = False
                        result_holder["response"] = True
                        buffer = ""
                    else:
                        buffer = buffer[i:]
                        
            # Fully parsed JSON after stream completes
            result_holder["raw_json"] = accumulated_json
            try:
                data = json.loads(accumulated_json)
                result_holder["classification"] = {
                    "save": data.get("save", False),
                    "extracted_facts": data.get("extracted_facts", []),
                    "mood": data.get("mood", "neutral")
                }
            except Exception as parse_err:
                print(f"Error parsing raw JSON: {parse_err}. Doing regex fallback.")
                # Regex Fallback
                save = True
                mood = "neutral"
                facts = []
                
                save_match = re.search(r'"save"\s*:\s*(true|false)', accumulated_json, re.I)
                if save_match:
                    save = save_match.group(1).lower() == "true"
                    
                mood_match = re.search(r'"mood"\s*:\s*"([^"]+)"', accumulated_json, re.I)
                if mood_match:
                    mood = mood_match.group(1)
                    
                facts_match = re.search(r'"extracted_facts"\s*:\s*\[(.*?)\]', accumulated_json, re.S)
                if facts_match:
                    facts_str = facts_match.group(1)
                    facts = [f.strip(' "') for f in facts_str.split(',') if f.strip(' "')]
                    
                result_holder["classification"] = {
                    "save": save,
                    "extracted_facts": facts,
                    "mood": mood
                }

        except Exception as e:
            print(f"Error in streaming: {e}. Falling back to offline mock streaming.")
            error_str = str(e).lower()
            is_api_error = any(kw in error_str for kw in ["permission_denied", "leaked", "api key", "401", "connection error", "connecterror", "not found"])
            if is_api_error or settings.use_custom_model:
                yield API_ERROR_WARNING
                mock_response = generate_mock_wellness_response(user_message)
                
                result_holder["response"] = mock_response
                result_holder["classification"] = mock_classify(user_message)
                
                words = mock_response.split()
                for i in range(0, len(words), 3):
                    chunk = " " + " ".join(words[i:i+3])
                    yield chunk
                    await asyncio.sleep(0.05)
            else:
                yield "Error: I apologize, but I encountered an error streaming your response."


_mood_agent: Optional[MoodAgentChainV2] = None


async def get_mood_agent() -> MoodAgentChainV2:
    global _mood_agent
    if _mood_agent is None:
        sm = await get_session_manager()
        vs = get_vector_service_gemini()
        cd = CrisisDetector()
        _mood_agent = MoodAgentChainV2(session_manager=sm, vector_service=vs, crisis_detector=cd)
    return _mood_agent
