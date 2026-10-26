"""
Test script to verify the Agent classification is working correctly.
Run this from the MOOD AI AGENT directory.
"""
import asyncio
import sys
import os
from uuid import uuid4

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services import get_mood_agent


async def test_classifier():
    """Test the consolidated agent classification with various messages."""
    
    print("=" * 60)
    print("Testing Consolidated Agent Classification")
    print("=" * 60)
    
    # Initialize agent
    agent = await get_mood_agent()
    
    user_id = uuid4()
    session_id = uuid4()
    
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
        print(f"\nInvoking agent...")
        
        try:
            result_holder = {}
            await agent.invoke(
                user_id=user_id,
                session_id=session_id,
                user_message=test['message'],
                result_holder=result_holder
            )
            
            result = result_holder.get("classification", {})
            
            print(f"\n✅ Classification Result:")
            print(f"  - Save to DB: {result.get('save')}")
            print(f"  - Mood: {result.get('mood')}")
            print(f"  - Extracted Facts: {len(result.get('extracted_facts', []))} facts")
            
            if result.get('extracted_facts'):
                print(f"\n  Facts:")
                for fact in result['extracted_facts']:
                    print(f"    • {fact}")
            
            # Verify expectations
            if i == 1:  # Generic greeting
                assert result.get('save') == False, "Generic greeting should NOT be saved"
                print(f"\n✅ PASS: Correctly identified as not worth saving")
            else:  # Meaningful messages
                assert result.get('save') == True, "Meaningful message should be saved"
                print(f"\n✅ PASS: Correctly identified as worth saving")
                
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            raise e
    
    print(f"\n{'=' * 60}")
    print("✅ All classification tests completed!")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    asyncio.run(test_classifier())
