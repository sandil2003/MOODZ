from fastapi import APIRouter, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import get_mood_chain, get_session_manager, get_vector_service
from app.models import MoodHistory
from app.database import AsyncSessionLocal
from typing import AsyncGenerator
import json

router = APIRouter(prefix="/chat", tags=["chat"])


async def save_to_vector_store(user_id, message: str, response: str):
    """Background task to save conversation to vector store."""
    try:
        vector_service = get_vector_service()
        
        # Save user message
        await vector_service.add_text(
            user_id=user_id,
            text=message,
            data_type="text",
            source="typing"
        )
        
        # Save assistant response
        await vector_service.add_text(
            user_id=user_id,
            text=response,
            data_type="text",
            source="assistant"
        )
    except Exception as e:
        print(f"Error saving to vector store: {e}")


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
        
        # Save assistant response to session
        await session_manager.add_assistant_message(session_id, full_response)
        
        # Send completion event
        yield f"data: {json.dumps({'done': True, 'session_id': str(session_id)})}\n\n"
        
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
    """
    try:
        # Get the chain
        chain = await get_mood_chain()
        
        # Get response
        response = await chain.invoke(
            user_id=request.user_id,
            session_id=request.session_id,
            user_message=request.message
        )
        
        # Schedule background task
        background_tasks.add_task(
            save_to_vector_store,
            request.user_id,
            request.message,
            response
        )
        
        return ChatResponse(
            response=response,
            session_id=str(request.session_id)
        )
        
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))
