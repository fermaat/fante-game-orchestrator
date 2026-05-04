"""Unit tests for profile_to_actor translation."""

import pytest

from fante.domain.actor import Actor, profile_to_actor
from fante.domain.profile import Attributes, PlayerProfile


@pytest.mark.unit
def test_profile_to_actor_maps_fields(sample_profile: PlayerProfile) -> None:
    actor = profile_to_actor(sample_profile)
    assert isinstance(actor, Actor)
    assert actor.name == sample_profile.name
    assert actor.attributes == sample_profile.attributes
    assert actor.skills == sample_profile.skills
    assert actor.tags == sample_profile.tags


@pytest.mark.unit
def test_profile_to_actor_model_dump_is_serialisable(sample_profile: PlayerProfile) -> None:
    actor = profile_to_actor(sample_profile)
    data = actor.model_dump()
    assert "name" in data
    assert "attributes" in data
    assert "strength" in data["attributes"]


@pytest.mark.unit
def test_attributes_defaults_are_zero() -> None:
    attrs = Attributes()
    assert all(v == 0 for v in attrs.model_dump().values())
