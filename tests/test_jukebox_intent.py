"""Functional tests for JukeboxIntentClassifier using MockProvider."""

from pathlib import Path

import pytest

from tests.conftest import MockProvider
from fante.jukebox.intent import JukeboxIntent, JukeboxIntentClassifier


def _make_classifier(
    tmp_path: Path,
    response: str,
    aliases: list[str] | None = None,
) -> JukeboxIntentClassifier:
    """Build a classifier with a minimal prompt fixture and a canned LLM response."""
    prompt = tmp_path / "jukebox_intent.yaml"
    prompt.write_text('name: jukebox_intent\ntemplate: "ignored ($aliases)"\n')
    provider = MockProvider([response])
    return JukeboxIntentClassifier(
        provider=provider,
        known_aliases=aliases or ["cocodrilo", "elefante"],
        prompt_path=prompt,
    )


@pytest.mark.functional
def test_play_intent_parsed(tmp_path):
    clf = _make_classifier(tmp_path, '{"action": "play", "song_query": "cocodrilo"}')
    intent = clf.classify("pon el cocodrilo")
    assert intent.action == "play"
    assert intent.song_query == "cocodrilo"


@pytest.mark.functional
def test_stop_intent_parsed(tmp_path):
    clf = _make_classifier(tmp_path, '{"action": "stop"}')
    intent = clf.classify("para la música")
    assert intent.action == "stop"
    assert intent.song_query is None


@pytest.mark.functional
def test_next_intent_parsed(tmp_path):
    clf = _make_classifier(tmp_path, '{"action": "next"}')
    intent = clf.classify("otra canción")
    assert intent.action == "next"


@pytest.mark.functional
def test_list_intent_parsed(tmp_path):
    clf = _make_classifier(tmp_path, '{"action": "list"}')
    intent = clf.classify("qué canciones tienes")
    assert intent.action == "list"


@pytest.mark.functional
def test_exit_intent_parsed(tmp_path):
    clf = _make_classifier(tmp_path, '{"action": "exit"}')
    intent = clf.classify("salir")
    assert intent.action == "exit"


@pytest.mark.functional
def test_unknown_intent_parsed(tmp_path):
    clf = _make_classifier(tmp_path, '{"action": "unknown"}')
    intent = clf.classify("bla bla bla")
    assert intent.action == "unknown"


@pytest.mark.functional
def test_garbage_json_returns_unknown(tmp_path):
    clf = _make_classifier(tmp_path, "esto no es json válido")
    intent = clf.classify("algo")
    assert intent.action == "unknown"
    assert intent.song_query is None


@pytest.mark.functional
def test_invalid_action_value_returns_unknown(tmp_path):
    clf = _make_classifier(tmp_path, '{"action": "dance"}')
    intent = clf.classify("baila")
    assert intent.action == "unknown"


@pytest.mark.functional
def test_missing_prompt_raises(tmp_path):
    provider = MockProvider(["{}"])
    with pytest.raises(FileNotFoundError, match="Jukebox intent prompt YAML not found"):
        JukeboxIntentClassifier(
            provider=provider,
            known_aliases=[],
            prompt_path=tmp_path / "nonexistent.yaml",
        )
