"""Functional tests — GameManager routes turns to JukeboxHandler when mode=jukebox."""

from collections.abc import Iterable

import pytest

from fante.events.bus import EventBus
from fante.manager import GameManager
from tests.conftest import FakeInput, FakeNarrator, FakeOutput, FakeProfileStore

# ---------------------------------------------------------------------------
# Fake jukebox handler
# ---------------------------------------------------------------------------


class FakeJukeboxHandler:
    """Records all calls; returns a fixed (message, exit_flag) pair."""

    def __init__(self, message: str = "hola", should_exit: bool = False) -> None:
        self._message = message
        self._should_exit = should_exit
        self.calls: list[str] = []

    def process(self, player_input: str) -> tuple[str, bool]:
        self.calls.append(player_input)
        return self._message, self._should_exit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_jukebox_game(
    jukebox_handler: FakeJukeboxHandler,
    narrator_responses: Iterable[str] = (),
) -> tuple[GameManager, FakeOutput, FakeNarrator]:
    from fante.domain.profile import Attributes, PlayerProfile

    profile = PlayerProfile(
        name="Fante",
        background="Explorador",
        preferences=[],
        attributes=Attributes(
            strength=3, speed=3, intellect=3, willpower=3, awareness=3, presence=3
        ),
        language="es",
    )
    narrator = FakeNarrator(narrator_responses)
    output = FakeOutput()
    game = GameManager(
        narrator=narrator,
        input_port=FakeInput([None]),
        output_port=output,
        profile_store=FakeProfileStore(profile),
        bus=EventBus(),
        jukebox_handler=jukebox_handler,  # type: ignore[arg-type]
        default_mode="jukebox",
    )
    return game, output, narrator


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.functional
def test_jukebox_turn_calls_handler_not_narrator():
    fake = FakeJukeboxHandler(message="Ahora suena: X.")
    game, output, narrator = _make_jukebox_game(fake)

    result = game.process_turn("pon X")

    assert fake.calls == ["pon X"]
    assert result == "Ahora suena: X."
    assert narrator.received == []  # narrator is NOT consulted


@pytest.mark.functional
def test_jukebox_turn_returns_message_for_caller_to_emit():
    """process_turn() returns the message — the outer run() loop is what emits
    it to OutputPort. process_turn must NOT emit itself (that would double-print
    and double-speak via TTS)."""
    fake = FakeJukeboxHandler(message="Música parada.")
    game, output, _ = _make_jukebox_game(fake)

    result = game.process_turn("para")

    assert result == "Música parada."
    assert output.emitted == []  # process_turn must not emit by itself


@pytest.mark.functional
def test_jukebox_exit_switches_mode_to_skill():
    fake = FakeJukeboxHandler(message="Volvemos a la aventura.", should_exit=True)
    game, _, narrator = _make_jukebox_game(fake, narrator_responses=["La aventura continúa."])

    assert game.mode == "jukebox"
    game.process_turn("salir")
    mode_after: str = game.mode  # capture in a plain str to avoid literal-narrowing
    assert mode_after == "skill"


@pytest.mark.functional
def test_normal_turn_uses_narrator_not_jukebox():
    """When mode != jukebox, the handler must NOT be called."""
    fake = FakeJukeboxHandler()
    game, _, narrator = _make_jukebox_game(fake, narrator_responses=["Narración RPG."])
    game.set_mode("skill")

    result = game.process_turn("exploro el bosque")

    assert fake.calls == []
    assert result == "Narración RPG."


@pytest.mark.functional
def test_jukebox_turn_increments_turn_index():
    fake = FakeJukeboxHandler()
    game, _, _ = _make_jukebox_game(fake)

    assert game.turn_index == 0
    game.process_turn("algo")
    assert game.turn_index == 1


@pytest.mark.functional
def test_jukebox_mode_without_handler_falls_through_to_narrator():
    """If mode=jukebox but no handler is wired, fall through to the RPG pipeline."""
    from fante.domain.profile import Attributes, PlayerProfile

    profile = PlayerProfile(
        name="Fante",
        background="Explorador",
        preferences=[],
        attributes=Attributes(
            strength=3, speed=3, intellect=3, willpower=3, awareness=3, presence=3
        ),
        language="es",
    )
    narrator = FakeNarrator(["Respuesta del narrador."])
    output = FakeOutput()
    game = GameManager(
        narrator=narrator,
        input_port=FakeInput([None]),
        output_port=output,
        profile_store=FakeProfileStore(profile),
        bus=EventBus(),
        jukebox_handler=None,
        default_mode="jukebox",
    )

    result = game.process_turn("hola")
    assert result == "Respuesta del narrador."
