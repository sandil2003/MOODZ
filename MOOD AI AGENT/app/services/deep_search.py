"""
LangGraph workflow for a Mood Analysis Agent (Web-search only for Search Node — Option A)

Nodes:
 - Understanding Node: extracts core question and classifies whether user asks personal or informational (for safety)
 - Search Node: performs web search using SerpAPI (or DuckDuckGo) and fetches top evidence
 - Analysis Node: evaluates credibility of sources + creates structured summaries
 - Writer Node: Produces final deep-research report with evidence and action suggestions

Notes:
 - This file uses LangChain for LLM and web search utilities, and a simple LangGraph-style StateGraph.
 - Replace API keys and install dependencies: langchain, langgraph (if available), serpapi, pinecone-client, redis, openai
 - The code is written to be clear and modular — adapt to your environment.

"""

from typing import Dict, Any, List, Tuple
import os
import asyncio
from dotenv import load_dotenv

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.utilities import SerpAPIWrapper

# ----------------- Configuration -----------------
load_dotenv()
SERPAPI_API_KEY = os.environ.get("SERPAPI_API_KEY", "your_serpapi_key_here")


class DeepResearchAgent:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.llm = ChatOpenAI(temperature=0.0, model=model, openai_api_key=os.getenv("OPENAI_API_KEY"))
        self.search = SerpAPIWrapper(serpapi_api_key=os.getenv("SERPAPI_API_KEY"))

    # ----------------- Helper functions -----------------

    def llm_chat(prompt: str, system: str = "You are a helpful assistant.") -> str:
        messages = [SystemMessage(content=system), HumanMessage(content=prompt)]
        resp = llm(messages)
        return resp.content


    async def async_llm_chat(prompt: str, system: str = "You are a helpful assistant.") -> str:
        messages = [SystemMessage(content=system), HumanMessage(content=prompt)]
        resp = await llm.apredict(messages=messages)
        return resp.content


    # ----------------- Node Implementations -----------------

    async def understanding_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the core question and classify intent/sensitivity."""
        user_input = state.get("input")
        prompt = (
            "You are the Understanding Node for a mood analysis assistant.\n"
            "Extract the user's core question in one short sentence and classify whether it's:\n"
            "- PERSONAL (user asking about their own emotions or sharing personal info)\n"
            "- INFORMATIONAL (asking for general research on mood/mental health)\n\n"
            f"User input: '''{user_input}'''\n\n"
            "Return a JSON object with keys: core_question, intent (PERSONAL/INFORMATIONAL), keywords (list)."
        )

        resp = await async_llm_chat(prompt)

        # Try to parse simple model output (we keep it robust to variations)
        # We expect something like: {"core_question": "...", "intent": "INFORMATIONAL", "keywords": ["stress", "students"]}

        # Basic extraction using the LLM again to produce stable JSON
        parse_prompt = (
            "Extract only a JSON object with the following fields from the previous assistant answer:\n"
            "core_question, intent, keywords (list of strings).\n\n"
            f"Previous assistant text: '''{resp}'''\n"
        )
        parsed = await async_llm_chat(parse_prompt)

        # Final minimal parsing — in production use json.loads after validation
        try:
            import json
            parsed_json = json.loads(parsed)
        except Exception:
            # fallback: craft a safe minimal value
            parsed_json = {"core_question": user_input, "intent": "INFORMATIONAL", "keywords": []}

        state.update({"understanding": parsed_json})
        return state


    async def search_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Perform web search for the core question and fetch top N results with snippets and urls."""
        understanding = state.get("understanding", {})
        core_q = understanding.get("core_question") or state.get("input")

        # Create a set of focused queries (decomposition)
        query_prompt = (
            "Given the research question below, suggest 3 focused search queries that will help find high-quality evidence.\n\n"
            f"Research question: '''{core_q}'''\n\n"
            "Return a JSON array of 3 search strings."
        )
        queries_raw = await async_llm_chat(query_prompt)
        try:
            import json
            queries = json.loads(queries_raw)
            if not isinstance(queries, list):
                raise ValueError
        except Exception:
            queries = [core_q]

        # For each query, run a web search and collect top results
        all_results: List[Dict[str, Any]] = []
        max_results_per_query = 3

        for q in queries[:3]:
            try:
                serp_resp = search.run(q)
                # SerpAPIWrapper returns plain text — you can adjust this part to parse structured fields if available
                # We'll include the query, raw_text, and top snippet for traceability
                all_results.append({"query": q, "raw": serp_resp})
            except Exception as e:
                all_results.append({"query": q, "error": str(e)})

        state.update({"search_results": all_results})
        return state


    async def analysis_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate credibility of found sources and summarize findings into evidence items."""
        search_results = state.get("search_results", [])
        core_q = state.get("understanding", {}).get("core_question", state.get("input"))

        # Build a prompt to evaluate credibility and extract key claims/evidence
        prompt = (
            "You are an analyst. Given the research question and the search result texts below,\n"
            "(1) extract up to 6 distinct evidence items relevant to the question. For each item include: title (short), claim (1 sentence), source (url or identifier if present), and a short credibility score (1-5) with reason.\n"
            "(2) then produce a 3-5 sentence concise summary of the overall findings.\n\n"
            f"Research question: '''{core_q}'''\n\n"
            "Search results (raw text or snippets):\n"
        )

        for idx, r in enumerate(search_results):
            prompt += f"---- RESULT {idx+1} (query={r.get('query')}) ----\n{r.get('raw')[:1500]}\n\n"

        analyst_resp = await async_llm_chat(prompt)

        # Ask LLM to output JSON to structure the findings
        parse_prompt = (
            "Now return ONLY a JSON object with keys: evidence (array of items), summary (string).\n"
            "Each evidence item must have: title, claim, source, credibility (1-5), reason.\n\n"
            f"Analyst raw output: '''{analyst_resp}'''\n"
        )
        parsed = await async_llm_chat(parse_prompt)

        try:
            import json
            parsed_json = json.loads(parsed)
        except Exception:
            # fallback: minimal structure
            parsed_json = {"evidence": [], "summary": analyst_resp}

        state.update({"analysis": parsed_json})
        return state


    async def writer_node(state: Dict[str, Any]) -> Dict[str, Any]:
        """Produce the final deep-search report, with an executive summary, evidence list, and recommended actions."""
        analysis = state.get("analysis", {})
        core_q = state.get("understanding", {}).get("core_question", state.get("input"))

        prompt = (
            "You are a professional research writer. Using the analysis and evidence below, produce a deep-search report including:\n"
            "- Title (1 line)\n- Executive summary (3-5 sentences)\n\n"
            f"Research question: '''{core_q}'''\n\n"
            f"Analysis JSON: '''{analysis}'''\n\n"
            "Format the report in Markdown.")

        report = await async_llm_chat(prompt)
        state.update({"report": report})
        return state


    # ----------------- Graph Orchestration -----------------

class MoodLangGraphAgent:
    def __init__(self):
        self.graph_steps = [
            ("understanding", understanding_node),
            ("search", search_node),
            ("analysis", analysis_node),
            ("writer", writer_node),
        ]

    async def run(self, user_input: str) -> Dict[str, Any]:
        state: Dict[str, Any] = {"input": user_input}

        for name, func in self.graph_steps:
            try:
                state = await func(state)
            except Exception as e:
                # graceful error handling: attach error and continue where possible
                state.setdefault("errors", []).append({"step": name, "error": str(e)})
                # break or continue depending on how critical the node is
                break

        return state


# ----------------- Example Usage -----------------

async def main():
    agent = MoodLangGraphAgent()

    user_query = (
        "What are the most evidence-backed interventions to reduce academic-related anxiety in university students?"
    )

    result = await agent.run(user_query)

    print("--- Final Report (Markdown) ---\n")
    print(result.get("report"))


if __name__ == "__main__":
    asyncio.run(main())
