"""
plugins/builtin/summarizer.py — Summarise any URL using AI.
"""

from __future__ import annotations

from html.parser import HTMLParser

import httpx

from tgai_agent.ai_core.base_provider import AIMessage
from tgai_agent.ai_core.router import complete
from tgai_agent.plugins.base_plugin import BasePlugin, PluginError
from tgai_agent.plugins.registry import PluginRegistry
from tgai_agent.utils.helpers import truncate
from tgai_agent.utils.logger import get_logger
from tgai_agent.utils.retry import async_retry

log = get_logger(__name__)


class _TextExtractor(HTMLParser):
    """Minimal HTML → plain text extractor."""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip and data.strip():
            self._parts.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self._parts)


class SummarizerPlugin(BasePlugin):
    name = "summarize_url"
    description = "Fetch a URL and produce an AI-generated summary."
    parameter_schema = {
        "type": "object",
        "required": ["url"],
        "properties": {
            "url": {"type": "string"},
            "focus": {"type": "string", "description": "What aspect to focus on (optional)"},
        },
    }

    @async_retry(max_attempts=2, wait_seconds=2)
    async def execute(self, params: dict, context: dict) -> str:
        url = params.get("url", "").strip()
        if not url:
            raise PluginError("URL is required.")

        focus = params.get("focus", "")
        user_id = context.get("user_id", 0)

        # Fetch page
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 TelegramAIAgent/1.0"},
                )
                resp.raise_for_status()
                html = resp.text
        except httpx.HTTPError as exc:
            raise PluginError(f"Failed to fetch URL: {exc}") from exc

        # Extract text
        parser = _TextExtractor()
        parser.feed(html)
        raw_text = truncate(parser.get_text(), 8000)

        focus_note = f" Focus especially on: {focus}." if focus else ""
        messages = [
            AIMessage(
                "system",
                f"You are a precise summariser. Provide a clear, structured summary.{focus_note}",
            ),
            AIMessage("user", f"Please summarise the following web page content:\n\n{raw_text}"),
        ]

        summary = await complete(user_id, "openai", messages, max_tokens=512)
        return f"📄 Summary of {url}:\n\n{summary}"


# Self-register
PluginRegistry.register(SummarizerPlugin())
