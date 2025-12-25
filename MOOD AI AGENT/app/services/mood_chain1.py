from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from app.services.session_manager import SessionManager
from app.services.vector_service import VectorService
from app.services.custom_model import get_custom_model
from app.models import MoodHistory, UserFact
from app.database import AsyncSessionLocal
from sqlalchemy import select, desc
from config import settings


class MoodAgentChain:
    """
    LangChain LCEL chain for mood analysis and recommendations.
    
    Flow:
    1. RunnableParallel: Fetch context from Redis, Pinecone, and PostgreSQL
    2. Combine contexts into a unified prompt
    3. Pass to LLM for generation
    4. Parse and return response
    """
    
    def __init__(
        self,
        session_manager: SessionManager,
        vector_service: VectorService,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize the mood agent chain.
        
        Args:
            session_manager: Redis session manager for short-term memory
            vector_service: Pinecone vector service for semantic search
            model: OpenAI model to use (ignored if using custom model)
        """
        self.session_manager = session_manager
        self.vector_service = vector_service
        
        # Choose between custom model and OpenAI based on configuration
        if settings.use_custom_model and settings.custom_model_url:
            print(f"Using custom model from: {settings.custom_model_url}")
            self.llm = get_custom_model(
                base_url=settings.custom_model_url,
                temperature=settings.custom_model_temperature,
                max_tokens=settings.custom_model_max_tokens,
                timeout=settings.custom_model_timeout
            )
        else:
            print(f"Using OpenAI model: {model}")
            self.llm = ChatOpenAI(
                model=model,
                temperature=0.7,
                openai_api_key=settings.openai_api_key
            )
        
        # Build the chain
        self.chain = self._build_chain()
    
    def _build_chain(self):
        """Build the LCEL chain with parallel context fetching."""
        
        # Define context fetchers
        redis_context = RunnableLambda(self._fetch_redis_context)
        pinecone_context = RunnableLambda(self._fetch_pinecone_context)
        postgres_context = RunnableLambda(self._fetch_postgres_context)
        
        # Parallel context fetching
        parallel_context = RunnableParallel(
            redis=redis_context,
            pinecone=pinecone_context,
            postgres=postgres_context,
            user_message=RunnablePassthrough()
        )
        
        # Combine contexts
        combine_context = RunnableLambda(self._combine_contexts)
        
        # Prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are MOODZ, an empathetic AI mood companion and mental wellness assistant.

Your role:
- Understand and validate the user's emotions
- Provide personalized support based on their history
- Offer actionable suggestions for mood improvement
- Track patterns and provide insights

Context available:
{context}

Guidelines:
- Be warm, empathetic, and non-judgmental
- Reference past conversations and patterns when relevant
- Provide specific, actionable advice
- Ask clarifying questions when needed
- Celebrate improvements and acknowledge challenges"""),
            ("human", "{user_message}")
        ])
        
        # Build the complete chain
        chain = (
            parallel_context
            | combine_context
            | prompt
            | self.llm
            | StrOutputParser()
        )
        
        return chain

    @tool(description="fetch recent conversation history for the user session")
    async def _fetch_redis_context(self, input_data: Dict[str, Any]) -> str:
        """
        Fetch recent conversation history from Redis.
        
        Args:
            input_data: Contains session_id and user_message
            
        Returns:
            str: Formatted conversation history
        """
        try:
            session_id = input_data.get("session_id")
            if not session_id:
                return "No recent conversation history."
            
            # Get last 10 messages
            history = await self.session_manager.get_recent_history(
                session_id=session_id,
                limit=10
            )
            
            if not history:
                return "No recent conversation history."
            
            # Format history
            formatted = ["Recent Conversation:"]
            for msg in history:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                formatted.append(f"{role}: {content}")
            
            return "\n".join(formatted)
            
        except Exception as e:
            print(f"Error fetching Redis context: {e}")
            return "Error retrieving conversation history."
    
    async def _fetch_pinecone_context(self, input_data: Dict[str, Any]) -> str:
        """
        Fetch relevant semantic context from Pinecone.
        
        Args:
            input_data: Contains user_id and user_message
            
        Returns:
            str: Formatted semantic context
        """
        try:
            user_id = input_data.get("user_id")
            user_message = input_data.get("user_message", "")
            
            if not user_id or not user_message:
                return "No semantic context available."
            
            # Search for relevant past entries
            results = await self.vector_service.similarity_search(
                query=user_message,
                user_id=user_id,
                k=5
            )
            
            if not results:
                return "No relevant past experiences found."
            
            # Format results
            formatted = ["Relevant Past Experiences:"]
            for i, result in enumerate(results, 1):
                text = result["text"]
                metadata = result["metadata"]
                mood = metadata.get("mood_label", "N/A")
                data_type = metadata.get("data_type", "unknown")
                timestamp = metadata.get("timestamp", "")
                
                formatted.append(f"\n{i}. [{data_type}] {text}")
                formatted.append(f"   Mood: {mood} | Time: {timestamp}")
            
            return "\n".join(formatted)
            
        except Exception as e:
            print(f"Error fetching Pinecone context: {e}")
            return "Error retrieving semantic context."
    
    async def _fetch_postgres_context(self, input_data: Dict[str, Any]) -> str:
        """
        Fetch structured data from PostgreSQL.
        
        Args:
            input_data: Contains user_id
            
        Returns:
            str: Formatted database context
        """
        try:
            user_id = input_data.get("user_id")
            if not user_id:
                return "No user data available."
            
            async with AsyncSessionLocal() as db:
                # Get recent mood history
                mood_result = await db.execute(
                    select(MoodHistory)
                    .where(MoodHistory.user_id == user_id)
                    .order_by(desc(MoodHistory.created_at))
                    .limit(5)
                )
                recent_moods = mood_result.scalars().all()
                
                # Get user facts
                facts_result = await db.execute(
                    select(UserFact)
                    .where(UserFact.user_id == user_id)
                    .order_by(desc(UserFact.created_at))
                    .limit(10)
                )
                user_facts = facts_result.scalars().all()
                
                # Format context
                formatted = []
                
                # Add mood history
                if recent_moods:
                    formatted.append("Recent Mood History:")
                    for mood in recent_moods:
                        formatted.append(
                            f"- {mood.sentiment_label} (score: {mood.mood_score}/10): {mood.summary[:100]}"
                        )
                
                # Add user facts
                if user_facts:
                    formatted.append("\nKnown Facts About User:")
                    for fact in user_facts:
                        formatted.append(f"- [{fact.category}] {fact.fact_text}")
                
                return "\n".join(formatted) if formatted else "No structured data available."
                
        except Exception as e:
            print(f"Error fetching PostgreSQL context: {e}")
            return "Error retrieving database context."
    
    def _combine_contexts(self, contexts: Dict[str, Any]) -> Dict[str, str]:
        """
        Combine all contexts into a single formatted string.
        
        Args:
            contexts: Dict with redis, pinecone, postgres contexts and user_message
            
        Returns:
            Dict: Combined context and user message
        """
        redis_ctx = contexts.get("redis", "")
        pinecone_ctx = contexts.get("pinecone", "")
        postgres_ctx = contexts.get("postgres", "")
        user_message = contexts.get("user_message", {}).get("user_message", "")
        
        # Combine all contexts
        combined = []
        
        if redis_ctx and redis_ctx != "No recent conversation history.":
            combined.append(f"=== SHORT-TERM MEMORY ===\n{redis_ctx}")
        
        if postgres_ctx and postgres_ctx != "No structured data available.":
            combined.append(f"\n=== USER PROFILE ===\n{postgres_ctx}")
        
        if pinecone_ctx and pinecone_ctx != "No relevant past experiences found.":
            combined.append(f"\n=== LONG-TERM MEMORY ===\n{pinecone_ctx}")
        
        context_str = "\n\n".join(combined) if combined else "No context available."
        
        return {
            "context": context_str,
            "user_message": user_message
        }
    
    async def invoke(
        self,
        user_id: UUID,
        session_id: UUID,
        user_message: str
    ) -> str:
        """
        Invoke the chain with user input.
        
        Args:
            user_id: User UUID
            session_id: Session UUID
            user_message: User's message
            
        Returns:
            str: AI response
        """
        try:
            # Prepare input
            input_data = {
                "user_id": user_id,
                "session_id": session_id,
                "user_message": user_message
            }
            
            # Invoke chain
            response = await self.chain.ainvoke(input_data)
            
            # Save to session history
            await self.session_manager.add_user_message(session_id, user_message)
            await self.session_manager.add_assistant_message(session_id, response)
            
            return response
            
        except Exception as e:
            print(f"Error invoking chain: {e}")
            return "I apologize, but I encountered an error processing your message. Please try again."


# Global chain instance
_mood_chain: Optional[MoodAgentChain] = None


async def get_mood_chain() -> MoodAgentChain:
    """
    Get or create the global mood agent chain.
    
    Returns:
        MoodAgentChain: Chain instance
    """
    global _mood_chain
    
    if _mood_chain is None:
        from app.services import get_session_manager, get_vector_service
        
        session_manager = await get_session_manager()
        vector_service = get_vector_service()
        
        _mood_chain = MoodAgentChain(
            session_manager=session_manager,
            vector_service=vector_service
        )
    
    return _mood_chain
