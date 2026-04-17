"""
Tests for agent_manager/roles/presets.py
"""

from __future__ import annotations

import pytest

from tgai_agent.agent_manager.roles.presets import (
    AGENT_PRESETS,
    get_preset,
    get_preset_display,
    list_presets,
)

EXPECTED_ROLES = [
    "researcher",
    "coder",
    "writer",
    "analyst",
    "assistant",
    "translator",
    "summarizer",
    "tutor",
]


class TestAgentPresets:
    def test_all_expected_roles_present(self):
        for role in EXPECTED_ROLES:
            assert role in AGENT_PRESETS, f"Missing preset: {role}"

    def test_preset_count(self):
        assert len(AGENT_PRESETS) >= 8

    def test_each_preset_has_required_fields(self):
        for role, preset in AGENT_PRESETS.items():
            assert "role" in preset, f"{role} missing 'role'"
            assert "description" in preset, f"{role} missing 'description'"
            assert "emoji" in preset, f"{role} missing 'emoji'"
            assert "system_prompt" in preset, f"{role} missing 'system_prompt'"
            assert preset["system_prompt"].strip(), f"{role} has empty system_prompt"

    def test_each_preset_role_matches_key(self):
        for key, preset in AGENT_PRESETS.items():
            assert preset["role"] == key, f"Key {key!r} doesn't match role {preset['role']!r}"


class TestGetPreset:
    def test_get_existing_preset(self):
        result = get_preset("researcher")
        assert result is not None
        assert result["role"] == "researcher"

    def test_get_preset_case_insensitive(self):
        assert get_preset("RESEARCHER") is not None
        assert get_preset("Coder") is not None

    def test_get_nonexistent_preset_returns_none(self):
        assert get_preset("nonexistent_role_xyz") is None

    @pytest.mark.parametrize("role", EXPECTED_ROLES)
    def test_get_all_presets(self, role: str):
        result = get_preset(role)
        assert result is not None
        assert result["role"] == role


class TestListPresets:
    def test_returns_list(self):
        result = list_presets()
        assert isinstance(result, list)

    def test_contains_all_expected_roles(self):
        result = list_presets()
        for role in EXPECTED_ROLES:
            assert role in result

    def test_length(self):
        assert len(list_presets()) >= 8


class TestGetPresetDisplay:
    def test_returns_string(self):
        result = get_preset_display("researcher")
        assert isinstance(result, str)

    def test_contains_emoji(self):
        result = get_preset_display("researcher")
        assert "🔬" in result

    def test_contains_role_name(self):
        result = get_preset_display("coder")
        assert "Coder" in result

    def test_unknown_role_returns_default_emoji(self):
        result = get_preset_display("unknown_role")
        assert "🤖" in result

    @pytest.mark.parametrize("role", EXPECTED_ROLES)
    def test_display_for_all_presets(self, role: str):
        result = get_preset_display(role)
        assert len(result) > 1
        assert role.title() in result
