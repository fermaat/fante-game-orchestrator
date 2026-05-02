"""GameManager — central orchestrator.

Depends only on port protocols and the EventBus. Knows nothing about
specific adapters. Adapters are wired in `fante.compose`.
"""

from collections.abc import Callable
from datetime import datetime, timezone

from core_utils import logger

from fante.domain.events import NarrationGenerated, TurnFinished, TurnStarted
from fante.domain.session import Session
from fante.events.bus import EventBus
from fante.ports import InputPort, NarratorPort, OutputPort, ProfileStore, SessionStore


class QuitRequested(Exception):
    """Raised by a command handler to signal the game loop should exit."""


class GameManager:
    def __init__(
        self,
        narrator: NarratorPort,
        input_port: InputPort,
        output_port: OutputPort,
        profile_store: ProfileStore,
        bus: EventBus,
        session_store: SessionStore | None = None,
        command_handler: Callable[[str], str | None] | None = None,
    ) -> None:
        self._narrator = narrator
        self._input = input_port
        self._output = output_port
        self._profile_store = profile_store
        self._bus = bus
        self._session_store = session_store
        self._command_handler = command_handler
        self._turn_index = 0
        self._session_started_at: datetime = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Public read-only state (used by CommandHandler for /status)
    # ------------------------------------------------------------------

    @property
    def turn_index(self) -> int:
        return self._turn_index

    @property
    def session_started_at(self) -> datetime:
        return self._session_started_at

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def process_turn(self, user_input: str) -> str:
        """Run one turn through narrator + event bus. Returns the narration."""
        self._turn_index += 1
        idx = self._turn_index
        self._bus.publish(TurnStarted(turn_index=idx, user_input=user_input))
        narration = self._narrator.respond(user_input)
        self._bus.publish(NarrationGenerated(turn_index=idx, narration=narration))
        self._bus.publish(TurnFinished(turn_index=idx))
        self._autosave()
        return narration

    def reset(self) -> None:
        self._turn_index = 0
        self._session_started_at = datetime.now(timezone.utc)
        self._narrator.reset()
        if self._session_store is not None:
            self._session_store.clear()

    def save_session(self) -> None:
        """Explicitly persist the current session."""
        if self._session_store is not None:
            self._session_store.save(self._build_session())

    def _autosave(self) -> None:
        if self._session_store is not None:
            try:
                self._session_store.save(self._build_session())
            except Exception:
                logger.exception("session autosave failed")

    def _build_session(self) -> Session:
        return Session(
            turn_index=self._turn_index,
            history=self._narrator.get_history(),
            started_at=self._session_started_at,
            last_at=datetime.now(timezone.utc),
        )

    # ------------------------------------------------------------------
    # REPL
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Blocking REPL: read → process → emit until input is exhausted."""
        profile = self._profile_store.load()
        self._output.emit(
            f"=== Aventura para {profile.name} ===\n" "(Escribe 'salir' para terminar)\n"
        )
        if profile.seed_prompt:
            try:
                self._output.emit(self.process_turn(profile.seed_prompt))
            except Exception:
                logger.exception("opening scene failed")
        while True:
            user_input = self._input.read()
            if user_input is None:
                break
            if not user_input:
                continue
            if self._command_handler is not None:
                try:
                    result = self._command_handler(user_input)
                except QuitRequested:
                    break
                if result is not None:
                    self._output.emit(result)
                    continue
            try:
                narration = self.process_turn(user_input)
            except Exception:
                logger.exception("turn failed")
                self._output.emit("(El narrador se ha quedado sin palabras. Inténtalo de nuevo.)")
                continue
            self._output.emit(narration)
        self._output.emit("¡Hasta la próxima aventura!")
