"""
Example usage of MoodAgentChain with LCEL.

Demonstrates the complete flow:
1. Parallel context fetching from Redis, Pinecone, and PostgreSQL
2. Context combination
3. LLM generation
4. Response handling
"""

import asyncio
from uuid import uuid4
from app.services import get_mood_chain, get_session_manager, get_vector_service
from app.models import MoodHistory, UserFact
from app.database import AsyncSessionLocal


async def setup_test_data(user_id, session_id):
    """Set up test data in all three stores."""
    print("Setting up test data...\n")
    
    # 1. Add to PostgreSQL
    async with AsyncSessionLocal() as db:
        from app.models import User
        
        # Create user first (required for foreign key)
        user = User(
            id=user_id,
            email=f"test_{user_id}@example.com",
            name="Test User",
            hashed_password="hashed_password_here",
            role="user"
        )
        db.add(user)
        await db.flush()  # Ensure user is created before adding related records
        
        # Add mood history
        mood1 = MoodHistory(
            user_id=user_id,
            mood_score=4,
            sentiment_label="anxious",
            summary="Feeling stressed about work deadlines",
            session_id=session_id
        )
        mood2 = MoodHistory(
            user_id=user_id,
            mood_score=8,
            sentiment_label="happy",
            summary="Had a great day with friends",
            session_id=session_id
        )
        
        # Add user facts
        fact1 = UserFact(
            user_id=user_id,
            fact_text="User has a dog named Rex",
            category="Personal",
            source="conversation"
        )
        fact2 = UserFact(
            user_id=user_id,
            fact_text="Works as a software engineer",
            category="Work",
            source="conversation"
        )
        
        db.add_all([mood1, mood2, fact1, fact2])
        await db.commit()
    
    print("✓ Added data to PostgreSQL")
    
    # 2. Add to Pinecone
    vector_service = get_vector_service()
    
    await vector_service.add_text(
        user_id=user_id,
        text="I was really stressed about the project deadline last week.",
        data_type="mood_checkin",
        source="typing",
        mood_label="stressed"
    )
    
    await vector_service.add_text(
        user_id=user_id,
        text="Playing with Rex always makes me feel better.",
        data_type="text",
        source="typing",
        mood_label="happy"
    )
    
    print("✓ Added data to Pinecone")
    
    # 3. Add to Redis
    session_manager = await get_session_manager()
    
    await session_manager.add_user_message(
        session_id,
        "Hi, I've been feeling a bit down lately."
    )
    
    await session_manager.add_assistant_message(
        session_id,
        "I'm sorry to hear that. Can you tell me more about what's been going on?"
    )
    
    print("✓ Added data to Redis\n")


async def example_basic_conversation():
    """Example of basic conversation with context."""
    print("=== Basic Conversation Example ===\n")
    
    # Create test user and session
    user_id = uuid4()
    session_id = uuid4()
    
    # Setup test data
    await setup_test_data(user_id, session_id)
    
    # Get the chain
    chain = await get_mood_chain()
    
    # User messages
    messages = [
        "I'm feeling stressed about work again.",
        "Maybe I should spend more time with my dog?",
        "What do you think I should do?"
    ]
    
    print("Starting conversation...\n")
    
    for msg in messages:
        print(f"USER: {msg}")
        
        # Get response
        response = await chain.invoke(
            user_id=user_id,
            session_id=session_id,
            user_message=msg
        )
        
        print(f"MOODZ: {response}\n")
        print("-" * 80 + "\n")


async def example_context_awareness():
    """Example showing context awareness."""
    print("\n=== Context Awareness Example ===\n")
    
    user_id = uuid4()
    session_id = uuid4()
    
    await setup_test_data(user_id, session_id)
    
    chain = await get_mood_chain()
    
    # Ask about past experiences
    response = await chain.invoke(
        user_id=user_id,
        session_id=session_id,
        user_message="What have I told you about myself?"
    )
    
    print(f"USER: What have I told you about myself?")
    print(f"MOODZ: {response}\n")


async def example_mood_tracking():
    """Example of mood tracking and pattern recognition."""
    print("\n=== Mood Tracking Example ===\n")
    
    user_id = uuid4()
    session_id = uuid4()
    
    await setup_test_data(user_id, session_id)
    
    chain = await get_mood_chain()
    
    # Ask about mood patterns
    response = await chain.invoke(
        user_id=user_id,
        session_id=session_id,
        user_message="Can you see any patterns in my mood?"
    )
    
    print(f"USER: Can you see any patterns in my mood?")
    print(f"MOODZ: {response}\n")


async def example_personalized_advice():
    """Example of personalized advice based on context."""
    print("\n=== Personalized Advice Example ===\n")
    
    user_id = uuid4()
    session_id = uuid4()
    
    await setup_test_data(user_id, session_id)
    
    chain = await get_mood_chain()
    
    # Ask for advice
    response = await chain.invoke(
        user_id=user_id,
        session_id=session_id,
        user_message="I'm feeling overwhelmed. What should I do?"
    )
    
    print(f"USER: I'm feeling overwhelmed. What should I do?")
    print(f"MOODZ: {response}\n")


if __name__ == "__main__":
    async def run_all_examples():
        """Run all examples."""
        await example_basic_conversation()
        await example_context_awareness()
        await example_mood_tracking()
        await example_personalized_advice()
        
        print("\n=== Examples Complete ===")
    
    asyncio.run(run_all_examples())
