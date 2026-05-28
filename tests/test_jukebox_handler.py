"""Functional tests for JukeboxHandler using FakeMusicHubClient and a stub classifier."""

from typing import Any

import pytest

from core_music_hub.client.client import SongNotFoundError
from fante.jukebox.handler import JukeboxHandler
from fante.jukebox.intent import JukeboxIntent

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeMusicHubClient:
    """Records calls and optionally raises on specific methods."""

    def __init__(
        self,
        catalog: list[dict[str, Any]] | None = None,
        raise_on: set[str] | None = None,
    ) -> None:
        self._catalog: list[dict[str, Any]] = catalog or []
        self._raise_on: set[str] = raise_on or set()
        self.calls: list[tuple[Any, ...]] = []

    def catalog(self) -> list[dict[str, Any]]:
        self.calls.append(("catalog",))
        return self._catalog

    def play(self, *, alias: str | None = None, **kw: Any) -> dict[str, Any]:
        self.calls.append(("play", alias))
        if "play" in self._raise_on:
            raise SongNotFoundError(alias or "")
        return {"id": alias, "title": (alias or "X").title()}

    def stop(self) -> None:
        self.calls.append(("stop",))
        if "stop" in self._raise_on:
            raise RuntimeError("stop failed")

    def next(self) -> dict[str, Any]:
        self.calls.append(("next",))
        if "next" in self._raise_on:
            raise SongNotFoundError("alone")
        return {"id": "x", "title": "X"}


class StubClassifier:
    """Returns a fixed intent regardless of player input."""

    def __init__(self, intent: JukeboxIntent) -> None:
        self._intent = intent

    def classify(self, player_input: str) -> JukeboxIntent:
        return self._intent


def _make_handler(
    intent: JukeboxIntent, **client_kwargs: Any
) -> tuple[JukeboxHandler, FakeMusicHubClient]:
    client = FakeMusicHubClient(**client_kwargs)
    classifier = StubClassifier(intent)
    return JukeboxHandler(client=client, classifier=classifier), client  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.functional
def test_play_calls_client_and_returns_title():
    handler, client = _make_handler(JukeboxIntent(action="play", song_query="cocodrilo"))
    msg, should_exit = handler.process("pon el cocodrilo")
    assert ("play", "cocodrilo") in client.calls
    assert "Cocodrilo" in msg
    assert should_exit is False


@pytest.mark.functional
def test_play_empty_query_returns_question():
    handler, client = _make_handler(JukeboxIntent(action="play", song_query=""))
    msg, should_exit = handler.process("pon algo")
    assert "¿Qué canción" in msg
    assert should_exit is False
    assert not client.calls  # no HTTP call made


@pytest.mark.functional
def test_play_not_found_returns_friendly_message():
    handler, client = _make_handler(
        JukeboxIntent(action="play", song_query="dragón"),
        raise_on={"play"},
    )
    msg, should_exit = handler.process("pon el dragón")
    assert "No conozco" in msg
    assert "dragón" in msg
    assert should_exit is False


@pytest.mark.functional
def test_stop_calls_client():
    handler, client = _make_handler(JukeboxIntent(action="stop"))
    msg, should_exit = handler.process("para")
    assert ("stop",) in client.calls
    assert "parada" in msg.lower()
    assert should_exit is False


@pytest.mark.functional
def test_stop_exception_still_returns_message():
    handler, client = _make_handler(JukeboxIntent(action="stop"), raise_on={"stop"})
    msg, should_exit = handler.process("para")
    assert "parada" in msg.lower()
    assert should_exit is False


@pytest.mark.functional
def test_next_calls_client_and_returns_title():
    handler, client = _make_handler(JukeboxIntent(action="next"))
    msg, should_exit = handler.process("otra")
    assert ("next",) in client.calls
    assert "Cambiando" in msg
    assert should_exit is False


@pytest.mark.functional
def test_next_song_not_found():
    handler, client = _make_handler(JukeboxIntent(action="next"), raise_on={"next"})
    msg, should_exit = handler.process("otra")
    assert "Sólo tengo" in msg
    assert should_exit is False


@pytest.mark.functional
def test_list_returns_song_titles():
    songs = [{"id": "a", "title": "Canción A"}, {"id": "b", "title": "Canción B"}]
    handler, client = _make_handler(JukeboxIntent(action="list"), catalog=songs)
    msg, should_exit = handler.process("lista")
    assert ("catalog",) in client.calls
    assert "Canción A" in msg
    assert "Canción B" in msg
    assert should_exit is False


@pytest.mark.functional
def test_list_empty_catalog():
    handler, client = _make_handler(JukeboxIntent(action="list"), catalog=[])
    msg, should_exit = handler.process("lista")
    assert "ninguna" in msg.lower()
    assert should_exit is False


@pytest.mark.functional
def test_list_more_than_eight_songs():
    songs = [{"id": str(i), "title": f"Canción {i}"} for i in range(10)]
    handler, client = _make_handler(JukeboxIntent(action="list"), catalog=songs)
    msg, _ = handler.process("lista")
    assert "más" in msg


@pytest.mark.functional
def test_exit_stops_music_and_signals_exit():
    handler, client = _make_handler(JukeboxIntent(action="exit"))
    msg, should_exit = handler.process("salir")
    assert ("stop",) in client.calls
    assert "aventura" in msg.lower()
    assert should_exit is True


@pytest.mark.functional
def test_unknown_intent_returns_help_message():
    handler, _ = _make_handler(JukeboxIntent(action="unknown"))
    msg, should_exit = handler.process("grgrgrg")
    assert "No te he entendido" in msg
    assert should_exit is False
