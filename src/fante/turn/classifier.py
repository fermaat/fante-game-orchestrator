"""ActionClassifier — pre-narrator LLM call that decides if input is a game action.

Uses a separate BridgeEngine (no shared history with narrator or evaluator).
Returns ActionIntent | None. On any parse failure returns None so the game
falls through to the narrator without interruption.
"""

import json
import logging
from pathlib import Path
from typing import cast

from core_llm_bridge import BridgeEngine
from core_llm_bridge.core.base import BaseLLMProvider
from core_llm_bridge.utils.prompt_manager import PromptManager

from fante.domain.turn import ActionIntent

_log = logging.getLogger(__name__)

_DEFAULT_PROMPT_PATH = Path("prompts/classifier.yaml")

_SYSTEM_TEMPLATE = """\
Eres un clasificador de acciones en un juego de rol para niños pequeños.
Tu trabajo es determinar si lo que dice el jugador es una acción del juego
(correr, saltar, trepar, empujar, nadar, etc.) o simplemente una conversación.

Reglas disponibles: $rule_ids

Responde ÚNICAMENTE con JSON estricto, sin explicaciones, sin markdown:
- Si es una acción: {"rule_id": "<id_de_la_regla>", "context": {}}
- Si no es una acción: {"rule_id": null}

Elige el rule_id más cercano a lo que intenta el jugador.
Si no hay ninguna regla adecuada, devuelve null.
"""

_USER_TEMPLATE = "Jugador ($name) dice: $player_input"


def _build_system_prompt(rule_ids: list[str], prompt_path: Path | None) -> str:
    prompts = PromptManager()
    if prompt_path is not None and prompt_path.exists():
        prompts.load_from_yaml(prompt_path)
    else:
        prompts.register("classifier_system", _SYSTEM_TEMPLATE)
    return cast(
        str,
        prompts.render("classifier_system", rule_ids=", ".join(rule_ids) or "(ninguna)"),
    )


class ActionClassifier:
    """Classifies player input as an action (ActionIntent) or not (None)."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        rule_ids: list[str],
        prompt_path: Path | None = _DEFAULT_PROMPT_PATH,
    ) -> None:
        system = _build_system_prompt(rule_ids, prompt_path)
        self._engine = BridgeEngine(
            provider=provider,
            system_prompt=system,
            max_history_length=1,
        )
        self._name_placeholder = "$name"

    def classify(self, player_input: str, player_name: str) -> ActionIntent | None:
        prompt = _USER_TEMPLATE.replace("$name", player_name).replace("$player_input", player_input)
        response = self._engine.chat(prompt)
        self._engine.clear_history()
        raw = cast(str, response.text).strip()
        return self._parse(raw)

    def _parse(self, raw: str) -> ActionIntent | None:
        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(line for line in lines if not line.startswith("```")).strip()
        try:
            data = json.loads(raw)
            rule_id = data.get("rule_id")
            if not rule_id:
                return None
            context = data.get("context") or {}
            return ActionIntent(rule_id=str(rule_id), context=dict(context))
        except (json.JSONDecodeError, AttributeError, TypeError):
            _log.debug("Classifier returned unparseable response: %r", raw)
            return None
