"""JukeboxIntentClassifier — parse a player utterance into a structured intent."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

from core_llm_bridge import BridgeEngine
from core_llm_bridge.core.base import BaseLLMProvider
from core_llm_bridge.utils.prompt_manager import PromptManager
from core_utils import logger

JukeboxAction = Literal["play", "stop", "next", "list", "exit", "unknown"]

_VALID_ACTIONS = ("play", "stop", "next", "list", "exit", "unknown")

_DEFAULT_PROMPT_PATH = Path("prompts/jukebox_intent.yaml")


@dataclass(frozen=True)
class JukeboxIntent:
    action: JukeboxAction
    song_query: str | None = None  # only meaningful for action="play"


class JukeboxIntentClassifier:
    """Classifies a player utterance into a jukebox intent using an LLM.

    Uses a stateless per-call BridgeEngine (no conversation history) so each
    turn is independent — the same pattern as ActionClassifier.
    """

    def __init__(
        self,
        provider: BaseLLMProvider,
        known_aliases: list[str],
        prompt_path: Path = _DEFAULT_PROMPT_PATH,
    ) -> None:
        if not prompt_path.exists():
            raise FileNotFoundError(f"Jukebox intent prompt YAML not found at {prompt_path}.")
        prompts = PromptManager()
        prompts.load_from_yaml(prompt_path)
        self._system = prompts.render("jukebox_intent", aliases=", ".join(known_aliases))
        self._provider = provider

    def classify(self, player_input: str) -> JukeboxIntent:
        """Return the structured intent for the given player utterance."""
        # Stateless per-call engine: no conversation history is carried between turns.
        engine = BridgeEngine(
            provider=self._provider, system_prompt=self._system, max_history_length=2
        )
        response = engine.chat(player_input)
        text = cast(str, response.text).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            logger.warning(f"jukebox_intent: LLM returned non-JSON: {text!r}")
            return JukeboxIntent(action="unknown")

        action = data.get("action", "unknown")
        if action not in _VALID_ACTIONS:
            return JukeboxIntent(action="unknown")
        return JukeboxIntent(
            action=cast(JukeboxAction, action),
            song_query=data.get("song_query"),
        )
