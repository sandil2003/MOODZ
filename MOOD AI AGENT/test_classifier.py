"""
Test script to verify the ConversationClassifier is working correctly.
Run this from the MOOD AI AGENT directory.
"""
import asyncio
from app.services.classifier import ConversationClassifier


async def test_classifier():
    """Test the classifier with various messages."""
    
    print("=" * 60)
    print("Testing ConversationClassifier")
    print("=" * 60)
    
    # Initialize classifier
    classifier = ConversationClassifier()
    
    # Test cases
    test_messages = [
        {
            "message": "Hello, how are you?",
            "expected": "Should NOT save (too generic)"
        },
        {
            "message": "I'm feeling really stressed about my presentation tomorrow. I've been working on it all week but I'm still worried.",
            "expected": "Should SAVE with mood: stressed/anxious"
        },
        {
            "message": "I just adopted a golden retriever puppy named Max! He's 3 months old and loves playing fetch.",
            "expected": "Should SAVE with facts extracted"
        },
        {
            "message": "I got promoted to senior developer today! I'll be leading a team of 5 people at TechCorp.",
            "expected": "Should SAVE with mood: excited, facts extracted"
        }
    ]
    
    for i, test in enumerate(test_messages, 1):
        print(f"\n{'=' * 60}")
        print(f"Test {i}: {test['expected']}")
        print(f"{'=' * 60}")
        print(f"Message: {test['message']}")
        print(f"\nClassifying...")
        
        try:
            result = await classifier.classify(test['message'])
            
            print(f"\n✅ Classification Result:")
            print(f"  - Save to DB: {result['save']}")
            print(f"  - Mood: {result['mood']}")
            print(f"  - Extracted Facts: {len(result['extracted_facts'])} facts")
            
            if result['extracted_facts']:
                print(f"\n  Facts:")
                for fact in result['extracted_facts']:
                    print(f"    • {fact}")
            
            # Verify expectations
            if i == 1:  # Generic greeting
                assert result['save'] == False, "Generic greeting should NOT be saved"
                print(f"\n✅ PASS: Correctly identified as not worth saving")
            else:  # Meaningful messages
                assert result['save'] == True, "Meaningful message should be saved"
                print(f"\n✅ PASS: Correctly identified as worth saving")
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 60}")
    print("✅ All tests completed!")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    asyncio.run(test_classifier())
