"""
Test different variations of the anxiety prompt to find the issue.
"""

import httpx
import json


def test_prompt_variations():
    """Test variations to identify the specific issue."""
    
    CUSTOM_MODEL_URL = "https://unharping-unhumidified-chara.ngrok-free.dev"
    
    print("=" * 70)
    print("🔍 TESTING PROMPT VARIATIONS")
    print("=" * 70)
    
    # Test different variations
    prompts = [
        "Hello! I'm feeling a bit anxious today. Can you help me?",  # Original
        "I'm feeling anxious today. Can you help?",  # Shorter
        "I'm feeling anxious. Help me please.",  # Different phrasing
        "I feel anxious today",  # No question
        "Hello, I'm anxious",  # Simple
        "I'm feeling a bit anxious",  # No question mark
    ]
    
    for i, prompt in enumerate(prompts, 1):
        print(f"\n{'─'*70}")
        print(f"Test {i}: {prompt}")
        
        payload = {
            "prompt": prompt,
            "temperature": 0.7,
            "max_tokens": 100
        }
        
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    f"{CUSTOM_MODEL_URL}/generate",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "ngrok-skip-browser-warning": "true"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    generated = result.get("generated_text", "")
                    
                    if generated:
                        print(f"✅ Generated {len(generated)} chars: {generated[:80]}...")
                    else:
                        print(f"❌ Empty response")
                else:
                    print(f"❌ HTTP {response.status_code}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n{'='*70}")
    print("Analysis: Check which prompts work and which don't")
    print("This will help identify if it's a specific word/phrase issue")
    print("=" * 70)


if __name__ == "__main__":
    test_prompt_variations()
