"""
Example usage of SessionManager for short-term memory.

This script demonstrates how to use the SessionManager service
to handle conversation history with automatic TTL expiry.
"""

import asyncio
from uuid import uuid4
from app.services import get_session_manager


async def example_conversation():
    """Example conversation flow using SessionManager."""
    
    # Get session manager instance
    session_manager = await get_session_manager()
    
    # Create a new session
    session_id = uuid4()
    print(f"Created session: {session_id}")
    
    # Add user message
    await session_manager.add_user_message(
        session_id=session_id,
        content="Hello! I'm feeling stressed about work.",
        metadata={"mood_score": 4}
    )
    print("✓ Added user message")
    
    # Add assistant response
    await session_manager.add_assistant_message(
        session_id=session_id,
        content="I understand you're feeling stressed. Can you tell me more about what's happening at work?",
        metadata={"sentiment": "empathetic"}
    )
    print("✓ Added assistant message")
    
    # Add another user message
    await session_manager.add_user_message(
        session_id=session_id,
        content="I have a big presentation tomorrow and I'm not prepared.",
        metadata={"mood_score": 3}
    )
    print("✓ Added another user message")
    
    # Get recent history (last 10 messages)
    history = await session_manager.get_recent_history(session_id, limit=10)
    print(f"\n📜 Recent history ({len(history)} messages):")
    for i, msg in enumerate(history, 1):
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        timestamp = msg.get("timestamp", "")
        print(f"  {i}. [{role}] {content[:50]}... ({timestamp})")
    
    # Check session info
    session_length = await session_manager.get_session_length(session_id)
    ttl = await session_manager.get_session_ttl(session_id)
    print(f"\n📊 Session info:")
    print(f"  - Total messages: {session_length}")
    print(f"  - TTL remaining: {ttl} seconds")
    
    # Get full history
    full_history = await session_manager.get_full_history(session_id)
    print(f"\n📚 Full history: {len(full_history)} messages")
    
    # Extend TTL
    await session_manager.extend_session_ttl(session_id, additional_seconds=7200)
    new_ttl = await session_manager.get_session_ttl(session_id)
    print(f"✓ Extended TTL to {new_ttl} seconds (2 hours)")
    
    # List active sessions
    active_sessions = await session_manager.get_active_sessions()
    print(f"\n🔄 Active sessions: {len(active_sessions)}")
    
    # Clear session (optional)
    # await session_manager.clear_session(session_id)
    # print("✓ Session cleared")


async def example_with_custom_messages():
    """Example with custom message format."""
    
    session_manager = await get_session_manager()
    session_id = uuid4()
    
    # Add custom formatted message
    custom_message = {
        "role": "user",
        "content": "I'm feeling much better today!",
        "timestamp": "2025-12-07T14:30:00",
        "metadata": {
            "mood_score": 8,
            "sentiment": "Happy",
            "topics": ["mood", "improvement"]
        }
    }
    
    await session_manager.add_message_to_session(session_id, custom_message)
    print("✓ Added custom message")
    
    exists = await session_manager.session_exists(session_id)
    print(f"Session exists: {exists}")
    # Retrieve and display
    history = await session_manager.get_recent_history(session_id)
    if history:
        print(f"\nRetrieved message:")
        print(f"  Content: {history[0]['content']}")
        print(f"  Metadata: {history[0]['metadata']}")
    else:
        print("No history found")


async def example_session_lifecycle():
    """Example of session lifecycle management."""
    
    session_manager = await get_session_manager()
    session_id = uuid4()
    
    # Check if session exists (should be False)
    exists = await session_manager.session_exists(session_id)
    print(f"Session exists: {exists}")
    
    # Add a message (creates session)
    await session_manager.add_user_message(session_id, "Hello!")
    
    # Check again (should be True)
    exists = await session_manager.session_exists(session_id)
    print(f"Session exists after message: {exists}")
    
    # Get session length
    length = await session_manager.get_session_length(session_id)
    print(f"Session length: {length}")
    
    # Clear session
    await session_manager.clear_session(session_id)
    
    # Check again (should be False)
    exists = await session_manager.session_exists(session_id)
    print(f"Session exists after clear: {exists}")


if __name__ == "__main__":
    async def run_all_examples():
        """Run all examples in a single event loop."""
        print("=== SessionManager Examples ===\n")
        
        print("Example 1: Basic Conversation")
        print("-" * 50)
        await example_conversation()
        
        print("\n\nExample 2: Custom Messages")
        print("-" * 50)
        await example_with_custom_messages()
        
        print("\n\nExample 3: Session Lifecycle")
        print("-" * 50)
        await example_session_lifecycle()
    
    # Run all examples in a single event loop
    asyncio.run(run_all_examples())
