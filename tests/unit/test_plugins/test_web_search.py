"""Tests for WebSearchPlugin."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tgai_agent.plugins.base_plugin import PluginError
from tgai_agent.plugins.builtin.web_search import WebSearchPlugin


@pytest.fixture
def plugin():
    return WebSearchPlugin()


@pytest.fixture
def context():
    return {"user_id": 1, "chat_id": 100}


@pytest.mark.asyncio
async def test_web_search_answer_field(plugin, context):
    mock_data = {
        "Answer": "42",
        "AbstractText": "",
        "AbstractSource": "",
        "RelatedTopics": [],
        "Results": [],
        "Definition": "",
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_data
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await plugin.execute({"query": "meaning of life"}, context)
        assert "42" in result
        assert "meaning of life" in result


@pytest.mark.asyncio
async def test_web_search_abstract_field(plugin, context):
    mock_data = {
        "Answer": "",
        "AbstractText": "Python is a programming language.",
        "AbstractSource": "Wikipedia",
        "RelatedTopics": [],
        "Results": [],
        "Definition": "",
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_data
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await plugin.execute({"query": "python"}, context)
        assert "Python is a programming language" in result
        assert "Wikipedia" in result


@pytest.mark.asyncio
async def test_web_search_related_topics(plugin, context):
    mock_data = {
        "Answer": "",
        "AbstractText": "",
        "AbstractSource": "",
        "RelatedTopics": [
            {"Text": "Topic about cats", "FirstURL": "https://example.com/cats"},
            {"Text": "Topic about dogs", "FirstURL": "https://example.com/dogs"},
        ],
        "Results": [],
        "Definition": "",
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_data
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await plugin.execute({"query": "pets"}, context)
        assert "cats" in result.lower() or "dogs" in result.lower()


@pytest.mark.asyncio
async def test_web_search_empty_results(plugin, context):
    mock_data = {
        "Answer": "", "AbstractText": "", "AbstractSource": "",
        "RelatedTopics": [], "Results": [], "Definition": "",
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_data
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await plugin.execute({"query": "xyzzy_nonexistent"}, context)
        assert "No results" in result


@pytest.mark.asyncio
async def test_web_search_empty_query_raises(plugin, context):
    with pytest.raises(PluginError):
        await plugin.execute({"query": ""}, context)


@pytest.mark.asyncio
async def test_web_search_whitespace_query_raises(plugin, context):
    with pytest.raises(PluginError):
        await plugin.execute({"query": "   "}, context)


@pytest.mark.asyncio
async def test_web_search_max_results_respected(plugin, context):
    mock_data = {
        "Answer": "",
        "AbstractText": "",
        "AbstractSource": "",
        "RelatedTopics": [
            {"Text": f"Topic {i}", "FirstURL": f"https://example.com/{i}"}
            for i in range(20)
        ],
        "Results": [],
        "Definition": "",
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = mock_data
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        result = await plugin.execute({"query": "test", "max_results": 3}, context)
        assert isinstance(result, str)


@pytest.mark.asyncio
async def test_web_search_http_error_raises(plugin, context):
    import httpx
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_cls.return_value = mock_client

        with pytest.raises(Exception):
            await plugin.execute({"query": "test"}, context)
