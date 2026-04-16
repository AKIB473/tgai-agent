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

        # Abstract (main answer)
        abstract = data.get("AbstractText", "").strip()
        if abstract:
            results.append(f"📖 Summary: {abstract}")

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                url = topic.get("FirstURL", "")
                text = topic["Text"]
                results.append(f"• {text}\n  {url}")

        if not results:
            return f"No results found for: {query!r}"

        return f"🔍 Search results for '{query}':\n\n" + "\n\n".join(results)


# Self-register on import
PluginRegistry.register(WebSearchPlugin())
