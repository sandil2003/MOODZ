"""
Example usage of ConversationClassifier.

Demonstrates how the classifier determines which conversations to save.
"""

import asyncio
from app.services import get_classifier


async def test_classifier():
    """Test the conversation classifier with various messages."""
    
    classifier = get_classifier()
    
    # Test messages
    test_messages = [
        # Should SAVE - Emotional content
        "I'm feeling really anxious about my job interview tomorrow.",
        "I had a great day today! Finally finished my project.",
        "I'm so stressed about everything going on in my life.",
        
        # Should SAVE - Personal facts
        "I have a dog named Rex who I love spending time with.",
        "I work as a software engineer at a startup.",
        "My birthday is next week and I'm turning 30.",
        
        # Should NOT SAVE - Greetings/small talk
        "Hi there!",
        "Hello",
        "Thanks!",
        "Ok, got it",
        
        # Should NOT SAVE - Simple questions
        "What's the weather?",
        "How are you?",
        
        # Should SAVE - Meaningful questions with context
        "How can I manage my stress better? I've been feeling overwhelmed.",
        "What should I do about my anxiety? It's affecting my sleep.",
    ]
    
    print("=== Conversation Classifier Test ===\n")
    
    for i, message in enumerate(test_messages, 1):
        print(f"{i}. Message: \"{message}\"")
        
        result = await classifier.classify(message)
        
        print(f"   Save: {result['save']}")
        print(f"   Mood: {result['mood']}")
        if result['extracted_facts']:
            print(f"   Facts: {result['extracted_facts']}")
        print()


async def test_fact_extraction():
    """Test fact extraction capabilities."""
    
    classifier = get_classifier()
    
    print("\n=== Fact Extraction Test ===\n")
    
    messages_with_facts = [
        "I'm a 28-year-old teacher living in New York.",
        "I have two cats named Luna and Shadow, and I love hiking on weekends.",
        "I'm taking medication for anxiety - Lexapro 10mg daily.",
        "My wife and I just bought our first house!",
    ]
    
    for message in messages_with_facts:
        print(f"Message: \"{message}\"")
        result = await classifier.classify(message)
        print(f"Extracted facts:")
        for fact in result['extracted_facts']:
            print(f"  - {fact}")
        print()


async def test_mood_detection():
    """Test mood detection capabilities."""
    
    classifier = get_classifier()
    
    print("\n=== Mood Detection Test ===\n")
    
    mood_messages = [
        ("I'm so excited about the concert tonight!", "excited"),
        ("I feel really down and don't want to do anything.", "sad"),
        ("I'm worried about the test results.", "anxious"),
        ("Everything is going well, I'm content.", "content"),
        ("I'm so frustrated with this situation!", "frustrated"),
        ("Just feeling neutral today, nothing special.", "neutral"),
    ]
    
    for message, expected_mood in mood_messages:
        print(f"Message: \"{message}\"")
        result = await classifier.classify(message)
        print(f"Detected mood: {result['mood']} (expected: {expected_mood})")
        print()


async def test_edge_cases():
    """Test edge cases and boundary conditions."""
    
    classifier = get_classifier()
    
    print("\n=== Edge Cases Test ===\n")
    
    edge_cases = [
        "",  # Empty message
        "...",  # Just punctuation
        "test test test",  # Repetitive
        "asdfghjkl",  # Gibberish
        "I'm feeling... I don't know... maybe anxious? Or stressed? Not sure.",  # Uncertain
    ]
    
    for message in edge_cases:
        print(f"Message: \"{message}\"")
        result = await classifier.classify(message)
        print(f"Result: {result}")
        print()


if __name__ == "__main__":
    async def run_all_tests():
        """Run all classifier tests."""
        await test_classifier()
        await test_fact_extraction()
        await test_mood_detection()
        await test_edge_cases()
        
        print("\n=== Tests Complete ===")
    
    asyncio.run(run_all_tests())
