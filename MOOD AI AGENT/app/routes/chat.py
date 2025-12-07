from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import get_mood_chain, get_session_manager, get_vector_service
from app.models import MoodHistory
from app.database import AsyncSessionLocal
from typing import AsyncGenerator
import json
from time import time
from app.utils import get_chat_logger

router = APIRouter(prefix="/chat", tags=["chat"])


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
    try:
        # Only save if classifier says so
        if not classification.get("save", False):
            print(f"Skipping database save for message: {message[:50]}...")
            return
        
        vector_service = get_vector_service()
        
        # Save user message with mood
        await vector_service.add_text(
            user_id=user_id,
            text=message,
            data_type="mood_checkin",
            source="typing",
            mood_label=classification.get("mood", "neutral"),
            context_id=str(session_id)
        )
        
        # Save assistant response
        await vector_service.add_text(
            user_id=user_id,
            text=response,
            data_type="text",
            source="assistant",
            context_id=str(session_id)
        )
        
        # Save extracted facts to database
        if classification.get("extracted_facts"):
            from app.models import UserFact
            from app.database import AsyncSessionLocal
            
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
            
            print(f"Saved {len(classification['extracted_facts'])} facts to database")
        
        # Save mood to database
        if classification.get("mood") and classification["mood"] != "neutral":
            from app.models import MoodHistory
            from app.database import AsyncSessionLocal
            
            # Map mood to score (simple heuristic)
            mood_scores = {
                "happy": 8, "joyful": 9, "excited": 8, "content": 7,
                "sad": 3, "depressed": 2, "down": 3, "melancholic": 3,
                "anxious": 4, "worried": 4, "nervous": 4, "stressed": 3,
                "angry": 3, "frustrated": 4, "irritated": 4,
                "calm": 7, "peaceful": 8, "relaxed": 7,
                "neutral": 5,
                "confused": 5, "uncertain": 5,
                "hopeful": 7, "optimistic": 8
            }
            
            mood_score = mood_scores.get(classification["mood"], 5)
            
            async with AsyncSessionLocal() as db:
                mood = MoodHistory(
                    user_id=user_id,
                    mood_score=mood_score,
                    sentiment_label=classification["mood"],
                    summary=message,
                    session_id=session_id
                )
                db.add(mood)
                await db.commit()
            
            print(f"Saved mood '{classification['mood']}' to database")
        
    except Exception as e:
        print(f"Error saving conversation: {e}")


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
        
        # Prepare input for streaming
        input_data = {
            "user_id": user_id,
            "session_id": session_id,
            "user_message": message
        }
        
        # Stream response
        full_response = ""
        
        async for chunk in chain.chain.astream(input_data):
            if chunk:
                full_response += chunk
                # Format as Server-Sent Event
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        
        # Calculate latency
        latency = time() - start_time
        
        # Save assistant response to session
        await session_manager.add_assistant_message(session_id, full_response)
        
        # Classify the conversation
        from app.services import get_classifier
        classifier = get_classifier()
        classification = await classifier.classify(user_message)
        
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
        yield f"data: {json.dumps({
            'done': True,
            'session_id': str(session_id),
            'latency': round(latency, 3),
            'classification': classification
        })}\n\n"
        
    except Exception as e:
        error_msg = f"Error: {str(e)}"
        yield f"data: {json.dumps({'error': error_msg})}\n\n"


@router.post("/stream", response_class=StreamingResponse)
async def chat_stream(
    request: ChatRequest,
    background_tasks: BackgroundTasks
):
    """
    Stream chat response in real-time.
    
    Returns Server-Sent Events (SSE) stream with:
    - `data: {"chunk": "text"}` - LLM token chunks
    - `data: {"done": true, "session_id": "..."}` - Completion event
    - `data: {"error": "message"}` - Error event
    
    Background tasks:
    - Save conversation to vector store
    """
    # Create streaming generator
    async def generate():
        full_response = ""
        async for event in stream_chat_response(
            request.user_id,
            request.session_id,
            request.message
        ):
            # Extract chunk for background task
            if '"chunk"' in event:
                try:
                    data = json.loads(event.replace("data: ", "").strip())
                    if "chunk" in data:
                        full_response += data["chunk"]
                except:
                    pass
            
            yield event
        
        # Schedule background task after streaming completes
        if full_response:
            background_tasks.add_task(
                save_to_vector_store,
                request.user_id,
                request.message,
                full_response
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
    - Save conversation to vector store
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
        
        # Schedule background tasks
        background_tasks.add_task(
            save_to_vector_store,
            request.user_id,
            request.message,
            response
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
            {"streaming": False}
        )
        
        return ChatResponse(
            response=response,
            session_id=str(request.session_id)
        )
        
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))
