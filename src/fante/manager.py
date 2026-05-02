"""GameManager — central orchestrator.

Depends only on port protocols and the EventBus. Knows nothing about
specific adapters. Adapters are wired in `fante.compose`.
"""

from core_utils import logger

from fante.domain.events import NarrationGenerated, TurnFinished, TurnStarted
from fante.events.bus import EventBus
from fante.ports import InputPort, NarratorPort, OutputPort, ProfileStore


class GameManager:
    def __init__(
        self,
        narrator: NarratorPort,
        input_port: InputPort,
        output_port: OutputPort,
        profile_store: ProfileStore,
        bus: EventBus,
    ) -> None:
        self._narrator = narrator
        self._input = input_port
        self._output = output_port
        self._profile_store = profile_store
        self._bus = bus
        self._turn_index = 0

    def process_turn(self, user_input: str) -> str:
        """Run one turn through narrator + event bus. Returns the narration."""
        self._turn_index += 1
        idx = self._turn_index
        self._bus.publish(TurnStarted(turn_index=idx, user_input=user_input))
        narration = self._narrator.respond(user_input)
        self._bus.publish(NarrationGenerated(turn_index=idx, narration=narration))
        self._bus.publish(TurnFinished(turn_index=idx))
        return narration

    def reset(self) -> None:
        self._turn_index = 0
        self._narrator.reset()

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
            try:
                narration = self.process_turn(user_input)
            except Exception:
                logger.exception("turn failed")
                self._output.emit("(El narrador se ha quedado sin palabras. Inténtalo de nuevo.)")
                continue
            self._output.emit(narration)
        self._output.emit("¡Hasta la próxima aventura!")
