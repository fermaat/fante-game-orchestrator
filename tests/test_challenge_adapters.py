"""Functional tests for challenge adapters and the dispatcher."""

import random

import pytest

from fante.adapters.automatic_challenge import AutomaticChallenge
from fante.adapters.color_naming_challenge import ColorNamingChallenge
from fante.adapters.math_quick_challenge import MathQuickChallenge
from fante.adapters.repeat_expression_challenge import RepeatExpressionChallenge
from fante.challenge.dispatcher import ChallengeDispatcher
from fante.domain.challenge import ChallengeSpec
from fante.domain.profile import Attributes, PlayerProfile

from tests.conftest import FakeInput, FakeOutput


def _profile() -> PlayerProfile:
    return PlayerProfile(name="Fante", attributes=Attributes(strength=3), age=6)


def _spec(adapter_id: str, **config) -> ChallengeSpec:  # type: ignore[no-untyped-def]
    return ChallengeSpec(
        id=adapter_id,
        adapter_id=adapter_id,
        prompt="prompt",
        category="physical",
        metadata={"config": config},
    )


@pytest.mark.functional
def test_automatic_returns_zero() -> None:
    score = AutomaticChallenge().run(_spec("automatic"), "trepo", _profile())
    assert score == 0


@pytest.mark.functional
def test_math_correct_answer_returns_high_score() -> None:
    out = FakeOutput()
    in_ = FakeInput(["8"])  # whatever the problem, we'll seed rng to make 3+5
    rng = random.Random(0)
    adapter = MathQuickChallenge(in_, out, rng=rng)
    spec = _spec("math_quick", operations=["add"], max_operand=10)
    # Use a more reliable approach: read what the prompt asked and answer accordingly
    in_._lines.clear()
    # Replay the same rng sequence the adapter will consume to compute the answer:
    rng2 = random.Random(0)
    op = rng2.choice(["add"])
    a = rng2.randint(1, 10)
    b = rng2.randint(1, 10)
    expected = a + b if op == "add" else a - b
    in_._lines.append(str(expected))
    score = adapter.run(spec, "trepo", _profile())
    assert score == 18


@pytest.mark.functional
def test_math_wrong_answer_returns_partial() -> None:
    in_ = FakeInput(["9999"])
    out = FakeOutput()
    adapter = MathQuickChallenge(in_, out, rng=random.Random(0))
    spec = _spec("math_quick", operations=["add"], max_operand=10)
    score = adapter.run(spec, "trepo", _profile())
    assert 0 < score < 18


@pytest.mark.functional
def test_math_garbage_answer_returns_low_score() -> None:
    in_ = FakeInput(["catorce"])
    out = FakeOutput()
    adapter = MathQuickChallenge(in_, out, rng=random.Random(0))
    spec = _spec("math_quick", operations=["add"], max_operand=10)
    score = adapter.run(spec, "trepo", _profile())
    assert 0 < score < 10


@pytest.mark.functional
def test_color_correct_normalized() -> None:
    out = FakeOutput()
    in_ = FakeInput(["MARRON"])  # uppercase, no accent
    adapter = ColorNamingChallenge(in_, out, rng=random.Random(0))
    spec = _spec(
        "color_naming",
        pool=[{"prompt": "color?", "accepted": ["marrón"]}],
    )
    score = adapter.run(spec, "trepo", _profile())
    assert score == 17


@pytest.mark.functional
def test_color_ignores_trailing_punctuation() -> None:
    out = FakeOutput()
    in_ = FakeInput(["blanca,"])  # comma artifact from STT or typing
    adapter = ColorNamingChallenge(in_, out, rng=random.Random(0))
    spec = _spec(
        "color_naming",
        pool=[{"prompt": "¿De qué color es la nieve?", "accepted": ["blanco", "blanca"]}],
    )
    score = adapter.run(spec, "trepo", _profile())
    assert score == 17


@pytest.mark.functional
def test_color_unknown_returns_partial() -> None:
    out = FakeOutput()
    in_ = FakeInput(["rojo"])
    adapter = ColorNamingChallenge(in_, out, rng=random.Random(0))
    spec = _spec(
        "color_naming",
        pool=[{"prompt": "color?", "accepted": ["marrón"]}],
    )
    score = adapter.run(spec, "trepo", _profile())
    assert 0 < score < 15


@pytest.mark.functional
def test_repeat_full_match_returns_high_score() -> None:
    out = FakeOutput()
    in_ = FakeInput(["trepa trepa trepa"])
    adapter = RepeatExpressionChallenge(in_, out, rng=random.Random(0))
    spec = _spec("repeat_expression", pool=[{"expression": "trepa trepa trepa"}])
    score = adapter.run(spec, "trepo", _profile())
    assert score == 18


@pytest.mark.functional
def test_repeat_partial_overlap_passes_when_half_covered() -> None:
    out = FakeOutput()
    in_ = FakeInput(["UNO DOS"])  # 2 of 3 tokens
    adapter = RepeatExpressionChallenge(in_, out, rng=random.Random(0))
    spec = _spec("repeat_expression", pool=[{"expression": "uno dos tres"}])
    score = adapter.run(spec, "trepo", _profile())
    assert score == 18


@pytest.mark.functional
def test_repeat_too_little_overlap_returns_tried() -> None:
    out = FakeOutput()
    in_ = FakeInput(["pelota azul"])  # zero overlap
    adapter = RepeatExpressionChallenge(in_, out, rng=random.Random(0))
    spec = _spec("repeat_expression", pool=[{"expression": "uno dos tres"}])
    score = adapter.run(spec, "trepo", _profile())
    assert score == 10


@pytest.mark.functional
def test_repeat_empty_input_returns_low_score() -> None:
    out = FakeOutput()
    in_ = FakeInput([""])
    adapter = RepeatExpressionChallenge(in_, out, rng=random.Random(0))
    spec = _spec("repeat_expression", pool=[{"expression": "trepa"}])
    score = adapter.run(spec, "trepo", _profile())
    assert score == 5


@pytest.mark.functional
def test_repeat_ignores_accents_and_punctuation() -> None:
    out = FakeOutput()
    in_ = FakeInput(["abracadabra"])  # without exclamation marks
    adapter = RepeatExpressionChallenge(in_, out, rng=random.Random(0))
    spec = _spec("repeat_expression", pool=[{"expression": "¡abracadabra!"}])
    score = adapter.run(spec, "trepo", _profile())
    assert score == 18


@pytest.mark.functional
def test_dispatcher_routes_to_correct_adapter() -> None:
    out = FakeOutput()
    in_a = FakeInput(["x"])
    in_b = FakeInput(["y"])

    class _Fake:
        def __init__(self, score: int, in_port) -> None:  # type: ignore[no-untyped-def]
            self.score = score
            self._in = in_port

        def run(self, spec, user_input, profile) -> int:  # type: ignore[no-untyped-def]
            self._in.read()  # consume
            return self.score

    disp = ChallengeDispatcher({"a": _Fake(10, in_a), "b": _Fake(20, in_b)})
    assert disp.run(_spec("a"), "u", _profile()) == 10
    assert disp.run(_spec("b"), "u", _profile()) == 20


@pytest.mark.functional
def test_dispatcher_raises_on_unknown_adapter() -> None:
    disp = ChallengeDispatcher({})
    with pytest.raises(KeyError):
        disp.run(_spec("missing"), "u", _profile())
