import asyncio
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.routes.chat import normalize_text

def test_normalization():
    print("Testing normalize_text...")
    
    # Test case 1: String
    assert normalize_text("Hello") == "Hello"
    print("✅ Case 1: String passed")
    
    # Test case 2: List of parts (Gemini style)
    parts = [{"text": "Hi "}, {"text": "there!"}]
    assert normalize_text(parts) == "Hi there!"
    print("✅ Case 2: List of parts passed")
    
    # Test case 3: Mixed list
    mixed = [{"text": "Part 1"}, " and string"]
    assert normalize_text(mixed) == "Part 1 and string"
    print("✅ Case 3: Mixed list passed")
    
    # Test case 4: None
    assert normalize_text(None) == ""
    print("✅ Case 4: None passed")
    
    # Test case 5: Other types
    assert normalize_text(123) == "123"
    print("✅ Case 5: Integer passed")

if __name__ == "__main__":
    test_normalization()
    print("\nAll normalization tests passed!")
