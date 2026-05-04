"""Tests for MCPRulesAdapter — unit (mocked) and integration (live server)."""

import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from fante.domain.actor import Actor
from fante.domain.profile import Attributes
from fante.domain.rules import CheckResult, PlotDieFace, RollResult

# ---------- Unit: exercise RulesPort contract against FakeRulesPort -----------


@pytest.mark.unit
def test_fake_rules_port_roll(sample_profile):
    from tests.conftest import FakeRulesPort

    rules = FakeRulesPort()
    result = rules.roll("1d20")
    assert isinstance(result, RollResult)
    assert result.spec == "1d20"


@pytest.mark.unit
def test_fake_rules_port_check_returns_success(sample_profile):
    from tests.conftest import FakeRulesPort

    from fante.domain.actor import profile_to_actor

    rules = FakeRulesPort()
    actor = profile_to_actor(sample_profile)
    result = rules.check("climb", actor)
    assert isinstance(result, CheckResult)
    assert result.success is True


@pytest.mark.unit
def test_fake_rules_port_check_configurable():
    from tests.conftest import FakeRulesPort

    rules = FakeRulesPort()
    custom = CheckResult(
        rule_id="dodge",
        pack_name="physics",
        d20_rolls=[],
        kept_roll=15,
        attribute_bonus=2,
        skill_bonus=1,
        situational_modifier=0,
        total=18,
        difficulty=12,
        success=True,
        plot_dice=[PlotDieFace.OPPORTUNITY],
        applied_modifiers=[],
        narration_seed="El personaje esquiva con agilidad.",
    )
    rules.set_check_result(custom)
    actor = Actor(name="Test", attributes=Attributes(), skills={}, tags=[])
    result = rules.check("dodge", actor)
    assert result.rule_id == "dodge"
    assert result.narration_seed == "El personaje esquiva con agilidad."
    assert result.skill_mode is True  # d20_rolls == []


# ---------- Integration: spawns the real mcp-game-rules server ---------------


@pytest.mark.integration
def test_mcp_adapter_roll_round_trip():
    from fante.adapters.mcp_rules import MCPRulesAdapter

    adapter = MCPRulesAdapter(command=[sys.executable, "-m", "mcp_game_rules"])
    try:
        result = adapter.roll("1d20")
        assert isinstance(result, RollResult)
        assert 1 <= result.total <= 20
    finally:
        adapter.close()


@pytest.mark.integration
def test_mcp_adapter_check_climb():
    from fante.adapters.mcp_rules import MCPRulesAdapter
    from fante.domain.actor import profile_to_actor

    adapter = MCPRulesAdapter(command=[sys.executable, "-m", "mcp_game_rules"])
    try:
        actor = Actor(
            name="Fante",
            attributes=Attributes(strength=3, speed=4),
            skills={},
            tags=[],
        )
        result = adapter.check("climb", actor, context={"surface": "dry"})
        assert isinstance(result, CheckResult)
        assert result.rule_id == "climb"
        assert result.total == (
            result.kept_roll
            + result.attribute_bonus
            + result.skill_bonus
            + result.situational_modifier
        )
    finally:
        adapter.close()


@pytest.mark.integration
def test_mcp_adapter_check_skill_mode():
    from fante.adapters.mcp_rules import MCPRulesAdapter

    adapter = MCPRulesAdapter(command=[sys.executable, "-m", "mcp_game_rules"])
    try:
        actor = Actor(name="Fante", attributes=Attributes(strength=3), skills={}, tags=[])
        result = adapter.check("climb", actor, player_score=14)
        assert result.skill_mode  # d20_rolls == []
        assert result.kept_roll == 14
    finally:
        adapter.close()
