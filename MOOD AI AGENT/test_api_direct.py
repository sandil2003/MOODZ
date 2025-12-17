"""
Simple standalone test for custom model API.

This script tests the connection to your Colab model without
requiring the full application dependencies.
"""

import httpx
import json


def test_custom_model_api():
    """Test the custom model API directly."""
    
    # Configuration
    CUSTOM_MODEL_URL = "https://unharping-unhumidified-chara.ngrok-free.dev"
    
    print("=" * 70)
    print("🧪 Testing Custom Model API")
    print("=" * 70)
    print(f"\n📡 Server URL: {CUSTOM_MODEL_URL}")
    
    # Test payload
    payload = {
        "prompt": "Hello! I'm feeling a bit anxious today. Can you help me?",
        "temperature": 0.7,
        "max_tokens": 512
    }
    
    print(f"\n📝 Test Payload:")
    print(json.dumps(payload, indent=2))
    
    print(f"\n⏳ Sending request to {CUSTOM_MODEL_URL}/generate ...")
    
    try:
        # Make the request
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{CUSTOM_MODEL_URL}/generate",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "ngrok-skip-browser-warning": "true"
                }
            )
            
            print(f"\n✅ Response Status: {response.status_code}")
            print(f"📊 Response Headers:")
            for key, value in response.headers.items():
                print(f"   {key}: {value}")
            
            # Try to parse as JSON
            try:
                result = response.json()
                print(f"\n📦 Response Body (JSON):")
                print(f"   Type: {type(result)}")
                print(f"   Content:")
                print(json.dumps(result, indent=4))
                
                # Try to extract text
                print(f"\n🔍 Attempting to extract text...")
                
                if isinstance(result, dict):
                    print(f"   Available keys: {list(result.keys())}")
                    
                    # Try different keys
                    for key in ["generated_text", "text", "response", "output", "result", "answer", "completion"]:
                        if key in result:
                            value = result[key]
                            print(f"   ✅ Found '{key}': {value[:100] if isinstance(value, str) else value}...")
                            break
                    else:
                        print(f"   ⚠️  None of the expected keys found!")
                        print(f"   📋 All key-value pairs:")
                        for k, v in result.items():
                            print(f"      {k}: {str(v)[:100]}...")
                
                elif isinstance(result, str):
                    print(f"   ✅ Response is a string: {result[:100]}...")
                
                else:
                    print(f"   ⚠️  Unexpected type: {type(result)}")
                    print(f"   Content: {str(result)[:200]}...")
                
            except json.JSONDecodeError:
                print(f"\n⚠️  Response is not JSON!")
                print(f"📄 Raw Response Text:")
                print(response.text[:500])
            
            print(f"\n{'=' * 70}")
            print("✅ Test completed!")
            print("=" * 70)
            
    except httpx.TimeoutException:
        print(f"\n❌ Error: Request timed out after 60 seconds")
        print("   - Check if your Colab server is running")
        print("   - Verify the model is loaded and ready")
        
    except httpx.ConnectError:
        print(f"\n❌ Error: Could not connect to {CUSTOM_MODEL_URL}")
        print("   - Verify the ngrok URL is correct")
        print("   - Check if the Colab server is running")
        print("   - Ensure ngrok tunnel is active")
        
    except httpx.HTTPStatusError as e:
        print(f"\n❌ HTTP Error: {e.response.status_code}")
        print(f"   Response: {e.response.text}")
        
    except Exception as e:
        print(f"\n❌ Unexpected Error: {type(e).__name__}")
        print(f"   Message: {str(e)}")


if __name__ == "__main__":
    test_custom_model_api()
