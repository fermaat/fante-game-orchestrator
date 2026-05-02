"""Tests for JSONSessionStore and session save/restore round-trip."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from fante.adapters.json_session_store import JSONSessionStore
from fante.domain.session import Session


@pytest.mark.unit
class TestJSONSessionStore:
    def test_load_returns_none_when_no_file(self, tmp_path: Path) -> None:
        store = JSONSessionStore(tmp_path / "session.json")
        assert store.load() is None

    def test_save_and_load_round_trip(self, tmp_path: Path) -> None:
        store = JSONSessionStore(tmp_path / "session.json")
        session = Session(
            turn_index=3,
            history=[
                {"role": "user", "content": "hola"},
                {"role": "assistant", "content": "Hola!"},
            ],
            started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            last_at=datetime(2026, 1, 1, 0, 5, tzinfo=timezone.utc),
        )
        store.save(session)
        loaded = store.load()
        assert loaded is not None
        assert loaded.turn_index == 3
        assert loaded.history == session.history

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        store = JSONSessionStore(tmp_path / "nested" / "dir" / "session.json")
        store.save(Session())
        assert (tmp_path / "nested" / "dir" / "session.json").exists()

    def test_clear_deletes_file(self, tmp_path: Path) -> None:
        path = tmp_path / "session.json"
        store = JSONSessionStore(path)
        store.save(Session())
        assert path.exists()
        store.clear()
        assert not path.exists()

    def test_clear_is_idempotent(self, tmp_path: Path) -> None:
        store = JSONSessionStore(tmp_path / "session.json")
        store.clear()  # no file — should not raise


@pytest.mark.functional
class TestSessionRoundTrip:
    """Functional: GameManager auto-saves and FakeNarrator seeds history."""

    def test_autosave_on_process_turn(self, make_game: object) -> None:
        from tests.conftest import FakeSessionStore

        game, _, _, narrator = make_game(  # type: ignore[operator]
            narrator_responses=["Bienvenido!"],
            input_lines=[None],
        )
        store = FakeSessionStore()
        game._session_store = store
        game.process_turn("hola")
        assert store.save_count == 1

    def test_reset_clears_session(self, make_game: object) -> None:
        from tests.conftest import FakeSessionStore

        game, _, _, _ = make_game(input_lines=[None])  # type: ignore[operator]
        store = FakeSessionStore()
        game._session_store = store
        game.reset()
        assert store.clear_count == 1

    def test_seed_history_restores_state(self) -> None:
        from fante.adapters.bridge_narrator import BridgeNarrator
        from tests.conftest import MockProvider

        messages = [
            {"role": "user", "content": "hola"},
            {"role": "assistant", "content": "Hola!"},
        ]
        from fante.domain.profile import PlayerProfile

        profile = PlayerProfile(name="Fante", language="es")
        narrator = BridgeNarrator(provider=MockProvider([]), profile=profile, prompt_path=None)
        narrator.seed_history(messages)
        assert narrator.get_history() == messages
