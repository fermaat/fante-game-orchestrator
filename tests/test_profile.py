"""Unit tests for PlayerProfile and JSONProfileStore."""

import json
from pathlib import Path

import pytest

from fante.adapters.json_profile_store import JSONProfileStore
from fante.domain.profile import Attributes, PlayerProfile

pytestmark = pytest.mark.unit


def test_profile_defaults_to_spanish_and_schema_v2() -> None:
    profile = PlayerProfile(name="Fante")
    assert profile.schema_version == 2
    assert profile.language == "es"
    assert profile.preferences == []
    assert profile.skills == {}
    assert profile.tags == []
    assert isinstance(profile.attributes, Attributes)


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
        attributes=Attributes(
            strength=3, speed=4, intellect=3, willpower=5, awareness=4, presence=6
        ),
        skills={"athletics": 1},
        tags=["explorador"],
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


def test_json_profile_store_migrates_v1_to_v2(tmp_path: Path) -> None:
    v1_data = {
        "schema_version": 1,
        "name": "Fante",
        "background": "Explorador",
        "preferences": ["elefantes"],
        "stats": {"fuerza": 8, "valor": 14},
        "language": "es",
    }
    path = tmp_path / "profile_v1.json"
    path.write_text(json.dumps(v1_data), encoding="utf-8")

    store = JSONProfileStore(path)
    profile = store.load()

    assert profile.schema_version == 2
    assert profile.name == "Fante"
    assert not hasattr(profile, "stats") or "stats" not in profile.model_fields
    assert isinstance(profile.attributes, Attributes)
    assert profile.skills == {}
    assert profile.tags == []
