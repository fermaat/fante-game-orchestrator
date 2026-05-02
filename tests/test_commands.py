"""Functional tests for slash commands."""

from datetime import datetime, timezone

import pytest

from fante.adapters.local_dice import LocalDice
from fante.cli.commands import CommandHandler
from fante.manager import QuitRequested


def _make_handler(
    turn_index: int = 0,
    profile_name: str = "Fante",
    reset_called: list[bool] | None = None,
    save_called: list[bool] | None = None,
    rules_port: object = None,
) -> CommandHandler:
    _reset = reset_called if reset_called is not None else []
    _save = save_called if save_called is not None else []
    started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return CommandHandler(
        profile_name=profile_name,
        get_turn_index=lambda: turn_index,
        get_session_started_at=lambda: started_at,
        reset_fn=lambda: _reset.append(True),
        save_fn=lambda: _save.append(True),
        rules_port=rules_port,  # type: ignore[arg-type]
    )


@pytest.mark.functional
class TestCommandHandler:
    def test_non_command_returns_none(self) -> None:
        h = _make_handler()
        assert h("hola") is None
        assert h("¿quién soy?") is None

    def test_quit_raises(self) -> None:
        h = _make_handler()
        with pytest.raises(QuitRequested):
            h("/quit")

    def test_quit_case_insensitive(self) -> None:
        h = _make_handler()
        with pytest.raises(QuitRequested):
            h("/Quit")

    def test_status_contains_turn_and_name(self) -> None:
        h = _make_handler(turn_index=5, profile_name="Marina")
        result = h("/status")
        assert result is not None
        assert "5" in result
        assert "Marina" in result

    def test_reset_calls_reset_fn(self) -> None:
        called: list[bool] = []
        h = _make_handler(reset_called=called)
        result = h("/reset")
        assert called == [True]
        assert result is not None
        assert len(result) > 0

    def test_save_calls_save_fn(self) -> None:
        called: list[bool] = []
        h = _make_handler(save_called=called)
        result = h("/save")
        assert called == [True]
        assert result is not None

    def test_roll_with_valid_spec(self) -> None:
        h = _make_handler(rules_port=LocalDice())
        result = h("/roll 1d20+2")
        assert result is not None
        assert "🎲" in result
        assert "1d20+2" in result

    def test_roll_with_multi_dice(self) -> None:
        h = _make_handler(rules_port=LocalDice())
        result = h("/roll 3d6")
        assert result is not None
        assert "3d6" in result

    def test_roll_invalid_spec_shows_error(self) -> None:
        h = _make_handler(rules_port=LocalDice())
        result = h("/roll abc")
        assert result is not None
        assert "inválidos" in result.lower() or "invalid" in result.lower()

    def test_roll_missing_arg(self) -> None:
        h = _make_handler(rules_port=LocalDice())
        result = h("/roll")
        assert result is not None
        assert "/roll" in result

    def test_roll_no_rules_port(self) -> None:
        h = _make_handler(rules_port=None)
        result = h("/roll 2d6")
        assert result is not None
        assert "disponible" in result

    def test_unknown_command_returns_none(self) -> None:
        h = _make_handler()
        assert h("/foobar") is None

    def test_game_manager_dispatches_commands(self, make_game: object) -> None:
        """Integration: GameManager routes /reset through the command handler."""
        reset_called: list[bool] = []
        game, _, out, _ = make_game(  # type: ignore[operator]
            narrator_responses=["respuesta"],
            input_lines=["/reset", "hola", None],
        )
        handler = _make_handler(reset_called=reset_called)
        game._command_handler = handler
        game.run()
        assert reset_called == [True]
        assert any("respuesta" in e for e in out.emitted)
