"""Unit tests for PlayerProfile and JSONProfileStore."""

from pathlib import Path

import pytest

from fante.adapters.json_profile_store import JSONProfileStore
from fante.domain.profile import PlayerProfile

pytestmark = pytest.mark.unit


def test_profile_defaults_to_spanish_and_schema_v1() -> None:
    profile = PlayerProfile(name="Fante")
    assert profile.schema_version == 1
    assert profile.language == "es"
    assert profile.preferences == []
    assert profile.stats == {}


def test_profile_accepts_valid_languages() -> None:
    for lang in ("es", "en", "mixed"):
        profile = PlayerProfile(name="Fante", language=lang)
        assert profile.language == lang


def test_json_profile_store_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "profile.json"
    original = PlayerProfile(
        name="Fante",
        background="Aventurero",
        preferences=["elefantes"],
        stats={"valor": 14},
        language="mixed",
    )

    store = JSONProfileStore(path)
    store.save(original)
    loaded = store.load()

    assert loaded == original


def test_json_profile_store_raises_when_missing(tmp_path: Path) -> None:
    store = JSONProfileStore(tmp_path / "missing.json")
    with pytest.raises(FileNotFoundError):
        store.load()
