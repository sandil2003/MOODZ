from fastapi import APIRouter, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import get_mood_chain, get_session_manager, get_vector_service
from app.models import MoodHistory, ChatHistory
from app.database import AsyncSessionLocal
from typing import AsyncGenerator, Dict, Any
import json
from time import time
from app.utils import get_chat_logger
import asyncio
from typing import AsyncGenerator, Dict, Any, List, Union


def normalize_text(content: Any) -> str:
    """
    Normalize LLM output (which might be a string, a list of parts, or other types) 
    into a single plain string for database storage and frontend display.
    """
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # Handle list of parts (e.g., from Gemini/LangChain)
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) 
            for part in content
        )
    # Fallback for other types
    return str(content)

router = APIRouter(prefix="/moods/chat", tags=["chat"])

# WebSocket connection manager for status updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"✅ WebSocket connected for session: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            print(f"🔌 WebSocket disconnected for session: {session_id}")
    
    async def send_status(self, session_id: str, status: str):
        print(f"📤 Attempting to send status to session {session_id}: {status}")
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json({
                    "type": "status",
                    "content": status
                })
                print(f"✅ Status sent successfully: {status}")
            except Exception as e:
                print(f"❌ Error sending status: {e}")
        else:
            print(f"⚠️  No WebSocket connection found for session: {session_id}")

manager = ConnectionManager()


async def save_chat_message_to_db(
    user_id,
    session_id,
    role: str,
    content: str,
    deep_search: bool = False
):
    """
    Save a chat message to the database.
    
    Args:
        user_id: User UUID
        session_id: Session UUID
        role: Either 'user' or 'assistant'
        content: Message text (will be normalized to string)
        deep_search: Whether deep search was used
    """
    try:
        # Normalize content to string to avoid DataError (lists/objects)
        content_str = normalize_text(content)
        
        print(f"💾 Saving {role} message to database...")
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
        print(f"✅ {role.capitalize()} message saved to database")
    except Exception as e:
        print(f"❌ Error saving {role} message to database: {e}")
        import traceback
        traceback.print_exc()
        # Don't raise - chat should continue even if DB save fails


async def save_conversation_intelligently(
    user_id,
    session_id,
    message: str,
    response: str,
    classification: Dict[str, Any]
):
    """
    Intelligently save conversation based on classifier decision.
    
    Args:
        user_id: User UUID
        session_id: Session UUID
        message: User message
        response: AI response
        classification: Classification result from classifier
    """
    print(f"\n{'='*60}")
    print(f"SAVE_CONVERSATION_INTELLIGENTLY CALLED")
    print(f"{'='*60}")
    print(f"User ID: {user_id}")
    print(f"Session ID: {session_id}")
    print(f"Message: {message[:100]}...")
    print(f"Classification: {classification}")
    print(f"{'='*60}\n")
    
    try:
        # Only save if classifier says so
        if not classification.get("save", False):
            print(f"❌ Skipping database save - classifier said save=False")
            print(f"   Message: {message[:50]}...")
            return
        
        print(f"✅ Classifier said SAVE=TRUE, proceeding with save...")
        
        vector_service = get_vector_service()
        
        # Save user message with mood
        print(f"📝 Saving user message to Pinecone...")
        await vector_service.add_text(
            user_id=user_id,
            text=message,
            data_type="mood_checkin",
            source="typing",
            mood_label=classification.get("mood", "neutral"),
            context_id=str(session_id)
        )
        print(f"✅ User message saved to Pinecone")
        
        # Save assistant response
        print(f"📝 Saving assistant response to Pinecone...")
        await vector_service.add_text(
            user_id=user_id,
            text=response,
            data_type="text",
            source="assistant",
            context_id=str(session_id)
        )
        print(f"✅ Assistant response saved to Pinecone")
        
        # Save extracted facts to database AND Pinecone
        if classification.get("extracted_facts"):
            print(f"💡 Found {len(classification['extracted_facts'])} facts to save")
            from app.models import UserFact
            from app.database import AsyncSessionLocal
            
            # Save to PostgreSQL
            async with AsyncSessionLocal() as db:
                for fact_text in classification["extracted_facts"]:
                    print(f"   - Saving fact: {fact_text}")
                    fact = UserFact(
                        user_id=user_id,
                        fact_text=fact_text,
                        category="auto_extracted",
                        source="conversation_classifier"
                    )
                    db.add(fact)
                
                await db.commit()
                print(f"✅ Saved {len(classification['extracted_facts'])} facts to PostgreSQL")
            
            # Embed facts to Pinecone
            for fact_text in classification["extracted_facts"]:
                await vector_service.add_text(
                    user_id=user_id,
                    text=fact_text,
                    data_type="user_fact",
                    source="conversation_classifier",
                    context_id=str(session_id),
                    additional_info={"category": "auto_extracted"}
                )
            print(f"✅ Saved facts to Pinecone")
        else:
            print(f"ℹ️  No facts extracted from this message")
        
        # Save mood to database
        mood_value = classification.get("mood", "neutral")
        print(f"📊 Detected mood: {mood_value}")
        
        if mood_value and mood_value != "neutral":
            print(f"💾 Saving mood to PostgreSQL...")
            from app.models import MoodHistory
            from app.database import AsyncSessionLocal
            
            # Map mood to score (simple heuristic)
            mood_scores = {
                "happy": 8, "joyful": 9, "excited": 8, "content": 7,
                "sad": 3, "depressed": 2, "down": 3, "melancholic": 3,
                "Anxious": 4, "worried": 4, "nervous": 4, "stressed": 3,
                "angry": 3, "frustrated": 4, "irritated": 4,
                "calm": 7, "peaceful": 8, "relaxed": 7,
                "neutral": 5,
                "confused": 5, "uncertain": 5,
                "hopeful": 7, "optimistic": 8
            }
            
            mood_score = mood_scores.get(mood_value, 5)
            print(f"   Mood score: {mood_score}/10")
            
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
            
            print(f"✅ Saved mood '{mood_value}' (score: {mood_score}) to PostgreSQL")
        else:
            print(f"⚠️  Mood is neutral - NOT saving to database")
            print(f"   (Neutral moods are not saved to reduce database bloat)")
        
        print(f"\n{'='*60}")
        print(f"SAVE COMPLETED SUCCESSFULLY")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ ERROR SAVING CONVERSATION")
        print(f"{'='*60}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")


async def stream_chat_response(
    user_id,
    session_id,
    message: str
) -> AsyncGenerator[str, None]:
    """
    Stream chat response with LLM tokens.
    
    Yields:
        str: Server-Sent Events formatted chunks
    """
    
    start_time = time()
    
    try:
        # Get the chain
        chain = await get_mood_chain()
        session_manager = await get_session_manager()
        
        # Save user message to session
        await session_manager.add_user_message(session_id, message)
        
        # Save user message to database
        await save_chat_message_to_db(user_id, session_id, "user", message)
        
        # CRISIS DETECTION - Check before processing
        from app.services.crisis_detection import CrisisDetector
        crisis_detector = CrisisDetector()
        crisis_info = await crisis_detector.check_crisis(message)
        
        if crisis_info["score"] == 1.0:
            print("crisis detected")
            crisis_message = "I'm really concerned about what you're sharing. Please reach out to a mental health professional or crisis helpline immediately. You can visit your local emergency services."
            
            await session_manager.add_assistant_message(session_id, crisis_message)
            await save_chat_message_to_db(user_id, session_id, "assistant", crisis_message)

            yield f"data: {json.dumps({'chunk': crisis_message})}\n\n"
            yield f"data: {json.dumps({'done': True, 'session_id': str(session_id), 'crisis_detected': True})}\n\n"
            return
        
        # Prepare input for agent
        input_data = {
            "input": message,
            "user_id": str(user_id),
            "session_id": str(session_id),
            "chat_history": []
        }
        
        # Stream response from agent
        full_response = ""
        
        async for event in chain.agent_executor.astream(input_data):
            # Extract the output from agent events
            if "output" in event:
                chunk = normalize_text(event["output"])
                full_response = chunk
                # Stream the complete output
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        
        # Calculate latency
        latency = time() - start_time
        
        # Save assistant response to session
        await session_manager.add_assistant_message(session_id, full_response)
        
        # Save assistant response to database
        await save_chat_message_to_db(user_id, session_id, "assistant", full_response)
        
        # Classify the conversation
        from app.services import get_classifier
        classifier = get_classifier()
        classification = await classifier.classify(message)
        
        # Log to JSONL file (always log)
        logger = get_chat_logger()
        await logger.log_chat(
            user_id=user_id,
            session_id=session_id,
            prompt=message,
            response=full_response,
            latency=latency,
            metadata={
                "streaming": True,
                "save_to_db": classification["save"],
                "mood": classification["mood"],
                "extracted_facts": classification["extracted_facts"]
            }
        )
        
        # Send completion event with classification
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
        import traceback
        traceback.print_exc()
        yield f"data: {json.dumps({'error': error_msg})}\n\n"


@router.post("/stream", response_class=StreamingResponse)
async def chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """
    Stream chat response in real-time.
    
    Supports both regular chat and deep search modes.
    Deep search mode: NO database saves (PostgreSQL, Pinecone, Redis)
    
    Returns Server-Sent Events (SSE) stream with:
    - `data: {"chunk": "text"}` - LLM token chunks
    - `data: {"done": true, "session_id": "..."}` - Completion event
    - `data: {"error": "message"}` - Error event
    """
    # Create streaming generator
    classification_result = {}
    
    async def generate():
        nonlocal classification_result
        full_response = ""
        
        # Check if deep search is enabled
        if request.deep_search:
            # Use deep search - NO database saves
            async for event in stream_deep_search_response(
                request.user_id,
                request.session_id,
                request.message
            ):
                yield event
            # Exit early - no classification, no database save for deep search
            return
        
        # Regular chat flow
        async for event in stream_chat_response(
            request.user_id,
            request.session_id,
            request.message
        ):
            # Extract chunk and classification
            if '"chunk"' in event:
                try:
                    data = json.loads(event.replace("data: ", "").strip())
                    if "chunk" in data:
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
        
        # Schedule background task after streaming completes (ONLY for regular chat)
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
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """
    Non-streaming chat endpoint.
    
    Returns complete response after LLM finishes generation.
    
    Background tasks:
    - Classify conversation
    - Intelligently save to database based on classifier
    - Log conversation to JSONL file
    """
    
    start_time = time()
    
    try:
        # Get the chain
        chain = await get_mood_chain()
        
        # Get response
        response = await chain.invoke(
            user_id=request.user_id,
            session_id=request.session_id,
            user_message=request.message
        )
        
        # Calculate latency
        latency = time() - start_time
        
        # Save messages to database
        await save_chat_message_to_db(request.user_id, request.session_id, "user", request.message)
        await save_chat_message_to_db(request.user_id, request.session_id, "assistant", response)
        
        # Classify the conversation
        from app.services import get_classifier
        classifier = get_classifier()
        classification = await classifier.classify(request.message)
        
        # Schedule background tasks
        background_tasks.add_task(
            save_conversation_intelligently,
            request.user_id,
            request.session_id,
            request.message,
            response,
            classification
        )
        
        # Log to JSONL file
        logger = get_chat_logger()
        background_tasks.add_task(
            logger.log_chat,
            request.user_id,
            request.session_id,
            request.message,
            response,
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
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for status updates
@router.websocket("/ws/status/{session_id}")
async def websocket_status(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
    except WebSocketDisconnect:
        manager.disconnect(session_id)


async def stream_deep_search_response(user_id, session_id, message: str) -> AsyncGenerator[str, None]:
    """Stream deep search response with status updates via WebSocket."""
    print(f"\n{'='*60}")
    print(f"🔍 DEEP SEARCH STREAMING - Starting")
    print(f"Session: {session_id}")
    print(f"Message: {message}")
    print(f"{'='*60}\n")
    
    try:
        print("📦 Importing DeepResearchAgent...")
        from app.services.deep_search import DeepResearchAgent
        print("✅ Import successful")
        
        async def send_status(status: str):
            print(f"📤 Sending status: {status}")
            await manager.send_status(str(session_id), status)
        
        print("🤖 Initializing DeepResearchAgent...")
        agent = DeepResearchAgent(status_callback=send_status)
        print("✅ Agent initialized")
        
        # Save user message to database
        await save_chat_message_to_db(user_id, session_id, "user", message, deep_search=True)
        
        print("🚀 Running deep search...")
        result = await agent.run(message)
        print(f"✅ Deep search completed. Result keys: {result.keys()}")
        
        report = result.get("report", "No results found.")
        print(f"📄 Report length: {len(report)} characters")
        
        if "errors" in result:
            print(f"⚠️  Errors in result: {result['errors']}")
        
        # Stream the report
        words = report.split()
        print(f"📝 Streaming {len(words)} words...")
        for i in range(0, len(words), 3):
            chunk = " " + " ".join(words[i:i+3])
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            await asyncio.sleep(0.05)
        
        print("✅ Streaming completed")
        
        # Save assistant response to database
        await save_chat_message_to_db(user_id, session_id, "assistant", report, deep_search=True)
        
        yield f"data: {json.dumps({'done': True, 'session_id': str(session_id), 'deep_search': True})}\n\n"
        
    except Exception as e:
        error_msg = f"Deep search error: {str(e)}"
        print(f"\n{'='*60}")
        print(f"❌ DEEP SEARCH ERROR")
        print(f"{'='*60}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        yield f"data: {json.dumps({'error': error_msg})}\n\n"

