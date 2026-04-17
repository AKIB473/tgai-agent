"""Extended helper function tests."""

from datetime import UTC, timezone

import pytest

from tgai_agent.utils.helpers import (
    chunk_list,
    flatten,
    hash_user_id,
    parse_duration,
    sanitise_markdown,
    truncate,
    utcnow,
)

# ── truncate ──────────────────────────────────────────────────────────────────


def test_truncate_short_string():
    assert truncate("hi", 10) == "hi"


def test_truncate_exact_length():
    assert truncate("hello", 5) == "hello"


def test_truncate_long_string():
    result = truncate("hello world", 8)
    assert len(result) == 8
    assert result.endswith("...")


def test_truncate_adds_ellipsis():
    result = truncate("abcdefghij", 6)
    assert result == "abc..."


def test_truncate_empty_string():
    assert truncate("", 5) == ""


# ── parse_duration ────────────────────────────────────────────────────────────


def test_parse_duration_seconds():
    assert parse_duration("30s") == 30


def test_parse_duration_minutes():
    assert parse_duration("5m") == 300


def test_parse_duration_hours():
    assert parse_duration("2h") == 7200


def test_parse_duration_days():
    assert parse_duration("1d") == 86400


def test_parse_duration_uppercase():
    assert parse_duration("10M") == 600


def test_parse_duration_invalid_unit():
    with pytest.raises(ValueError):
        parse_duration("5x")


def test_parse_duration_no_unit():
    with pytest.raises(ValueError):
        parse_duration("100")


def test_parse_duration_empty():
    with pytest.raises(ValueError):
        parse_duration("")


def test_parse_duration_with_spaces():
    assert parse_duration("  5m  ") == 300


# ── chunk_list ────────────────────────────────────────────────────────────────


def test_chunk_list_even():
    assert chunk_list([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]


def test_chunk_list_uneven():
    assert chunk_list([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]


def test_chunk_list_empty():
    assert chunk_list([], 3) == []


def test_chunk_list_size_one():
    assert chunk_list([1, 2, 3], 1) == [[1], [2], [3]]


def test_chunk_list_size_larger_than_list():
    assert chunk_list([1, 2], 10) == [[1, 2]]


# ── flatten ───────────────────────────────────────────────────────────────────


def test_flatten_basic():
    assert flatten([[1, 2], [3, 4], [5]]) == [1, 2, 3, 4, 5]


def test_flatten_empty():
    assert flatten([]) == []


def test_flatten_single():
    assert flatten([[1, 2, 3]]) == [1, 2, 3]


# ── hash_user_id ──────────────────────────────────────────────────────────────


def test_hash_user_id_consistent():
    h1 = hash_user_id(12345)
    h2 = hash_user_id(12345)
    assert h1 == h2


def test_hash_user_id_length():
    h = hash_user_id(12345)
    assert len(h) == 12


def test_hash_user_id_different_inputs():
    assert hash_user_id(111) != hash_user_id(222)


def test_hash_user_id_is_hex():
    h = hash_user_id(99999)
    int(h, 16)  # should not raise


# ── utcnow ────────────────────────────────────────────────────────────────────


def test_utcnow_returns_utc():
    dt = utcnow()
    assert dt.tzinfo == UTC


def test_utcnow_is_datetime():
    from datetime import datetime

    dt = utcnow()
    assert isinstance(dt, datetime)


# ── sanitise_markdown ─────────────────────────────────────────────────────────


def test_sanitise_markdown_escapes_asterisk():
    result = sanitise_markdown("*bold*")
    assert "\\*" in result


def test_sanitise_markdown_escapes_underscore():
    result = sanitise_markdown("_italic_")
    assert "\\_" in result


def test_sanitise_markdown_plain_text_unchanged():
    result = sanitise_markdown("hello world")
    assert result == "hello world"
