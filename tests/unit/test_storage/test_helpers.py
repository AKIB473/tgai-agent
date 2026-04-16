"""Tests for utility helpers."""

import pytest
from tgai_agent.utils.helpers import (
    chunk_list,
    flatten,
    parse_duration,
    sanitise_markdown,
    truncate,
)


def test_truncate_short():
    assert truncate("hello", 100) == "hello"


def test_truncate_long():
    result = truncate("a" * 200, 50)
    assert len(result) == 50
    assert result.endswith("...")


def test_chunk_list():
    assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_list_empty():
    assert chunk_list([], 3) == []


def test_flatten():
    assert flatten([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]


@pytest.mark.parametrize("text,expected", [
    ("5s", 5),
    ("3m", 180),
    ("2h", 7200),
    ("1d", 86400),
])
def test_parse_duration(text, expected):
    assert parse_duration(text) == expected


def test_parse_duration_invalid():
    with pytest.raises(ValueError):
        parse_duration("10x")


def test_sanitise_markdown_escapes_special():
    result = sanitise_markdown("Hello *world* (test)!")
    assert "\\*" in result
    assert "\\(" in result
