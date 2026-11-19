"""
Test script to verify token usage and request count optimization.
Verifies that exactly 1 LLM request is made per user chat message.
"""
import asyncio
import sys
import os
from uuid import uuid4
from unittest.mock import AsyncMock

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services import get_mood_agent


async def run_token_verifier():
    print("=" * 70)
    print("🧪 TOKEN & REQUEST OPTIMIZATION VERIFIER")
    print("=" * 70)
    
    agent = await get_mood_agent()
    
    user_id = uuid4()
    session_id = uuid4()
    user_message = "I am feeling super happy because I got a new pet dog today! He is a puppy."
    
    # Store reference to the real astream method
    real_astream = agent.llm.astream
    
    # Counter for LLM requests
    llm_call_count = 0
    input_text = ""
    
    # Intercept the astream method to count calls and inspect input tokens
    async def mock_astream(messages, *args, **kwargs):
        nonlocal llm_call_count, input_text
        llm_call_count += 1
        
        # Capture the prompt/messages content to measure tokens
        prompt_parts = []
        for msg in messages:
            if isinstance(msg, dict):
                prompt_parts.append(msg.get("content", ""))
            elif hasattr(msg, "content"):
                prompt_parts.append(msg.content)
            else:
                prompt_parts.append(str(msg))
        input_text = "\n".join(prompt_parts)
        
        # Call the real LLM astream
        async for chunk in real_astream(messages, *args, **kwargs):
            yield chunk

    # Attach our interceptor by bypassing Pydantic's __setattr__ via __dict__
    agent.llm.__dict__["astream"] = mock_astream
    
    print(f"User Message: '{user_message}'")
    print("\nRunning agent invoke...")
    
    result_holder = {}
    response = await agent.invoke(
        user_id=user_id,
        session_id=session_id,
        user_message=user_message,
        result_holder=result_holder
    )
    
    # Clean response
    from app.services.fallback_mocks import API_ERROR_WARNING
    clean_response = response.replace(API_ERROR_WARNING, "")
    
    print("\n--- METRICS SUMMARY ---")
    print(f"1. Total LLM API Requests: {llm_call_count}")
    
    # Heuristic estimation: ~4 characters per token
    estimated_input_tokens = len(input_text) // 4
    estimated_output_tokens = len(clean_response) // 4
    total_tokens = estimated_input_tokens + estimated_output_tokens
    
    print(f"2. Estimated Input Tokens: {estimated_input_tokens} (~{len(input_text)} characters)")
    print(f"3. Estimated Output (Response) Tokens: {estimated_output_tokens} (~{len(clean_response)} characters)")
    print(f"4. Estimated Total Tokens: {total_tokens}")
    print(f"5. Classification Result Saved: {result_holder.get('classification', {}).get('save')}")
    print(f"6. Detected Mood: {result_holder.get('classification', {}).get('mood')}")
    print(f"7. Extracted Facts: {result_holder.get('classification', {}).get('extracted_facts')}")
    
    # Assertions
    assert llm_call_count == 1, f"Expected exactly 1 LLM request, but got {llm_call_count}"
    print("\n✅ PASS: Exactly 1 LLM request was made.")
    print("✅ PASS: Token and Request optimizations verified successfully!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_token_verifier())
