"""
Debug script to check what's happening in your Colab server.

This will help identify if:
1. The server is using the old code (not restarted)
2. The model is not generating tokens
3. There's an issue with the tokenizer
"""

import httpx
import json


def debug_colab_server():
    """Debug the Colab server to find the issue."""
    
    CUSTOM_MODEL_URL = "https://unharping-unhumidified-chara.ngrok-free.dev"
    
    print("=" * 70)
    print("🔍 DEBUGGING COLAB SERVER")
    print("=" * 70)
    
    # Test 1: Check if server is running
    print("\n📋 Test 1: Health Check")
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{CUSTOM_MODEL_URL}/health")
            if response.status_code == 200:
                print("✅ Server is running")
                print(f"   Response: {response.json()}")
            else:
                print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach server: {e}")
        return
    
    # Test 2: Try with a very simple prompt
    print("\n📋 Test 2: Simple Prompt Test")
    simple_payload = {
        "prompt": "Hello",
        "temperature": 0.7,
        "max_tokens": 50
    }
    
    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{CUSTOM_MODEL_URL}/generate",
                json=simple_payload,
                headers={
                    "Content-Type": "application/json",
                    "ngrok-skip-browser-warning": "true"
                }
            )
            
            print(f"   Status: {response.status_code}")
            result = response.json()
            print(f"   Response: {json.dumps(result, indent=2)}")
            
            if result.get("generated_text") == "":
                print("\n⚠️  ISSUE FOUND: generated_text is empty!")
                print("\n🔍 Possible causes:")
                print("   1. Server not restarted after code change")
                print("   2. Model is not generating any tokens")
                print("   3. Tokenizer issue")
                print("\n💡 SOLUTION:")
                print("   In your Colab notebook:")
                print("   1. Stop the uvicorn server (interrupt the cell)")
                print("   2. Re-run the cell with the corrected code")
                print("   3. Make sure you see the startup logs")
                print("   4. Run this test again")
            else:
                print(f"\n✅ SUCCESS! Generated text: {result['generated_text'][:100]}...")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Try with different temperature
    print("\n📋 Test 3: High Temperature Test")
    high_temp_payload = {
        "prompt": "Say hello",
        "temperature": 1.0,
        "max_tokens": 20
    }
    
    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{CUSTOM_MODEL_URL}/generate",
                json=high_temp_payload,
                headers={
                    "Content-Type": "application/json",
                    "ngrok-skip-browser-warning": "true"
                }
            )
            
            result = response.json()
            print(f"   Generated: '{result.get('generated_text', '')}'")
            
            if result.get("generated_text"):
                print("   ✅ Model CAN generate text!")
            else:
                print("   ❌ Still empty - model might not be generating")
                
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("🔍 DEBUGGING COMPLETE")
    print("=" * 70)
    
    print("\n📝 NEXT STEPS:")
    print("1. Check your Colab notebook logs for any errors")
    print("2. Make sure you see these logs when a request comes in:")
    print("   ============================================================")
    print("   📝 Received prompt: ...")
    print("   📊 Input length: X tokens")
    print("   📊 Generated: Y tokens")
    print("   ✅ Response: ...")
    print("   ============================================================")
    print("\n3. If you DON'T see those logs:")
    print("   → Server is using OLD code - RESTART IT!")
    print("\n4. If you see 'Generated: 0 tokens':")
    print("   → Model is not generating - check model loading")
    print("\n5. Share the Colab logs here so I can help further")


if __name__ == "__main__":
    debug_colab_server()
