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
from langchain_core.tools import ToolRuntime, tool
from langchain.agents import create_agent

@tool(description="Fetch recent conversation history for the user session")
async def fetch_recent_conversation(
    session_id: str,
    runtime: ToolRuntime
) -> str:
    session_manager = runtime.context.session_manager

    history = await session_manager.get_recent_history(
        session_id=session_id,
        limit=10
    )

    if not history:
        return "No recent conversation history."

    formatted = ["Recent Conversation:"]
    for msg in history:
        formatted.append(f"{msg['role'].upper()}: {msg['content']}")

    return "\n".join(formatted)

@tool(description="Fetch relevant past experiences for the user using similarity search")
async def fetch_semantic_conversation(
    user_id: str,
    user_input: str,
    runtime: ToolRuntime) -> str:

    vector_service = runtime.context.vector_service

    results = vector_service.similarity_search(
        query=user_input,
        user_id = user_id,
        k=5
    )
    if not results:
        return "no related past experiences found"
    
    formatted = ["Relevant past experiences."]
    for r in results:
        formatted.append(
            f"- {r['text']} (Mood: {r['metadata'].get('mood_label')})"
        )
    return "\n".join(formatted)

@tool(description="Fetch structured user mood history and known user facts")
async def fetch_mood_history(
    user_id: str,
    runtime: ToolRuntime
) -> str:
    async with AsyncSessionLocal() as db:
        moods = (await db.execute(
            select(MoodHistory)
            .where(MoodHistory.user_id == user_id)
            .order_by(desc(MoodHistory.created_at))
            .limit(5)
        )).scalars().all()

        facts = (await db.execute(
            select(UserFact)
            .where(UserFact.user_id == user_id)
            .order_by(desc(UserFact.created_at))
            .limit(10)
        )).scalars().all()

    formatted = []

    if moods:
        formatted.append("Recent Mood History:")
        for m in moods:
            formatted.append(f"- {m.sentiment_label} ({m.mood_score}/10)")

    if facts:
        formatted.append("\nKnown User Facts:")
        for f in facts:
            formatted.append(f"- {f.fact_text}")

    return "\n".join(formatted) or "No structured user data."
    
SYSTEM_PROMPT = """
You are MOODZ, an empathetic AI mood companion.

You can:
- Recall recent conversations
- Retrieve past emotional experiences
- Analyze user mood patterns

Use tools when they help you understand the user's emotional state better.
Be warm, empathetic, and actionable.
"""

llm = ChatOpenAI(
    model = "gpt-4o-mini",
    temperature = 0.7,
    openai_api_key = settings.openai_api_key
)

tools = [
    fetch_recent_conversation,
    fetch_semantic_conversation,
    fetch_mood_history
]

agent = create_agent(
    model = llm,
    tools = tools,
    system_prompt = SYSTEM_PROMPT,
)

response = await agent.invoke(
    {
        "messages": [
            {"role": "user", "content": user_message}
        ]
    },
    context={
        "session_manager": session_manager,
        "vector_service": vector_service,
        "user_id": str(user_id),
        "session_id": str(session_id)
    }
)

