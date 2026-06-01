"""GameManager — central orchestrator.

Depends only on port protocols and the EventBus. Knows nothing about
specific adapters. Adapters are wired in `fante.compose`.
"""

import unicodedata
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
    from fante.jukebox.handler import JukeboxHandler
    from fante.ports.challenge import ChallengePort
    from fante.ports.challenge_selector import ChallengeSelectorPort
    from fante.ports.evaluator import PerformanceEvaluatorPort
    from fante.ports.knowledge import KnowledgePort
    from fante.ports.rule_meta import RuleMetaProvider
    from fante.turn.classifier import ActionClassifier

Mode = Literal["dice", "skill", "jukebox"]


def _normalize(s: str) -> str:
    """Lowercase + strip diacritics. Length is preserved (combining marks dropped)."""
    nfd = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


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
        knowledge: "KnowledgePort | None" = None,
        rule_meta_provider: "RuleMetaProvider | None" = None,
        challenge_selector: "ChallengeSelectorPort | None" = None,
        challenge: "ChallengePort | None" = None,
        jukebox_handler: "JukeboxHandler | None" = None,
        wake_words: list[str] | None = None,
        session_topic: str | None = None,
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
        self._knowledge = knowledge
        self._rule_meta_provider = rule_meta_provider
        self._challenge_selector = challenge_selector
        self._challenge = challenge
        self._jukebox_handler = jukebox_handler
        self._wake_words: list[str] = list(wake_words) if wake_words else []
        self._session_topic = session_topic
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

    def set_session_topic(self, topic: str | None) -> None:
        self._session_topic = topic

    # ------------------------------------------------------------------
    # Wake-word detection
    # ------------------------------------------------------------------

    def _detect_wake_word(self, user_input: str) -> str | None:
        """If `user_input` starts with a configured wake word, return the remainder
        (with leading whitespace and trailing punctuation stripped). Returns None
        if no wake word matches.

        Matching is case- and accent-insensitive. A word boundary (whitespace,
        punctuation, or end-of-input) is required after the wake word, so
        "fantástico" does NOT match "fante".

        Multi-word wake words are supported and matched longest-first.
        """
        if not self._wake_words:
            return None

        text = user_input.lstrip()
        normalized_text = _normalize(text)

        # Longest wake word first — so "hey fante" beats "fante" when both configured.
        candidates = sorted(self._wake_words, key=len, reverse=True)
        for word in candidates:
            normalized_word = _normalize(word)
            if not normalized_text.startswith(normalized_word):
                continue
            # Require a word boundary after the wake word (or end of input).
            idx = len(normalized_word)
            if idx < len(normalized_text) and normalized_text[idx].isalnum():
                continue
            # Slice from the ORIGINAL text — preserves casing/accents in the remainder
            # so it reaches the jukebox handler / song-query classifier intact.
            remainder = text[idx:].lstrip(",.!? \t")
            return remainder
        return None

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    def process_turn(self, user_input: str) -> str:
        """Run one turn through the full pipeline. Returns the narration."""
        self._turn_index += 1
        idx = self._turn_index
        self._bus.publish(TurnStarted(turn_index=idx, user_input=user_input))

        # ---- Wake-word shortcut → enter jukebox + execute remainder ---------------
        # Note: we DO NOT call self._output.emit() in these branches. The outer
        # run() loop emits whatever process_turn() returns, so emitting here
        # would double-print and double-speak (via TTS).
        remainder = self._detect_wake_word(user_input)
        if remainder is not None:
            if self._jukebox_handler is None:
                message = "(Modo jukebox no disponible.)"
                self._bus.publish(NarrationGenerated(turn_index=idx, narration=message))
                self._bus.publish(TurnFinished(turn_index=idx))
                self._autosave()
                return message

            self._mode = "jukebox"
            if not remainder:
                message = "Dime."
            else:
                message, should_exit = self._jukebox_handler.process(remainder)
                if should_exit:
                    self._mode = "skill"
            self._bus.publish(NarrationGenerated(turn_index=idx, narration=message))
            self._bus.publish(TurnFinished(turn_index=idx))
            self._autosave()
            return message
        # --------------------------------------------------------------------------

        # Jukebox mode: delegate entirely to the jukebox handler, skip RPG pipeline.
        if self._mode == "jukebox" and self._jukebox_handler is not None:
            message, should_exit = self._jukebox_handler.process(user_input)
            if should_exit:
                self._mode = "skill"  # back to RPG default
            self._bus.publish(NarrationGenerated(turn_index=idx, narration=message))
            self._bus.publish(TurnFinished(turn_index=idx))
            self._autosave()
            return message

        check_result = None
        knowledge: str | None = None

        if self._classifier is not None and self._rules is not None:
            profile = self._profile_store.load()
            intent = self._classifier.classify(user_input, profile.name)

            if intent is None:
                logger.debug(
                    f"classifier returned None for user_input={user_input!r} "
                    "— treating as conversation (skipping check)"
                )
            else:
                self._bus.publish(ActionClassified(turn_index=idx, intent=intent))
                player_score: int | None = None

                # Challenge phase: if all three pieces are wired, ask the selector
                # whether a minigame applies and run it for a score.
                if (
                    self._rule_meta_provider is not None
                    and self._challenge_selector is not None
                    and self._challenge is not None
                ):
                    try:
                        meta = self._rule_meta_provider.get_rule_meta(intent.rule_id)
                        logger.debug(
                            f"challenge.meta rule_id={meta.rule_id} "
                            f"challenge={meta.challenge} "
                            f"category={meta.challenge_category} "
                            f"attribute={meta.attribute}"
                        )
                        spec = self._challenge_selector.pick(meta, self._session_topic, profile)
                        if spec is None:
                            logger.debug(
                                f"challenge.pick rule_id={intent.rule_id} "
                                f"session_topic={self._session_topic} -> None (skip)"
                            )
                        else:
                            logger.debug(
                                f"challenge.pick rule_id={intent.rule_id} -> spec.id={spec.id} "
                                f"adapter={spec.adapter_id}"
                            )
                            score = self._challenge.run(spec, user_input, profile)
                            logger.debug(f"challenge.run spec.id={spec.id} -> score={score}")
                            if score > 0:
                                player_score = score
                    except Exception:
                        logger.exception(f"challenge phase failed for rule_id={intent.rule_id}")

                # Skill-mode evaluator fallback when no challenge produced a score.
                if player_score is None and self._mode == "skill" and self._evaluator is not None:
                    player_score = self._evaluator.score(
                        user_input, profile, intent.context or None
                    )
                actor = profile_to_actor(profile)
                check_result = self._rules.check(
                    intent.rule_id, actor, intent.context or None, player_score
                )
                self._bus.publish(CheckResolved(turn_index=idx, result=check_result))

                resolved_topic = check_result.knowledge_topic or self._session_topic
                if resolved_topic and self._knowledge is not None:
                    ctx = {
                        "action": intent.rule_id,
                        "success": check_result.success,
                        "roll": check_result.kept_roll,
                        "difficulty": check_result.difficulty,
                        "actor": profile.name,
                        "context": intent.context or {},
                    }
                    try:
                        knowledge = self._knowledge.query(resolved_topic, ctx)
                    except Exception:
                        logger.exception(f"knowledge query failed for topic={resolved_topic}")

        narration = self._narrator.respond(user_input, check_result, knowledge)
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
