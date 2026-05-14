"""Functional tests for `ChallengeRegistry` + `ChallengeSelector`."""

import random
from pathlib import Path

import pytest

from fante.challenge.registry import ChallengeDef, ChallengeRegistry
from fante.challenge.selector import ChallengeSelector
from fante.domain.challenge import RuleMeta
from fante.domain.profile import Attributes, PlayerProfile


def _profile(age: int | None = 6) -> PlayerProfile:
    return PlayerProfile(
        name="Fante",
        attributes=Attributes(strength=3, intellect=4, speed=4, awareness=4),
        age=age,
    )


def _meta(
    challenge: str = "optional",
    category: str | None = "physical",
    attribute: str | None = "strength",
) -> RuleMeta:
    return RuleMeta(
        rule_id="climb",
        pack_name="physics_basic",
        attribute=attribute,
        skill=None,
        base_difficulty=10,
        knowledge_topic=None,
        challenge=challenge,  # type: ignore[arg-type]
        challenge_category=category,  # type: ignore[arg-type]
    )


def _def(
    id: str,
    categories: tuple[str, ...] = ("physical",),
    attributes: tuple[str, ...] = (),
    topics: tuple[str, ...] = (),
    min_age: int = 0,
    max_age: int = 99,
) -> ChallengeDef:
    return ChallengeDef(
        id=id,
        adapter_id=id,
        categories=categories,  # type: ignore[arg-type]
        attributes=attributes,
        topics=topics,
        min_age=min_age,
        max_age=max_age,
        prompt="",
    )


@pytest.mark.functional
def test_challenge_none_returns_none() -> None:
    sel = ChallengeSelector(ChallengeRegistry([_def("x")]))
    assert sel.pick(_meta(challenge="none"), None, _profile()) is None


@pytest.mark.functional
def test_optional_below_probability_returns_none() -> None:
    # Seed chosen so the first random() call returns > 0.5, gating "optional" out.
    sel = ChallengeSelector(
        ChallengeRegistry([_def("x")]),
        optional_activation_prob=0.5,
        rng=random.Random(2),  # first random() == 0.956... > 0.5
    )
    assert sel.pick(_meta(challenge="optional"), None, _profile()) is None


@pytest.mark.functional
def test_required_picks_a_minigame_when_matching() -> None:
    sel = ChallengeSelector(
        ChallengeRegistry([_def("x", categories=("physical",), attributes=("strength",))]),
        rng=random.Random(42),
    )
    spec = sel.pick(_meta(challenge="required"), None, _profile())
    assert spec is not None
    assert spec.id == "x"


@pytest.mark.functional
def test_filter_excludes_wrong_category() -> None:
    sel = ChallengeSelector(
        ChallengeRegistry([_def("only_mental", categories=("mental",))]),
        rng=random.Random(42),
    )
    assert sel.pick(_meta(challenge="required", category="physical"), None, _profile()) is None


@pytest.mark.functional
def test_filter_excludes_wrong_attribute() -> None:
    sel = ChallengeSelector(
        ChallengeRegistry([_def("only_intellect", attributes=("intellect",))]),
        rng=random.Random(42),
    )
    assert sel.pick(_meta(challenge="required", attribute="strength"), None, _profile()) is None


@pytest.mark.functional
def test_filter_excludes_wrong_age() -> None:
    sel = ChallengeSelector(
        ChallengeRegistry([_def("teen_only", min_age=12, max_age=18)]),
        rng=random.Random(42),
    )
    assert sel.pick(_meta(challenge="required"), None, _profile(age=6)) is None


@pytest.mark.functional
def test_recent_history_excludes_last_pick() -> None:
    defs = [_def("a"), _def("b")]
    sel = ChallengeSelector(
        ChallengeRegistry(defs),
        recent_history_size=2,
        rng=random.Random(0),
    )
    # First pick goes in history; subsequent calls must avoid it until evicted.
    first = sel.pick(_meta(challenge="required"), None, _profile())
    assert first is not None
    second = sel.pick(_meta(challenge="required"), None, _profile())
    assert second is not None
    assert second.id != first.id


@pytest.mark.functional
def test_topic_bias_skews_distribution() -> None:
    defs = [
        _def("plain"),
        _def("biased", topics=("math",)),
    ]
    counts: dict[str, int] = {"plain": 0, "biased": 0}
    # Many trials, no recent-history exclusion in effect within a single trial
    for seed in range(200):
        sel = ChallengeSelector(
            ChallengeRegistry(defs),
            recent_history_size=0,
            topic_bias_weight=5.0,
            rng=random.Random(seed),
        )
        spec = sel.pick(_meta(challenge="required"), "math", _profile())
        if spec:
            counts[spec.id] += 1
    # With a 5x weight on the biased one, it should clearly dominate.
    assert counts["biased"] > counts["plain"] * 2


@pytest.mark.functional
def test_registry_loads_yaml(tmp_path: Path) -> None:
    yaml_content = """
id: sample
adapter: sample
categories: [mental]
attributes: [intellect]
topics: [math]
min_age: 5
max_age: 12
prompt: "Test prompt"
config:
  foo: bar
"""
    (tmp_path / "sample.yaml").write_text(yaml_content)
    registry = ChallengeRegistry.from_directory(tmp_path)
    defs = registry.all()
    assert len(defs) == 1
    assert defs[0].id == "sample"
    assert defs[0].categories == ("mental",)
    assert defs[0].config == {"foo": "bar"}
