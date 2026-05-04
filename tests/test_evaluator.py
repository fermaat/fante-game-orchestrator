"""Tests for LLMPerformanceEvaluator."""

import pytest

from fante.domain.profile import Attributes, PlayerProfile


@pytest.fixture
def profile() -> PlayerProfile:
    return PlayerProfile(
        name="Fante",
        attributes=Attributes(strength=3, speed=4),
    )


@pytest.mark.functional
def test_evaluator_returns_score_in_range(profile: PlayerProfile) -> None:
    from tests.conftest import MockProvider

    from fante.adapters.llm_evaluator import LLMPerformanceEvaluator

    provider = MockProvider(["14"])
    ev = LLMPerformanceEvaluator(provider=provider, prompt_path=None)
    score = ev.score("¡quiero trepar!", profile)
    assert 1 <= score <= 20
    assert score == 14


@pytest.mark.functional
def test_evaluator_fallback_on_non_integer(profile: PlayerProfile) -> None:
    from tests.conftest import MockProvider

    from fante.adapters.llm_evaluator import LLMPerformanceEvaluator

    provider = MockProvider(["no sé"])
    ev = LLMPerformanceEvaluator(provider=provider, fallback_score=7, prompt_path=None)
    score = ev.score("bla", profile)
    assert score == 7


@pytest.mark.functional
def test_evaluator_fallback_on_out_of_range(profile: PlayerProfile) -> None:
    from tests.conftest import MockProvider

    from fante.adapters.llm_evaluator import LLMPerformanceEvaluator

    provider = MockProvider(["25"])
    ev = LLMPerformanceEvaluator(provider=provider, fallback_score=12, prompt_path=None)
    score = ev.score("algo", profile)
    assert score == 12


@pytest.mark.functional
def test_evaluator_parses_score_with_trailing_text(profile: PlayerProfile) -> None:
    from tests.conftest import MockProvider

    from fante.adapters.llm_evaluator import LLMPerformanceEvaluator

    provider = MockProvider(["16 (muy involucrado)"])
    ev = LLMPerformanceEvaluator(provider=provider, prompt_path=None)
    score = ev.score("¡corro!", profile)
    assert score == 16
