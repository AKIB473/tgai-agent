"""
plugins/builtin/web_search.py — Web search via DuckDuckGo (no API key needed).
"""

from __future__ import annotations

import httpx

from tgai_agent.plugins.base_plugin import BasePlugin, PluginError
from tgai_agent.plugins.registry import PluginRegistry
from tgai_agent.utils.logger import get_logger
from tgai_agent.utils.retry import async_retry

log = get_logger(__name__)

DDG_URL = "https://api.duckduckgo.com/"


class WebSearchPlugin(BasePlugin):
    name = "web_search"
    description = "Search the web using DuckDuckGo. Returns top results as text."
    parameter_schema = {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "default": 5},
        },
    }

    @async_retry(max_attempts=2, wait_seconds=1)
    async def execute(self, params: dict, context: dict) -> str:
        query = params.get("query", "").strip()
        if not query:
            raise PluginError("Search query cannot be empty.")

        max_results = min(int(params.get("max_results", 5)), 10)

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                DDG_URL,
                params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                headers={"User-Agent": "TelegramAIAgent/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []

        answer = data.get("Answer", "").strip()
        if answer:
            results.append(f"💡 Answer: {answer}")

        abstract = data.get("AbstractText", "").strip()
        if abstract:
            source = data.get("AbstractSource", "")
            results.append(f"📖 {abstract}" + (f"\n  Source: {source}" if source else ""))

        definition = data.get("Definition", "").strip()
        if definition:
            results.append(f"📚 Definition: {definition}")

        for topic in data.get("RelatedTopics", []):
            if len(results) >= max_results + 2:
                break
            if isinstance(topic, dict) and "Text" in topic:
                url = topic.get("FirstURL", "")
                results.append(f"• {topic['Text']}" + (f"\n  {url}" if url else ""))
            elif isinstance(topic, dict) and "Topics" in topic:
                for sub in topic["Topics"][:2]:
                    if isinstance(sub, dict) and "Text" in sub:
                        results.append(f"• {sub['Text']}")

        for r in data.get("Results", [])[:3]:
            if isinstance(r, dict) and "Text" in r:
                url = r.get("FirstURL", "")
                results.append(f"🔗 {r['Text']}" + (f"\n  {url}" if url else ""))

        if not results:
            return f"No results found for: {query!r}. Try a more specific search term."

        return f"🔍 Search results for '{query}':\n\n" + "\n\n".join(results[:max_results + 2])


# Self-register on import
PluginRegistry.register(WebSearchPlugin())
