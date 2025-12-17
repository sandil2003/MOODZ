"""
Final integration test - Test with the exact prompt format.

This tests with the ACTUAL prompt that will be sent from MOODZ backend.
"""

import httpx
import json


def test_with_real_prompt():
    """Test with a real mood-related prompt."""
    
    CUSTOM_MODEL_URL = "https://unharping-unhumidified-chara.ngrok-free.dev"
    
    print("=" * 70)
    print("🧪 FINAL INTEGRATION TEST")
    print("=" * 70)
    
    # Test with the EXACT prompt from earlier
    test_cases = [
        {
            "name": "Anxiety Support",
            "prompt": "Hello! I'm feeling a bit anxious today. Can you help me?",
            "max_tokens": 512
        },
        {
            "name": "Short Response",
            "prompt": "How are you?",
            "max_tokens": 100
        },
        {
            "name": "Mood Check",
            "prompt": "I'm feeling stressed about work.",
            "max_tokens": 256
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"Test {i}: {test['name']}")
        print(f"{'='*70}")
        
        payload = {
            "prompt": test["prompt"],
            "temperature": 0.7,
            "max_tokens": test["max_tokens"]
        }
        
        print(f"\n📝 Prompt: {test['prompt']}")
        print(f"⚙️  Max tokens: {test['max_tokens']}")
        
        try:
            with httpx.Client(timeout=60) as client:
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
                        print(f"\n✅ SUCCESS!")
                        print(f"📊 Response length: {len(generated)} characters")
                        print(f"📄 Generated text:")
                        print(f"   {generated[:200]}...")
                        if len(generated) > 200:
                            print(f"   ... (truncated, total {len(generated)} chars)")
                    else:
                        print(f"\n❌ FAILED - Empty response")
                        print(f"   Full response: {json.dumps(result, indent=2)}")
                        print(f"\n⚠️  Your Colab server might still be using OLD code!")
                        print(f"   Check Colab logs - you should see:")
                        print(f"   📊 Generated: X tokens (where X > 0)")
                else:
                    print(f"\n❌ HTTP Error: {response.status_code}")
                    print(f"   Response: {response.text}")
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")
    
    print(f"\n{'='*70}")
    print("🏁 TESTING COMPLETE")
    print("=" * 70)
    
    print("\n📋 SUMMARY:")
    print("If ALL tests show ✅ SUCCESS with actual generated text:")
    print("  → Your integration is COMPLETE! 🎉")
    print("  → You can now use the custom model in MOODZ")
    print("\nIf tests show ❌ FAILED with empty responses:")
    print("  → Your Colab server is still using OLD code")
    print("  → In Colab: Stop the server, update code, restart")
    print("  → Make sure you see the debug logs in Colab")


if __name__ == "__main__":
    test_with_real_prompt()
