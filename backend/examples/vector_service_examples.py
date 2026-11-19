"""
Example usage of VectorService for Pinecone similarity search.

This script demonstrates how to use the VectorService to:
- Add text with embeddings to Pinecone
- Perform similarity search
- Filter by user, data type, and mood
- Get relevant context for AI responses
"""

import asyncio
from uuid import uuid4
from app.services import get_vector_service


async def example_basic_usage():
    """Basic usage of VectorService."""
    print("=== Basic Vector Service Usage ===\n")
    
    # Get vector service
    vector_service = get_vector_service()
    
    # Create a test user
    user_id = uuid4()
    print(f"Test user ID: {user_id}\n")
    
    # Add some mood check-ins
    print("Adding mood check-ins...")
    
    doc_id1 = await vector_service.add_text(
        user_id=user_id,
        text="I'm feeling really stressed about the upcoming deadline at work.",
        data_type="mood_checkin",
        source="typing",
        mood_label="anxious",
        additional_info={"intensity": 7}
    )
    print(f"✓ Added document: {doc_id1}")
    
    doc_id2 = await vector_service.add_text(
        user_id=user_id,
        text="Had a great day! Finished my project and got positive feedback.",
        data_type="mood_checkin",
        source="typing",
        mood_label="happy",
        additional_info={"intensity": 9}
    )
    print(f"✓ Added document: {doc_id2}")
    
    doc_id3 = await vector_service.add_text(
        user_id=user_id,
        text="Feeling overwhelmed with all the tasks I need to complete.",
        data_type="mood_checkin",
        source="typing",
        mood_label="stressed",
        additional_info={"intensity": 8}
    )
    print(f"✓ Added document: {doc_id3}\n")
    
    # Perform similarity search
    print("Searching for similar entries to 'work pressure'...")
    results = await vector_service.similarity_search(
        query="work pressure and deadlines",
        user_id=user_id,
        k=3
    )
    
    print(f"\nFound {len(results)} similar entries:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.4f}")
        print(f"   Text: {result['text'][:80]}...")
        print(f"   Mood: {result['metadata'].get('mood_label', 'N/A')}")
        print(f"   Type: {result['metadata'].get('data_type')}")


async def example_filtered_search():
    """Example of filtered similarity search."""
    print("\n\n=== Filtered Search Example ===\n")
    
    vector_service = get_vector_service()
    user_id = uuid4()
    
    # Add different types of data
    print("Adding various data types...")
    
    await vector_service.add_text(
        user_id=user_id,
        text="Listened to calming piano music before bed.",
        data_type="music",
        source="music_analysis",
        mood_label="calm",
        additional_info={"genre": "classical", "duration": 300}
    )
    
    await vector_service.add_text(
        user_id=user_id,
        text="Journal entry: Today was challenging but I learned a lot.",
        data_type="journal",
        source="journal",
        mood_label="reflective"
    )
    
    await vector_service.add_text(
        user_id=user_id,
        text="Quick check-in: Feeling peaceful after meditation.",
        data_type="mood_checkin",
        source="typing",
        mood_label="calm"
    )
    
    print("✓ Added 3 entries\n")
    
    # Search only in mood check-ins
    print("Searching only in mood_checkin data type...")
    results = await vector_service.similarity_search(
        query="feeling peaceful",
        user_id=user_id,
        data_type="mood_checkin",
        k=5
    )
    
    print(f"Found {len(results)} mood check-ins:")
    for result in results:
        print(f"  - {result['text'][:60]}... (score: {result['score']:.4f})")


async def example_context_building():
    """Example of building context for AI."""
    print("\n\n=== Context Building Example ===\n")
    
    vector_service = get_vector_service()
    user_id = uuid4()
    
    # Add user history
    print("Adding user history...")
    
    await vector_service.add_text(
        user_id=user_id,
        text="I have a dog named Rex who always makes me happy.",
        data_type="text",
        source="typing",
        mood_label="happy"
    )
    
    await vector_service.add_text(
        user_id=user_id,
        text="Work has been stressful lately with the new project.",
        data_type="text",
        source="typing",
        mood_label="stressed"
    )
    
    await vector_service.add_text(
        user_id=user_id,
        text="I love hiking on weekends to clear my mind.",
        data_type="text",
        source="typing",
        mood_label="content"
    )
    
    print("✓ Added user history\n")
    
    # Get context for a new query
    query = "I'm feeling down today"
    print(f"User query: '{query}'")
    print("\nRetrieving relevant context...\n")
    
    context = await vector_service.get_user_context(
        user_id=user_id,
        query=query,
        k=3
    )
    
    print(context)


async def example_similar_moods():
    """Example of finding similar past moods."""
    print("\n\n=== Similar Moods Example ===\n")
    
    vector_service = get_vector_service()
    user_id = uuid4()
    
    # Add mood history
    print("Adding mood history...")
    
    moods = [
        ("Feeling anxious about tomorrow's presentation.", "anxious"),
        ("Really happy after getting promoted!", "happy"),
        ("Stressed about financial situation.", "stressed"),
        ("Nervous about the job interview.", "anxious"),
        ("Excited about the upcoming vacation!", "excited")
    ]
    
    for text, mood in moods:
        await vector_service.add_text(
            user_id=user_id,
            text=text,
            data_type="mood_checkin",
            source="typing",
            mood_label=mood
        )
    
    print(f"✓ Added {len(moods)} mood entries\n")
    
    # Find similar moods
    current_mood = "Worried about the upcoming exam"
    print(f"Current mood: '{current_mood}'")
    print("\nFinding similar past moods...\n")
    
    similar = await vector_service.find_similar_moods(
        user_id=user_id,
        current_mood=current_mood,
        k=3
    )
    
    print(f"Found {len(similar)} similar moods:")
    for i, mood in enumerate(similar, 1):
        print(f"\n{i}. {mood['text']}")
        print(f"   Mood: {mood['metadata']['mood_label']}")
        print(f"   Similarity: {mood['score']:.4f}")


async def example_index_stats():
    """Example of getting index statistics."""
    print("\n\n=== Index Statistics ===\n")
    
    vector_service = get_vector_service()
    
    stats = await vector_service.get_index_stats()
    
    print("Pinecone Index Stats:")
    print(f"  Total vectors: {stats.get('total_vectors', 0)}")
    print(f"  Dimension: {stats.get('dimension', 0)}")
    print(f"  Index fullness: {stats.get('index_fullness', 0):.2%}")


if __name__ == "__main__":
    async def run_all_examples():
        """Run all examples."""
        await example_basic_usage()
        await example_filtered_search()
        await example_context_building()
        await example_similar_moods()
        await example_index_stats()
        
        print("\n\n=== Examples Complete ===")
    
    asyncio.run(run_all_examples())
