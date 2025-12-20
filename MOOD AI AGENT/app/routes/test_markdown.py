"""
Test endpoint for markdown rendering verification.
Add this to your FastAPI routes to test markdown rendering.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/test", tags=["test"])

TEST_MARKDOWN = """# Markdown Rendering Test

## Overview
This is a **test response** to verify that markdown rendering is working correctly in the frontend.

## Features to Check

### Text Formatting
- **Bold text** should appear bold
- *Italic text* should appear italic
- `Inline code` should have a different background

### Lists
1. First ordered item
2. Second ordered item
3. Third ordered item

Unordered list:
- Apple
- Banana
- Cherry

### Code Block
```python
def test_function():
    return "Hello, World!"
```

### Blockquote
> This is a blockquote.
> It should have a left border.

## Summary
If all the above elements render correctly, then **markdown is working**! ✅

---
*Test completed successfully*
"""


@router.get("/markdown")
async def test_markdown_rendering():
    """
    Test endpoint that returns markdown-formatted text.
    
    Usage:
    1. Call GET /test/markdown
    2. Display the response in your frontend
    3. Verify markdown renders correctly
    """
    return {
        "response": TEST_MARKDOWN,
        "session_id": "test-session",
        "test": True
    }
