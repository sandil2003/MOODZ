"""
Quick test script to verify SerpAPI is working correctly
"""
import os
from dotenv import load_dotenv
from langchain_community.utilities import SerpAPIWrapper

load_dotenv()

print("🔍 Testing SerpAPI Connection...")
print(f"API Key present: {'Yes' if os.getenv('SERPAPI_API_KEY') else 'No'}")
print(f"API Key (first 10 chars): {os.getenv('SERPAPI_API_KEY')[:10]}...")

try:
    search = SerpAPIWrapper(serpapi_api_key=os.getenv("SERPAPI_API_KEY"))
    print("\n✅ SerpAPIWrapper initialized successfully")
    
    print("\n🔎 Running test search: 'latest AI news'")
    result = search.run("latest AI news")
    
    print(f"\n✅ Search completed!")
    print(f"Result type: {type(result)}")
    print(f"Result length: {len(str(result))}")
    print(f"\n📄 First 500 characters:")
    print(str(result)[:500])
    print("\n" + "="*60)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
