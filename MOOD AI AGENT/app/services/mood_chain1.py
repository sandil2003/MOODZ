from typing import List, Optional
from uuid import UUID
from langchain_core.tools import tool
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.services.session_manager import SessionManager
from app.services.vector_service import VectorService
from app.services.custom_model import get_custom_model
from app.models import MoodHistory, UserFact
from app.database import AsyncSessionLocal
from sqlalchemy import select, desc
from config import settings
from langchain_community.callbacks import get_openai_callback


class MoodAgentChainV2:

    def __init__(
        self,
        session_manager: SessionManager,
        vector_service: VectorService,
        model: str = "gpt-4o-mini"
    ):
        """
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
                openai_api_key=settings.openai_api_key,
                model_kwargs={"stream_options": {"include_usage": True}}
            )
        
        # Build tools and agent
        self.tools = self._build_tools()
        self.agent_executor = self._build_agent()
    
    def _build_tools(self) -> List:
        
        @tool(description="Fetch recent conversation history for the user session.")
        async def fetch_recent_conversation(session_id: str) -> str:
            try:
                history = await self.session_manager.get_recent_history(
                    session_id=UUID(session_id),
                    limit=10
                )
                
                if not history:
                    return "No recent conversation history."
                
                formatted = ["Recent Conversation:"]
                for msg in history:
                    role = msg.get("role", "unknown").upper()
                    content = msg.get("content", "")
                    formatted.append(f"{role}: {content}")
                
                return "\n".join(formatted)
                
            except Exception as e:
                print(f"Error fetching conversation history: {e}")
                return "Error retrieving conversation history."
        
        @tool(description="Fetch relevant past experiences using similarity search.")
        async def fetch_semantic_context(user_id: str, query: str) -> str:
            try:
                results = await self.vector_service.similarity_search(
                    query=query,
                    user_id=UUID(user_id),
                    k=5
                )
                
                if not results:
                    return "No related past experiences found."
                
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
                print(f"Error fetching semantic context: {e}")
                return "Error retrieving past experiences."
        
        @tool(description="Fetch structured user mood history and known user facts.")
        async def fetch_user_profile(user_id: str) -> str:
            try:
                async with AsyncSessionLocal() as db:
                    # Get recent mood history
                    mood_result = await db.execute(
                        select(MoodHistory)
                        .where(MoodHistory.user_id == UUID(user_id))
                        .order_by(desc(MoodHistory.created_at))
                        .limit(5)
                    )
                    moods = mood_result.scalars().all()
                    
                    # Get user facts
                    facts_result = await db.execute(
                        select(UserFact)
                        .where(UserFact.user_id == UUID(user_id))
                        .order_by(desc(UserFact.created_at))
                        .limit(10)
                    )
                    facts = facts_result.scalars().all()
                
                formatted = []
                
                if moods:
                    formatted.append("Recent Mood History:")
                    for mood in moods:
                        formatted.append(
                            f"- {mood.sentiment_label} (score: {mood.mood_score}/10): {mood.summary[:100]}"
                        )
                
                if facts:
                    formatted.append("\nKnown Facts About User:")
                    for fact in facts:
                        formatted.append(f"- [{fact.category}] {fact.fact_text}")
                
                return "\n".join(formatted) or "No structured user data available."
                
            except Exception as e:
                print(f"Error fetching user profile: {e}")
                return "Error retrieving user profile."
        
        return [
            fetch_recent_conversation,
            fetch_semantic_context,
            fetch_user_profile
        ]
    
    def _build_agent(self) -> AgentExecutor:
        
        system_prompt = """You are MOODZ, an empathetic AI mental wellness companion.

Your goals:
- Understand and validate emotions
- Use tools ONLY when helpful (e.g., if you need to remember something specific)
- Personalize responses using history
- Never reveal internal reasoning or technical tool names to the user

Available tools:
- fetch_recent_conversation: Get recent chat history
- fetch_semantic_context: Find similar past experiences  
- fetch_user_profile: Get mood history and user facts
Current User ID: {user_id}
Current Session ID: {session_id}
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            name = "MoodzAgent",
            max_iterations=5,
            handle_parsing_errors=True
        )
    
    async def invoke(
        self,
        user_id: UUID,
        session_id: UUID,
        user_message: str
    ) -> str:
        """
            user_id: User UUID
            session_id: Session UUID
            user_message: User's message

        """
        try:
            await self.session_manager.add_user_message(session_id, user_message)

            existing_history = await self.session_manager.get_recent_history(session_id)
            # Prepare input with context
            input_data = {
                "input": user_message,
                "user_id": str(user_id),
                "session_id": str(session_id),
                "chat_history": existing_history
            }

            with get_openai_callback() as cb:
                result = await self.agent_executor.ainvoke(input_data)

                print(f"Total tokens: {cb.total_tokens}")
                print(f"Prompt tokens: {cb.prompt_tokens}")
                print(f"Completion tokens: {cb.completion_tokens}")
                print(f"Total cost: {cb.total_cost}")
            
            response = result.get("output", "")
            
            # Save to session history
            await self.session_manager.add_assistant_message(session_id, response)
            
            return response
            
        except Exception as e:
            print(f"Error invoking agent: {e}")
            import traceback
            traceback.print_exc()
            return "I apologize, but I encountered an error processing your message. Please try again."


# Global agent instance
_mood_agent: Optional[MoodAgentChainV2] = None


async def get_mood_agent() -> MoodAgentChainV2:

    global _mood_agent
    
    if _mood_agent is None:
        from app.services import get_session_manager, get_vector_service
        
        session_manager = await get_session_manager()
        vector_service = get_vector_service()
        
        _mood_agent = MoodAgentChainV2(
            session_manager=session_manager,
            vector_service=vector_service
        )
    
    return _mood_agent
