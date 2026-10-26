"""
Test script for custom model integration.

This script tests the connection to the custom model via ngrok
and verifies that it can generate responses.
"""

import asyncio
from app.services import get_custom_model
from config import settings


async def test_custom_model():
    """Test the custom model connection and generation."""
    
    print("=" * 60)
    print("Testing Custom Model Integration")
    print("=" * 60)
    
    # Check configuration
    print(f"\nConfiguration:")
    print(f"  USE_CUSTOM_MODEL: {settings.use_custom_model}")
    print(f"  CUSTOM_MODEL_URL: {settings.custom_model_url}")
    print(f"  Temperature: {settings.custom_model_temperature}")
    print(f"  Max Tokens: {settings.custom_model_max_tokens}")
    print(f"  Timeout: {settings.custom_model_timeout}s")
    
    if not settings.custom_model_url:
        print("\n❌ Error: CUSTOM_MODEL_URL is not set in .env file")
        return
    
    # Create model instance
    print(f"\n📡 Connecting to custom model at: {settings.custom_model_url}")
    model = get_custom_model(
        base_url=settings.custom_model_url,
        temperature=settings.custom_model_temperature,
        max_tokens=settings.custom_model_max_tokens,
        timeout=settings.custom_model_timeout
    )
    
    # Test prompt
    test_prompt = "Hello! I'm feeling a bit anxious today. Can you help me?"
    
    print(f"\n📝 Test Prompt:")
    print(f"  {test_prompt}")
    
    print(f"\n⏳ Generating response...")
    
    try:
        # Test async call
        response = await model._acall(test_prompt)
        
        print(f"\n✅ Response received:")
        print(f"  {response}")
        print(f"\n{'=' * 60}")
        print("✅ Custom model test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during generation:")
        print(f"  {str(e)}")
        print(f"\n{'=' * 60}")
        print("❌ Custom model test failed!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_custom_model())
