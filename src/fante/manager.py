"""GameManager — central orchestrator.

Depends only on port protocols and the EventBus. Knows nothing about
specific adapters. Adapters are wired in `fante.compose`.
"""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

from core_utils import logger

from fante.domain.actor import profile_to_actor
from fante.domain.events import (
    ActionClassified,
    CheckResolved,
    NarrationGenerated,
    TurnFinished,
    TurnStarted,
)
from fante.domain.session import Session
from fante.events.bus import EventBus
from fante.ports import InputPort, NarratorPort, OutputPort, ProfileStore, RulesPort, SessionStore

if TYPE_CHECKING:
    from fante.ports.evaluator import PerformanceEvaluatorPort
    from fante.turn.classifier import ActionClassifier

Mode = Literal["dice", "skill"]


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
        rules_port: RulesPort | None = None,
        classifier: "ActionClassifier | None" = None,
        evaluator: "PerformanceEvaluatorPort | None" = None,
        default_mode: Mode = "skill",
    ) -> None:
        self._narrator = narrator
        self._input = input_port
        self._output = output_port
        self._profile_store = profile_store
        self._bus = bus
        self._session_store = session_store
        self._command_handler = command_handler
        self._rules = rules_port
        self._classifier = classifier
        self._evaluator = evaluator
        self._mode: Mode = default_mode
        self._turn_index = 0
        self._session_started_at: datetime = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Public read-only state
    # ------------------------------------------------------------------

    @property
    def turn_index(self) -> int:
        return self._turn_index

    @property
    def session_started_at(self) -> datetime:
        return self._session_started_at

    @property
    def mode(self) -> Mode:
        return self._mode

    def set_mode(self, mode: Mode) -> None:
        self._mode = mode

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def process_turn(self, user_input: str) -> str:
        """Run one turn through the full pipeline. Returns the narration."""
        self._turn_index += 1
        idx = self._turn_index
        self._bus.publish(TurnStarted(turn_index=idx, user_input=user_input))

        check_result = None

        if self._classifier is not None and self._rules is not None:
            profile = self._profile_store.load()
            intent = self._classifier.classify(user_input, profile.name)

            if intent is not None:
                self._bus.publish(ActionClassified(turn_index=idx, intent=intent))
                player_score: int | None = None
                if self._mode == "skill" and self._evaluator is not None:
                    player_score = self._evaluator.score(
                        user_input, profile, intent.context or None
                    )
                actor = profile_to_actor(profile)
                check_result = self._rules.check(
                    intent.rule_id, actor, intent.context or None, player_score
                )
                self._bus.publish(CheckResolved(turn_index=idx, result=check_result))

        narration = self._narrator.respond(user_input, check_result)
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
