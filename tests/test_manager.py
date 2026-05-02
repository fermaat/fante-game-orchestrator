"""Functional tests for GameManager — real orchestrator with port-level fakes."""

import pytest

from fante.domain.events import DomainEvent, NarrationGenerated, TurnStarted

pytestmark = pytest.mark.functional


def test_process_turn_returns_narration_and_publishes_events(make_game) -> None:  # type: ignore[no-untyped-def]
    game, _, _, narrator = make_game(narrator_responses=["Ves un elefante."])
    seen: list[DomainEvent] = []
    game._bus.subscribe(DomainEvent, seen.append)

    out = game.process_turn("hola")

    assert out == "Ves un elefante."
    assert narrator.received == ["hola"]
    event_types = [type(e).__name__ for e in seen]
    assert event_types == ["TurnStarted", "NarrationGenerated", "TurnFinished"]
    assert isinstance(seen[0], TurnStarted) and seen[0].user_input == "hola"
    assert isinstance(seen[1], NarrationGenerated) and seen[1].narration == "Ves un elefante."


def test_run_loops_until_input_returns_none(make_game) -> None:  # type: ignore[no-untyped-def]
    game, _, output, narrator = make_game(
        narrator_responses=["Resp 1", "Resp 2"],
        input_lines=["primero", "segundo", None],
    )

    game.run()

    # banner + 2 narrations + goodbye
    assert any("Aventura para Fante" in line for line in output.emitted)
    assert "Resp 1" in output.emitted
    assert "Resp 2" in output.emitted
    assert any("Hasta la próxima" in line for line in output.emitted)
    assert narrator.received == ["primero", "segundo"]


def test_run_skips_empty_input_without_calling_narrator(make_game) -> None:  # type: ignore[no-untyped-def]
    game, _, _, narrator = make_game(
        narrator_responses=["Resp"],
        input_lines=["", "real", None],
    )

    game.run()

    assert narrator.received == ["real"]


def test_narrator_failure_does_not_break_the_loop(make_game) -> None:  # type: ignore[no-untyped-def]
    game, _, output, _ = make_game(input_lines=["hola", None])
    # Override narrator with one that raises.

    class Boom:
        def respond(self, user_input: str) -> str:
            raise RuntimeError("ollama down")

        def reset(self) -> None:
            pass

    game._narrator = Boom()

    game.run()

    assert any("se ha quedado sin palabras" in line for line in output.emitted)


def test_reset_clears_turn_counter_and_narrator(make_game) -> None:  # type: ignore[no-untyped-def]
    game, _, _, narrator = make_game(narrator_responses=["a", "b"])
    game.process_turn("x")
    game.reset()
    assert game._turn_index == 0
    assert narrator.reset_count == 1


@pytest.mark.parametrize(
    "quit_word",
    ["quit", "exit", "salir", "QUIT", "Salir"],
)
def test_stdin_input_recognises_quit_words(quit_word: str) -> None:
    """Sanity check on the StdinInput adapter (also functional in spirit)."""
    from fante.adapters.stdio_io import StdinInput

    inp = StdinInput()
    assert inp._quit_words == ("quit", "exit", "salir")
    assert quit_word.lower() in inp._quit_words
