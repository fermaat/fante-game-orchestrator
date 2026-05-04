"""Functional tests for the full action-turn pipeline in GameManager."""

import pytest

from fante.domain.profile import Attributes, PlayerProfile
from fante.domain.rules import CheckResult, PlotDieFace
from fante.domain.turn import ActionIntent
from fante.events.bus import EventBus


def _make_check_result(rule_id: str = "climb", success: bool = True) -> CheckResult:
    return CheckResult(
        rule_id=rule_id,
        pack_name="physics_basic",
        d20_rolls=[15],
        kept_roll=15,
        attribute_bonus=3,
        skill_bonus=0,
        situational_modifier=0,
        total=18,
        difficulty=12,
        success=success,
        plot_dice=[PlotDieFace.OPPORTUNITY],
        applied_modifiers=[],
        narration_seed="El personaje trepa con agilidad.",
    )


class FakeClassifier:
    def __init__(self, intent: ActionIntent | None) -> None:
        self._intent = intent
        self.calls: list[tuple[str, str]] = []

    def classify(self, player_input: str, player_name: str) -> ActionIntent | None:
        self.calls.append((player_input, player_name))
        return self._intent


class FakeEvaluator:
    def __init__(self, score: int = 14) -> None:
        self._score = score
        self.calls: list[tuple[str, object]] = []

    def score(self, player_input: str, profile: object, context: object = None) -> int:
        self.calls.append((player_input, profile))
        return self._score


@pytest.mark.functional
def test_no_classifier_goes_straight_to_narrator(make_game) -> None:  # type: ignore[no-untyped-def]
    game, _, out, narrator = make_game(
        narrator_responses=["narración directa"],
        input_lines=["hola", None],
    )
    game.run()
    assert narrator.received == ["hola"]
    assert narrator.received_check_results == [None]


@pytest.mark.functional
def test_classifier_none_skips_check(make_game) -> None:  # type: ignore[no-untyped-def]
    from tests.conftest import FakeRulesPort

    game, _, out, narrator = make_game(
        narrator_responses=["sin acción"],
        input_lines=["hola", None],
    )
    clf = FakeClassifier(intent=None)
    game._classifier = clf
    game._rules = FakeRulesPort()
    game.run()
    assert narrator.received_check_results == [None]
    assert len(clf.calls) == 1


@pytest.mark.functional
def test_action_turn_skill_mode_calls_evaluator(make_game) -> None:  # type: ignore[no-untyped-def]
    from tests.conftest import FakeRulesPort

    rules = FakeRulesPort()
    rules.set_check_result(_make_check_result())
    clf = FakeClassifier(intent=ActionIntent(rule_id="climb", context={"surface": "dry"}))
    ev = FakeEvaluator(score=16)

    game, _, out, narrator = make_game(
        narrator_responses=["trepas con éxito"],
        input_lines=["trepo", None],
    )
    game._classifier = clf
    game._rules = rules
    game._evaluator = ev
    game._mode = "skill"
    game.run()

    assert len(ev.calls) == 1
    assert narrator.received_check_results[0] is not None
    assert narrator.received_check_results[0].success is True


@pytest.mark.functional
def test_action_turn_dice_mode_skips_evaluator(make_game) -> None:  # type: ignore[no-untyped-def]
    from tests.conftest import FakeRulesPort

    rules = FakeRulesPort()
    rules.set_check_result(_make_check_result())
    clf = FakeClassifier(intent=ActionIntent(rule_id="climb"))
    ev = FakeEvaluator(score=18)

    game, _, out, narrator = make_game(
        narrator_responses=["trepas"],
        input_lines=["trepo", None],
    )
    game._classifier = clf
    game._rules = rules
    game._evaluator = ev
    game._mode = "dice"
    game.run()

    assert len(ev.calls) == 0


@pytest.mark.functional
def test_mode_toggle_via_set_mode(make_game) -> None:  # type: ignore[no-untyped-def]
    game, _, _, _ = make_game(input_lines=[None])
    assert game.mode == "skill"
    game.set_mode("dice")
    assert game.mode == "dice"
    game.set_mode("skill")
    assert game.mode == "skill"


@pytest.mark.functional
def test_action_classified_and_check_resolved_events_published(make_game) -> None:  # type: ignore[no-untyped-def]
    from fante.domain.events import ActionClassified, CheckResolved
    from tests.conftest import FakeRulesPort

    rules = FakeRulesPort()
    rules.set_check_result(_make_check_result())
    clf = FakeClassifier(intent=ActionIntent(rule_id="climb"))

    received: list[object] = []
    game, _, _, narrator = make_game(
        narrator_responses=["ok"],
        input_lines=["trepo", None],
    )
    game._classifier = clf
    game._rules = rules
    game._bus.subscribe(ActionClassified, lambda e: received.append(e))
    game._bus.subscribe(CheckResolved, lambda e: received.append(e))
    game.run()

    types = [type(e) for e in received]
    assert ActionClassified in types
    assert CheckResolved in types
