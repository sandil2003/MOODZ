from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, Dict, Any, List, Optional
import json
from time import time
import asyncio
from uuid import UUID
from pydantic import BaseModel

from app.database import AsyncSessionLocal, get_db
from app.models import ChatHistory, MoodHistory, UserFact
from app.schemas import (
    ChatRequest, ChatResponse,
    ChatMessageResponse, ChatSessionSummary, ChatSessionDetail,
    MoodHistoryResponse, UserFactResponse
)
from app.services import get_mood_agent, get_session_manager, get_vector_service_gemini, API_ERROR_WARNING
from app.utils import get_chat_logger


def normalize_text(content: Any) -> str:
    """Normalize LLM output into a single plain string for database and frontend."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) 
            for part in content
        )
    return str(content)


# ==========================================
# Router Definitions
# ==========================================
chat_router = APIRouter(prefix="/moods/chat", tags=["chat"])
chat_history_router = APIRouter(prefix="/chat-history", tags=["chat-history"])
history_router = APIRouter(prefix="/history", tags=["history"])
mood_data_router = APIRouter(prefix="/mood-data", tags=["mood-data"])


# WebSocket connection manager for status updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"WebSocket connected for session: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"🔌 WebSocket disconnected for session: {session_id}")
    
    async def send_status(self, session_id: str, status: str):
        print(f"Attempting to send status to session {session_id}: {status}")
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json({
                    "type": "status",
                    "content": status
                })
                print(f"Status sent successfully: {status}")
            except Exception as e:
                print(f"Error sending status: {e}")
        else:
            print(f"No WebSocket connection found for session: {session_id}")


manager = ConnectionManager()


# ==========================================
# Chat Database Helpers
# ==========================================

async def save_chat_message_to_db(
    user_id,
    session_id,
    role: str,
    content: str,
    deep_search: bool = False
):
    try:
        content_str = normalize_text(content)
        print(f"Saving {role} message to database...")
        async with AsyncSessionLocal() as db:
            message = ChatHistory(
                user_id=user_id,
                session_id=session_id,
                role=role,
                content=content_str,
                deep_search=deep_search
            )
            db.add(message)
            await db.commit()
        print(f"{role.capitalize()} message saved to database")
    except Exception as e:
        print(f"Error saving {role} message to database: {e}")
        import traceback
        traceback.print_exc()


async def save_conversation_intelligently(
    user_id,
    session_id,
    message: str,
    response: str,
    classification: Dict[str, Any]
):
    print(f"\n{'='*60}\nSAVE_CONVERSATION_INTELLIGENTLY CALLED\n{'='*60}")
    try:
        if not classification.get("save", False):
            print(f"Skipping database save - classifier said save=False")
            return
            
        vector_service = get_vector_service_gemini()
        
        # Try to save user message and response to Pinecone
        try:
            print(f"Saving user message to Pinecone...")
            await vector_service.add_text(
                user_id=user_id,
                text=message,
                data_type="mood_checkin",
                source="typing",
                mood_label=classification.get("mood", "neutral"),
                context_id=str(session_id)
            )
            
            print(f"Saving assistant response to Pinecone...")
            await vector_service.add_text(
                user_id=user_id,
                text=response,
                data_type="text",
                source="assistant",
                context_id=str(session_id)
            )
        except Exception as pc_err:
            print(f"Warning: Failed to save text to Pinecone / generate embeddings: {pc_err}")
            print("Continuing with PostgreSQL database writes...")
            
        # PostgreSQL writes for facts
        if classification.get("extracted_facts"):
            print(f"Saving {len(classification['extracted_facts'])} facts to PostgreSQL...")
            async with AsyncSessionLocal() as db:
                for fact_text in classification["extracted_facts"]:
                    fact = UserFact(
                        user_id=user_id,
                        fact_text=fact_text,
                        category="auto_extracted",
                        source="conversation_classifier"
                    )
                    db.add(fact)
                await db.commit()
                
            # Try saving facts to Pinecone
            try:
                for fact_text in classification["extracted_facts"]:
                    await vector_service.add_text(
                        user_id=user_id,
                        text=fact_text,
                        data_type="user_fact",
                        source="conversation_classifier",
                        context_id=str(session_id),
                        additional_info={"category": "auto_extracted"}
                    )
            except Exception as pc_err:
                print(f"Warning: Failed to save facts to Pinecone: {pc_err}")
                
        mood_value = classification.get("mood", "neutral")
        if mood_value and mood_value != "neutral":
            print(f"Saving mood '{mood_value}' to PostgreSQL...")
            mood_scores = {
                "happy": 8, "joyful": 9, "excited": 8, "content": 7,
                "sad": 3, "depressed": 2, "down": 3, "melancholic": 3,
                "Anxious": 4, "worried": 4, "nervous": 4, "stressed": 3,
                "angry": 3, "frustrated": 4, "irritated": 4,
                "calm": 7, "peaceful": 8, "relaxed": 7,
                "neutral": 5, "confused": 5, "uncertain": 5,
                "hopeful": 7, "optimistic": 8
            }
            mood_score = mood_scores.get(mood_value, 5)
            async with AsyncSessionLocal() as db:
                mood = MoodHistory(
                    user_id=user_id,
                    mood_score=mood_score,
                    sentiment_label=mood_value,
                    summary=message,
                    session_id=session_id
                )
                db.add(mood)
                await db.commit()
                
        print(f"\n{'='*60}\nSAVE COMPLETED SUCCESSFULLY\n{'='*60}")
    except Exception as e:
        print(f"Error saving conversation intelligently: {e}")
        import traceback
        traceback.print_exc()


# ==========================================
# APIRouter 1: Chat Endpoints
# ==========================================

async def stream_chat_response(
    user_id,
    session_id,
    message: str
) -> AsyncGenerator[str, None]:
    start_time = time()
    try:
        chain = await get_mood_agent()
        session_manager = await get_session_manager()
        
        await session_manager.add_user_message(session_id, message)
        await save_chat_message_to_db(user_id, session_id, "user", message)
        
        full_response = ""
        result_holder = {}
        async for chunk in chain.astream(user_id, session_id, message, result_holder):
            if chunk == "CRISIS":
                print("Crisis detected")
                crisis_message = "I'm really concerned about what you're sharing. Please reach out to a mental health professional or crisis helpline immediately. You can visit your local emergency services."
                await session_manager.add_assistant_message(session_id, crisis_message)
                await save_chat_message_to_db(user_id, session_id, "assistant", crisis_message)
                yield f"data: {json.dumps({'chunk': crisis_message})}\n\n"
                yield f"data: {json.dumps({'done': True, 'session_id': str(session_id), 'crisis_detected': True})}\n\n"
                return
                
            if chunk == API_ERROR_WARNING:
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
                continue
                
            full_response += chunk
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            
        latency = time() - start_time
        clean_response = full_response
        
        await session_manager.add_assistant_message(session_id, clean_response)
        await save_chat_message_to_db(user_id, session_id, "assistant", clean_response)
        
        classification = None
        if "classification" in result_holder:
            classification = result_holder["classification"]
        elif "raw_json" in result_holder:
            try:
                data = json.loads(result_holder["raw_json"])
                classification = {
                    "save": data.get("save", False),
                    "extracted_facts": data.get("extracted_facts", []),
                    "mood": data.get("mood", "neutral")
                }
            except Exception as parse_err:
                print(f"Error parsing raw JSON in route: {parse_err}")
                from app.services import mock_classify
                classification = mock_classify(message)
                
        if not classification:
            classification = {"save": False, "extracted_facts": [], "mood": "neutral"}
            
        logger = get_chat_logger()
        await logger.log_chat(
            user_id=user_id,
            session_id=session_id,
            prompt=message,
            response=clean_response,
            latency=latency,
            metadata={
                "streaming": True,
                "save_to_db": classification["save"],
                "mood": classification["mood"],
                "extracted_facts": classification["extracted_facts"]
            }
        )
        
        completion_data = {
            'done': True,
            'session_id': str(session_id),
            'latency': round(latency, 3),
            'classification': classification
        }
        yield f"data: {json.dumps(completion_data)}\n\n"
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        print(f"Error in stream_chat_response: {e}")
        yield f"data: {json.dumps({'error': error_msg})}\n\n"


@chat_router.post("/stream", response_class=StreamingResponse)
async def chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    classification_result = {}
    
    async def generate():
        nonlocal classification_result
        full_response = ""
        
        async for event in stream_chat_response(
            request.user_id,
            request.session_id,
            request.message
        ):
            if '"chunk"' in event:
                try:
                    data = json.loads(event.replace("data: ", "").strip())
                    if "chunk" in data:
                        if data["chunk"] != API_ERROR_WARNING:
                            full_response += data["chunk"]
                except:
                    pass
            if '"classification"' in event:
                try:
                    data = json.loads(event.replace("data: ", "").strip())
                    if "classification" in data:
                        classification_result = data["classification"]
                except:
                    pass
            yield event
            
        if full_response and classification_result:
            background_tasks.add_task(
                save_conversation_intelligently,
                request.user_id,
                request.session_id,
                request.message,
                full_response,
                classification_result
            )
            
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@chat_router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    start_time = time()
    try:
        chain = await get_mood_agent()
        result_holder = {}
        response = await chain.invoke(
            user_id=request.user_id,
            session_id=request.session_id,
            user_message=request.message,
            result_holder=result_holder
        )
        latency = time() - start_time
        
        await save_chat_message_to_db(request.user_id, request.session_id, "user", request.message)
        
        clean_response = response
        if API_ERROR_WARNING in response:
            clean_response = response.replace(API_ERROR_WARNING, "")
            
        await save_chat_message_to_db(request.user_id, request.session_id, "assistant", clean_response)
        
        classification = None
        if "classification" in result_holder:
            classification = result_holder["classification"]
        elif "raw_json" in result_holder:
            try:
                data = json.loads(result_holder["raw_json"])
                classification = {
                    "save": data.get("save", False),
                    "extracted_facts": data.get("extracted_facts", []),
                    "mood": data.get("mood", "neutral")
                }
            except Exception as parse_err:
                print(f"Error parsing raw JSON in route: {parse_err}")
                from app.services import mock_classify
                classification = mock_classify(request.message)
                
        if not classification:
            classification = {"save": False, "extracted_facts": [], "mood": "neutral"}
            
        background_tasks.add_task(
            save_conversation_intelligently,
            request.user_id,
            request.session_id,
            request.message,
            clean_response,
            classification
        )
        
        logger = get_chat_logger()
        background_tasks.add_task(
            logger.log_chat,
            request.user_id,
            request.session_id,
            request.message,
            clean_response,
            latency,
            {
                "streaming": False,
                "save_to_db": classification["save"],
                "mood": classification["mood"],
                "extracted_facts": classification["extracted_facts"]
            }
        )
        return ChatResponse(
            response=response,
            session_id=str(request.session_id)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.websocket("/ws/status/{session_id}")
async def websocket_status(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        manager.disconnect(session_id)


# ==========================================
# APIRouter 2: Chat History (PostgreSQL) Endpoints
# ==========================================

@chat_history_router.get("/sessions", response_model=List[ChatSessionSummary])
async def get_chat_sessions(
    user_id: UUID = Query(..., description="User ID to fetch sessions for"),
    limit: int = Query(50, ge=1, le=100, description="Max sessions to return"),
    db: AsyncSession = Depends(get_db)
):
    try:
        query = (
            select(
                ChatHistory.session_id,
                func.count(ChatHistory.id).label('message_count'),
                func.max(ChatHistory.timestamp).label('last_message_time')
            )
            .where(ChatHistory.user_id == user_id)
            .group_by(ChatHistory.session_id)
            .order_by(desc('last_message_time'))
            .limit(limit)
        )
        result = await db.execute(query)
        sessions_data = result.all()
        
        session_summaries = []
        for session_data in sessions_data:
            first_msg_query = (
                select(ChatHistory.content)
                .where(
                    ChatHistory.session_id == session_data.session_id,
                    ChatHistory.role == 'user'
                )
                .order_by(ChatHistory.timestamp)
                .limit(1)
            )
            first_msg_result = await db.execute(first_msg_query)
            first_message = first_msg_result.scalar()
            
            first_msg = first_message or "New Chat"
            title = first_msg[:50] + "..." if len(first_msg) > 50 else first_msg
            
            session_summaries.append(
                ChatSessionSummary(
                    session_id=session_data.session_id,
                    title=title,
                    last_message_time=session_data.last_message_time,
                    message_count=session_data.message_count,
                    first_message=first_message
                )
            )
        return session_summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@chat_history_router.get("/sessions/{session_id}", response_model=ChatSessionDetail)
async def get_chat_session(
    session_id: UUID,
    user_id: UUID = Query(..., description="User ID for authorization"),
    db: AsyncSession = Depends(get_db)
):
    try:
        query = (
            select(ChatHistory)
            .where(
                ChatHistory.session_id == session_id,
                ChatHistory.user_id == user_id
            )
            .order_by(ChatHistory.timestamp)
        )
        result = await db.execute(query)
        messages = result.scalars().all()
        
        if not messages:
            raise HTTPException(status_code=404, detail=f"No messages found for session {session_id}")
            
        message_responses = [
            ChatMessageResponse(
                id=msg.id,
                user_id=msg.user_id,
                session_id=msg.session_id,
                role=msg.role,
                content=msg.content,
                timestamp=msg.timestamp,
                deep_search=msg.deep_search
            )
            for msg in messages
        ]
        return ChatSessionDetail(
            session_id=session_id,
            messages=message_responses,
            message_count=len(message_responses)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# APIRouter 3: Short-Term History (Redis) Endpoints
# ==========================================

class SessionHistoryResponse(BaseModel):
    session_id: str
    message_count: int
    messages: List[Dict[str, Any]]
    ttl_seconds: int


@history_router.get("/session/{session_id}", response_model=SessionHistoryResponse)
async def get_redis_session_history(session_id: UUID, limit: int = 50):
    try:
        if limit > 100:
            limit = 100
        session_manager = await get_session_manager()
        
        exists = await session_manager.session_exists(session_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
            
        if limit == -1:
            messages = await session_manager.get_full_history(session_id)
        else:
            messages = await session_manager.get_recent_history(session_id, limit=limit)
            
        message_count = await session_manager.get_session_length(session_id)
        ttl = await session_manager.get_session_ttl(session_id)
        
        return SessionHistoryResponse(
            session_id=str(session_id),
            message_count=message_count,
            messages=messages,
            ttl_seconds=ttl if ttl > 0 else 0
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@history_router.get("/sessions/active")
async def get_active_sessions():
    try:
        session_manager = await get_session_manager()
        sessions = await session_manager.get_active_sessions()
        return {
            "active_sessions": sessions,
            "count": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@history_router.delete("/session/{session_id}")
async def clear_session_history(session_id: UUID):
    try:
        session_manager = await get_session_manager()
        exists = await session_manager.session_exists(session_id)
        if not exists:
            raise HTTPException(status_code=404, detail="Session not found")
            
        success = await session_manager.clear_session(session_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to clear session")
            
        return {
            "message": "Session cleared successfully",
            "session_id": str(session_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# APIRouter 4: Mood Data Endpoints
# ==========================================

from datetime import timedelta

@mood_data_router.get("/mood-history/{user_id}", response_model=List[MoodHistoryResponse])
async def get_mood_history(
    user_id: UUID,
    limit: int = Query(default=50, le=200),
    days: Optional[int] = Query(default=None, description="Filter by last N days")
):
    try:
        async with AsyncSessionLocal() as db:
            query = select(MoodHistory).where(
                MoodHistory.user_id == user_id
            ).order_by(desc(MoodHistory.created_at)).limit(limit)
            
            if days:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                query = query.where(MoodHistory.created_at >= cutoff_date)
                
            result = await db.execute(query)
            mood_entries = result.scalars().all()
            return [
                MoodHistoryResponse(
                    id=entry.id,
                    user_id=entry.user_id,
                    mood_score=entry.mood_score,
                    sentiment_label=entry.sentiment_label,
                    topics=entry.topics if entry.topics else [],
                    summary=entry.summary,
                    session_id=entry.session_id,
                    created_at=entry.created_at
                )
                for entry in mood_entries
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mood_data_router.get("/user-facts/{user_id}", response_model=List[UserFactResponse])
async def get_user_facts(
    user_id: UUID,
    category: Optional[str] = Query(default=None, description="Filter by category"),
    limit: int = Query(default=100, le=500)
):
    try:
        async with AsyncSessionLocal() as db:
            query = select(UserFact).where(
                UserFact.user_id == user_id
            ).order_by(desc(UserFact.created_at)).limit(limit)
            
            if category:
                query = query.where(UserFact.category == category)
                
            result = await db.execute(query)
            facts = result.scalars().all()
            return [
                UserFactResponse(
                    id=fact.id,
                    user_id=fact.user_id,
                    fact_text=fact.fact_text,
                    category=fact.category,
                    source=fact.source,
                    created_at=fact.created_at
                )
                for fact in facts
            ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@mood_data_router.get("/mood-stats/{user_id}")
async def get_mood_stats(user_id: UUID, days: int = Query(default=30)):
    try:
        async with AsyncSessionLocal() as db:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            query = select(MoodHistory).where(
                MoodHistory.user_id == user_id,
                MoodHistory.created_at >= cutoff_date
            ).order_by(MoodHistory.created_at)
            
            result = await db.execute(query)
            mood_entries = result.scalars().all()
            
            if not mood_entries:
                return {
                    "total_entries": 0,
                    "average_mood": None,
                    "highest_mood": None,
                    "lowest_mood": None,
                    "most_common_sentiment": None,
                    "days_analyzed": days
                }
                
            mood_scores = [entry.mood_score for entry in mood_entries]
            sentiments = [entry.sentiment_label for entry in mood_entries if entry.sentiment_label]
            
            most_common_sentiment = None
            if sentiments:
                from collections import Counter
                sentiment_counts = Counter(sentiments)
                most_common_sentiment = sentiment_counts.most_common(1)[0][0]
                
            return {
                "total_entries": len(mood_entries),
                "average_mood": round(sum(mood_scores) / len(mood_scores), 2),
                "highest_mood": max(mood_scores),
                "lowest_mood": min(mood_scores),
                "most_common_sentiment": most_common_sentiment,
                "days_analyzed": days,
                "trend": "improving" if len(mood_scores) > 1 and mood_scores[-1] > mood_scores[0] else "declining" if len(mood_scores) > 1 and mood_scores[-1] < mood_scores[0] else "stable"
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
