"""
Test script to verify markdown rendering in the frontend.
This creates a mock deep search response with rich markdown formatting.
"""

import asyncio
import json

# Sample markdown-rich response for testing
TEST_MARKDOWN_RESPONSE = """# Latest AI Developments in 2024

## Overview

Artificial Intelligence has seen remarkable progress in 2024, with breakthroughs in **large language models**, **multimodal AI**, and **AI safety**. The industry continues to evolve rapidly with new applications emerging across healthcare, education, and creative industries.

## Key Findings

- **GPT-4 and Beyond**: OpenAI's latest models demonstrate improved reasoning capabilities
- **Multimodal Integration**: AI systems now seamlessly process text, images, and audio
- **Open Source Movement**: Companies like Meta and Mistral are releasing powerful open-source models
- **AI Safety Research**: Increased focus on alignment and responsible AI development
- **Edge AI**: More efficient models running on consumer devices

## Latest Updates

### December 2024
- Google announced **Gemini 2.0** with enhanced multimodal capabilities
- Anthropic released **Claude 3.5** with improved coding abilities
- Meta's **Llama 3** family expanded with specialized variants

### November 2024
- OpenAI introduced **GPT-4 Turbo** with reduced costs
- Microsoft integrated AI deeply into **Office 365**
- Adobe launched **Firefly 2** for creative professionals

## Current Trends

1. **Agentic AI**: Systems that can plan and execute complex tasks autonomously
2. **Personalization**: AI models adapting to individual user preferences
3. **Efficiency**: Smaller, faster models achieving comparable performance
4. **Regulation**: Governments worldwide implementing AI governance frameworks

### Code Example
```python
# Simple AI integration example
from openai import OpenAI

client = OpenAI()
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## Summary

The AI landscape in 2024 is characterized by rapid innovation, increased accessibility through open-source initiatives, and growing emphasis on safety and ethics. **Large language models** continue to improve while becoming more efficient, and **multimodal capabilities** are becoming standard rather than exceptional.

> "AI is not just a technology trend; it's a fundamental shift in how we interact with computers and information." - Industry Expert

---

**Sources**: OpenAI Blog, Google AI Research, Meta AI, Anthropic Documentation
"""


async def test_markdown_output():
    """Test function to output the markdown response."""
    print("=" * 60)
    print("MARKDOWN TEST OUTPUT")
    print("=" * 60)
    print("\nThis is what the backend would send to the frontend:\n")
    print(TEST_MARKDOWN_RESPONSE)
    print("\n" + "=" * 60)
    print("END OF TEST OUTPUT")
    print("=" * 60)
    
    # Also save to a file for easy copying
    with open("test_markdown_output.md", "w", encoding="utf-8") as f:
        f.write(TEST_MARKDOWN_RESPONSE)
    
    print("\n✅ Test markdown saved to: test_markdown_output.md")
    print("📋 Copy this content and paste it in your frontend to test rendering")


if __name__ == "__main__":
    asyncio.run(test_markdown_output())
