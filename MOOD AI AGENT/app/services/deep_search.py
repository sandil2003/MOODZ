"""
Deep Search Agent for finding the latest and most current information on topics

Nodes:
 - Understanding Node: extracts search intent and key terms
 - Search Node: performs web search with queries optimized for latest information
 - Analysis Node: extracts current trends, recent updates, and latest findings
 - Writer Node: Creates comprehensive summary of the most current information found

Dependencies:
 - langchain-openai
 - langchain-core
 - langchain-community
 - python-dotenv
 - google-search-results (serpapi)
"""

from typing import Dict, Any, List
import os
import asyncio
import json
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.utilities import SerpAPIWrapper

# ----------------- Configuration -----------------
load_dotenv()


class DeepResearchAgent:
    """Agent for performing deep search to find the latest and most current information on topics."""
    
    def __init__(self, model: str = "gpt-4o-mini", status_callback=None):
        """Initialize the deep research agent."""
        self.llm = ChatOpenAI(
            temperature=0.0, 
            model=model, 
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.search = SerpAPIWrapper(
            serpapi_api_key=os.getenv("SERPAPI_API_KEY")
        )
        self.status_callback = status_callback

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

    def update_status(self, status: str):
        if self.status_callback:
            self.status_callback(status)
    # ----------------- Node Implementations -----------------

    async def understanding_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the core question and classify intent/sensitivity."""
        self.update_status("Understanding query...")
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
        self.update_status("Searching...")
        understanding = state.get("understanding", {})
        core_q = understanding.get("core_question") or state.get("input")

        # Create search queries focused on latest information
        query_prompt = (
            "Given the search topic below, create 3 focused search queries to find the LATEST and most CURRENT information.\n"
            "Include terms like 'latest', 'recent', '2024', '2025', 'current', 'news', 'updates' where appropriate.\n\n"
            f"Search topic: '''{core_q}'''\n\n"
            "Return a JSON array of 3 search query strings optimized for finding recent information."
        )
        queries_raw = await self.async_llm_chat(query_prompt)
        
        try:
            queries = json.loads(queries_raw)
            if not isinstance(queries, list):
                raise ValueError("Not a list")
        except Exception:
            # Fallback: add "latest" to the original query
            queries = [f"latest {core_q}", f"{core_q} 2024 2025", f"recent {core_q} news"]

        # For each query, run a web search and collect top results
        all_results: List[Dict[str, Any]] = []

        for q in queries[:3]:
            try:
                serp_resp = self.search.run(q)
                all_results.append({"query": q, "raw": serp_resp})
            except Exception as e:
                all_results.append({"query": q, "error": str(e)})

        state.update({"search_results": all_results})
        return state

    async def analysis_node(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze search results and extract the latest information and key insights."""
        self.update_status("Analyzing...")
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
        self.update_status("Writing...")
        analysis = state.get("analysis", {})
        core_q = state.get("understanding", {}).get("core_question", state.get("input"))

        prompt = (
            "You are creating a comprehensive summary of the LATEST INFORMATION found on a topic.\n"
            "Using the findings below, create a well-organized summary that includes:\n"
            "- Title: Clear, descriptive title\n"
            "- Overview: 2-3 sentence overview of what was found\n"
            "- Key Findings: Bullet points of the most important current information\n"
            "- Latest Updates: Recent developments, news, or changes\n"
            "- Current Trends: Patterns or trends identified\n\n"
            f"Search topic: '''{core_q}'''\n\n"
            f"Findings: '''{analysis}'''\n\n"
            "Format the summary in clear, readable Markdown. Focus on recency and relevance."
        )

        report = await self.async_llm_chat(prompt)
        state.update({"report": report})
        return state

    async def run(self, user_input: str) -> Dict[str, Any]:
        """Run the full deep research pipeline."""
        state: Dict[str, Any] = {"input": user_input}

        # Execute nodes in sequence
        try:
            self.update_status("Starting Deep Search...")
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
