"""Functional tests for the wake-word shortcut through GameManager.process_turn."""

import pytest

from tests.conftest import FakeRulesPort


class _FakeJukeboxHandler:
    def __init__(self, response: str = "Ahora suena: X", should_exit: bool = False) -> None:
        self.calls: list[str] = []
        self._response = response
        self._should_exit = should_exit

    def process(self, input_: str) -> tuple[str, bool]:
        self.calls.append(input_)
        return (self._response, self._should_exit)


@pytest.mark.functional
def test_wake_word_routes_to_jukebox_handler(make_game):
    """A wake-word utterance switches to jukebox mode and passes the remainder
    to the handler — without touching the RPG pipeline."""
    handler = _FakeJukeboxHandler(response="Ahora suena: X")
    game, _, out, narrator = make_game(
        narrator_responses=["should not be called"],
        input_lines=["fante pon el cocodrilo", None],
    )
    game._wake_words = ["fante"]
    game._jukebox_handler = handler
    game._classifier = None
    game._rules = FakeRulesPort()
    game.run()

    assert handler.calls == ["pon el cocodrilo"]
    assert game.mode == "jukebox"
    assert any("Ahora suena: X" in e for e in out.emitted)


@pytest.mark.functional
def test_wake_word_alone_emits_prompt(make_game):
    handler = _FakeJukeboxHandler()
    game, _, out, _ = make_game(input_lines=["fante", None])
    game._wake_words = ["fante"]
    game._jukebox_handler = handler
    game.run()

    assert handler.calls == []
    assert any("Dime" in e for e in out.emitted)
    assert game.mode == "jukebox"


@pytest.mark.functional
def test_wake_word_handler_exit_returns_to_rpg(make_game):
    handler = _FakeJukeboxHandler(response="Volvemos a la aventura.", should_exit=True)
    game, _, out, _ = make_game(input_lines=["fante salir", None])
    game._wake_words = ["fante"]
    game._jukebox_handler = handler
    game.run()

    assert game.mode == "skill"


@pytest.mark.functional
def test_wake_word_without_handler_emits_unavailable(make_game):
    game, _, out, _ = make_game(input_lines=["fante pon X", None])
    game._wake_words = ["fante"]
    game._jukebox_handler = None
    game.run()

    assert any("no disponible" in e.lower() for e in out.emitted)


@pytest.mark.functional
def test_no_wake_word_falls_through_to_rpg(make_game):
    """Without a wake word the normal RPG/jukebox pipeline runs as before."""
    game, _, out, narrator = make_game(
        narrator_responses=["narración normal"],
        input_lines=["pon el caballo", None],
    )
    game._wake_words = ["fante"]
    game._jukebox_handler = None
    game.run()

    assert narrator.received == ["pon el caballo"]
