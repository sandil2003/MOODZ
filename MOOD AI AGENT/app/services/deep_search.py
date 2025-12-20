"""
Deep Search Agent for finding the latest and most current information on topics

Nodes:
 - Understanding Node: extracts search intent and key terms
 - Search Node: performs web search with queries optimized for latest information
 - Analysis Node: extracts current trends, recent updates, and latest findings
 - Writer Node: Creates comprehensive summary of the most current information found

Dependencies:
 - langchain-google-genai
 - langchain-core
 - langchain-community
 - python-dotenv
 - duckduckgo-search (free, no API key required)
"""

from typing import Dict, Any, List
import os
import asyncio
import json
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_google_genai import ChatGoogleGenerativeAI

# ----------------- Configuration -----------------
load_dotenv()


class DeepResearchAgent:
    """Agent for performing deep search to find the latest and most current information on topics."""
    
    def __init__(self, model: str = "gemini-2.5-flash", status_callback=None):
        """Initialize the deep research agent."""
        self.llm = ChatGoogleGenerativeAI(
            model=model, 
            temperature=0.0,
            google_api_key=os.getenv("GEMINI_API_KEY")
        )
        # DuckDuckGo search - free, no API key required
        self.search = DuckDuckGoSearchRun()
        self.status_callback = status_callback
        print("✅ Deep Search initialized with DuckDuckGo (free search)")

    # ----------------- Helper functions -----------------

    def llm_chat(self, prompt: str, system: str = "You are a helpful assistant.") -> str:
        """Synchronous LLM chat."""
        messages = [SystemMessage(content=system), HumanMessage(content=prompt)]
        resp = self.llm.invoke(messages)
        return resp.content

    async def async_llm_chat(self, prompt: str, system: str = "You are a helpful assistant.") -> str:
        """Asynchronous LLM chat."""
        messages = [SystemMessage(content=system), HumanMessage(content=prompt)]
        resp = await self.llm.ainvoke(messages)
        return resp.content


    async def update_status(self, status: str):
        """Send status update via callback if available."""
        if self.status_callback:
            try:
                await self.status_callback(status)
                print(f"📤 Status sent: {status}")
            except Exception as e:
                print(f"❌ Error sending status: {e}")
    
    # ----------------- Node Implementations -----------------

    async def understanding_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the core question and classify intent/sensitivity."""
        await self.update_status("Understanding query...")
        user_input = state.get("input")
        prompt = (
            "You are analyzing a user's search query to find the LATEST and most CURRENT information.\n"
            "Extract the user's core search topic in one short sentence and identify key search terms.\n"
            "Classify the query type:\n"
            "- PERSONAL (user asking about their own emotions or sharing personal info)\n"
            "- INFORMATIONAL (seeking latest news, trends, or current information on a topic)\n\n"
            f"User query: '''{user_input}'''\n\n"
            "Return a JSON object with keys: core_question, intent (PERSONAL/INFORMATIONAL), keywords (list of search terms)."
        )

        resp = await self.async_llm_chat(prompt)

        # Basic extraction using the LLM again to produce stable JSON
        parse_prompt = (
            "Extract only a JSON object with the following fields from the previous assistant answer:\n"
            "core_question, intent, keywords (list of strings).\n\n"
            f"Previous assistant text: '''{resp}'''\n"
        )
        parsed = await self.async_llm_chat(parse_prompt)

        # Final minimal parsing
        try:
            parsed_json = json.loads(parsed)
        except Exception:
            # fallback: craft a safe minimal value
            parsed_json = {"core_question": user_input, "intent": "INFORMATIONAL", "keywords": []}

        state.update({"understanding": parsed_json})
        return state

    async def search_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search for the latest and most current information."""
        await self.update_status("Searching...")
        understanding = state.get("understanding", {})
        core_q = understanding.get("core_question") or state.get("input")

        print(f"\n{'='*60}")
        print(f"🔍 SEARCH NODE - Starting web search")
        print(f"Core question: {core_q}")
        print(f"{'='*60}\n")

        # Create search queries focused on latest information
        query_prompt = (
            "Given the search topic below, create 3 focused search queries to find the LATEST and most CURRENT information.\n"
            "Include terms like 'latest', 'recent', '2024', '2025', 'current', 'news', 'updates' where appropriate.\n\n"
            f"Search topic: '''{core_q}'''\n\n"
            "Return ONLY a JSON array of 3 search query strings. Example: [\"query 1\", \"query 2\", \"query 3\"]\n"
            "Do not include any other text, just the JSON array."
        )
        queries_raw = await self.async_llm_chat(query_prompt)
        
        print(f"📝 Generated queries (raw): {queries_raw[:200]}...")
        
        try:
            # Try to extract JSON from markdown code blocks if present
            import re
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', queries_raw, re.DOTALL)
            if json_match:
                queries_raw = json_match.group(1)
            
            # Also try to find JSON array directly
            if not queries_raw.strip().startswith('['):
                array_match = re.search(r'\[.*?\]', queries_raw, re.DOTALL)
                if array_match:
                    queries_raw = array_match.group(0)
            
            queries = json.loads(queries_raw)
            if not isinstance(queries, list):
                raise ValueError("Not a list")
            print(f"✅ Parsed {len(queries)} queries successfully")
        except Exception as e:
            print(f"⚠️  Failed to parse queries: {e}")
            # Fallback: add "latest" to the original query
            queries = [f"latest {core_q}", f"{core_q} 2024 2025", f"recent {core_q} news"]
            print(f"📌 Using fallback queries: {queries}")

        # For each query, run a web search and collect top results
        all_results: List[Dict[str, Any]] = []

        for idx, q in enumerate(queries[:3]):
            print(f"\n🔎 Query {idx+1}: {q}")
            try:
                serp_resp = self.search.run(q)
                print(f"✅ Search completed. Response length: {len(str(serp_resp))}")
                print(f"📄 Response preview: {str(serp_resp)[:300]}...")
                all_results.append({"query": q, "raw": serp_resp})
            except Exception as e:
                print(f"❌ Search failed: {str(e)}")
                all_results.append({"query": q, "error": str(e)})

        print(f"\n{'='*60}")
        print(f"📊 Search Summary: {len(all_results)} results collected")
        for idx, r in enumerate(all_results):
            if "error" in r:
                print(f"  Result {idx+1}: ERROR - {r['error']}")
            else:
                print(f"  Result {idx+1}: {len(str(r.get('raw', '')))} chars")
        print(f"{'='*60}\n")

        state.update({"search_results": all_results})
        return state

    async def analysis_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze search results and extract the latest information and key insights."""
        await self.update_status("Analyzing...")
        search_results = state.get("search_results", [])
        core_q = state.get("understanding", {}).get("core_question", state.get("input"))

        # Build a prompt to extract latest information and key insights
        prompt = (
            "You are analyzing web search results to extract the LATEST and most CURRENT information.\n"
            "Focus on:\n"
            "(1) Recent developments, news, and updates (prioritize 2024-2025 information)\n"
            "(2) Current trends and patterns\n"
            "(3) Latest statistics, data, or findings\n"
            "(4) Recent expert opinions or statements\n\n"
            "Extract up to 6 key information items. For each include:\n"
            "- title: Brief headline\n"
            "- info: The key information or finding (1-2 sentences)\n"
            "- source: URL or source name if available\n"
            "- recency: How recent (e.g., '2024', 'December 2024', 'Recent')\n"
            "- relevance: Relevance score 1-5\n\n"
            f"Search topic: '''{core_q}'''\n\n"
            "Search results:\n"
        )

        for idx, r in enumerate(search_results):
            prompt += f"---- RESULT {idx+1} (query={r.get('query')}) ----\n{r.get('raw', '')[:1500]}\n\n"

        analyst_resp = await self.async_llm_chat(prompt)

        # Ask LLM to output JSON to structure the findings
        parse_prompt = (
            "Return ONLY a JSON object with keys: findings (array of items), summary (string).\n"
            "Each finding item must have: title, info, source, recency, relevance (1-5).\n"
            "Summary should be 3-5 sentences highlighting the most current and important information.\n\n"
            f"Analysis output: '''{analyst_resp}'''\n"
        )
        parsed = await self.async_llm_chat(parse_prompt)

        try:
            parsed_json = json.loads(parsed)
        except Exception:
            # fallback: minimal structure
            parsed_json = {"findings": [], "summary": analyst_resp}

        state.update({"analysis": parsed_json})
        return state

    async def writer_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create a comprehensive summary of the latest information found."""
        await self.update_status("Writing...")
        analysis = state.get("analysis", {})
        core_q = state.get("understanding", {}).get("core_question", state.get("input"))

        prompt = (
            "You are creating a comprehensive research summary. Generate a well-formatted markdown document.\n\n"
            "IMPORTANT FORMATTING RULES:\n"
            "- Use # for main title (only ONE main title)\n"
            "- Use ## for major sections\n"
            "- Use ### for subsections\n"
            "- Use bullet points (-) for lists\n"
            "- Use **bold** for emphasis on key terms\n"
            "- Use proper spacing between sections (blank lines)\n"
            "- Keep paragraphs concise (2-3 sentences max)\n\n"
            "REQUIRED STRUCTURE:\n"
            "1. Main Title (# format)\n"
            "2. Overview section (## Overview) - 2-3 sentences summarizing what was found\n"
            "3. Key Findings section (## Key Findings) - Bullet points of important information\n"
            "4. Latest Updates section (## Latest Updates) - Recent developments with dates if available\n"
            "5. Current Trends section (## Current Trends) - Patterns or trends identified\n"
            "6. Summary section (## Summary) - Brief conclusion\n\n"
            f"Search topic: '''{core_q}'''\n\n"
            f"Research findings: '''{analysis}'''\n\n"
            "Generate a clean, professional markdown document following the structure above. "
            "Focus on clarity, readability, and proper markdown formatting."
        )

        report = await self.async_llm_chat(prompt)
        state.update({"report": report})
        return state

    async def run(self, user_input: str) -> Dict[str, Any]:
        """Run the full deep research pipeline."""
        state: Dict[str, Any] = {"input": user_input}

        # Execute nodes in sequence
        try:
            await self.update_status("Starting Deep Search...")
            state = await self.understanding_node(state)
            state = await self.search_node(state)
            state = await self.analysis_node(state)
            state = await self.writer_node(state)
        except Exception as e:
            state.setdefault("errors", []).append({"error": str(e)})

        return state


# ----------------- Example Usage -----------------

async def main():
    """Example usage of the DeepResearchAgent for finding latest information."""
    agent = DeepResearchAgent()

    user_query = "What are the latest developments in AI and mental health technology?"

    result = await agent.run(user_query)

    print("--- Latest Information Summary ---\n")
    print(result.get("report", "No report generated"))
    
    if "errors" in result:
        print("\n--- Errors ---")
        for error in result["errors"]:
            print(f"Error: {error}")


if __name__ == "__main__":
    asyncio.run(main())
