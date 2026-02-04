import os
import asyncio
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

async def test_gemini_direct():
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = "gemini-2.5-flash"
    
    print(f"Testing Gemini API with model: {model_name}")
    
    if not api_key:
        print("❌ GEMINI_API_KEY not found in .env")
        return

    try:
        llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=0.7
        )
        
        response = await llm.ainvoke("Hello, how are you today?")
        print(f"✅ Gemini Response: {response.content}")
        
    except Exception as e:
        print(f"❌ Error testing Gemini API: {e}")

if __name__ == "__main__":
    asyncio.run(test_gemini_direct())
