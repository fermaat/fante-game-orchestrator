"""LLMPerformanceEvaluator — scores player engagement via an LLM judge.

Uses a separate BridgeEngine (no shared history with the narrator).
Returns an integer in [1, 20]. On parse failure falls back to the
configured default score.
"""

import logging
from pathlib import Path
from typing import Any, cast

from core_llm_bridge import BridgeEngine
from core_llm_bridge.core.base import BaseLLMProvider
from core_llm_bridge.utils.prompt_manager import PromptManager

from fante.domain.profile import PlayerProfile

_log = logging.getLogger(__name__)

_DEFAULT_PROMPT_PATH = Path("prompts/evaluator.yaml")

_SYSTEM_TEMPLATE = """\
Eres un juez que puntúa la participación de un niño de 2 años en su aventura de rol.
Premia la *implicación e intención*, no la calidad literaria.

Escala:
- 1–8: no dice nada coherente, silencio, ruido.
- 9–13: algo reconocible pero sin dirección clara.
- 14–18: involucrado, muestra intención o entusiasmo.
- 19–20: respuesta excepcionalmente comprometida.

Devuelve ÚNICAMENTE un número entero del 1 al 20. Sin explicaciones.
"""

_USER_TEMPLATE = """\
Aventurero: $name
Contexto de la acción: $context
Lo que dijo el jugador: $player_input
"""


def _build_system_prompt(prompt_path: Path | None) -> str:
    prompts = PromptManager()
    if prompt_path is not None and prompt_path.exists():
        prompts.load_from_yaml(prompt_path)
    else:
        prompts.register("evaluator_system", _SYSTEM_TEMPLATE)
    return cast(str, prompts.render("evaluator_system"))


class LLMPerformanceEvaluator:
    """PerformanceEvaluatorPort backed by an LLM-as-judge."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        fallback_score: int = 12,
        prompt_path: Path | None = _DEFAULT_PROMPT_PATH,
    ) -> None:
        system = _build_system_prompt(prompt_path)
        self._engine = BridgeEngine(
            provider=provider,
            system_prompt=system,
            max_history_length=1,
        )
        self._fallback = fallback_score

    def score(
        self,
        player_input: str,
        profile: PlayerProfile,
        context: dict[str, Any] | None = None,
    ) -> int:
        ctx_str = ", ".join(f"{k}: {v}" for k, v in (context or {}).items()) or "—"
        prompt = _USER_TEMPLATE.replace("$name", profile.name)
        prompt = prompt.replace("$context", ctx_str)
        prompt = prompt.replace("$player_input", player_input or "(silencio)")
        response = self._engine.chat(prompt)
        self._engine.clear_history()
        raw = cast(str, response.text).strip()
        try:
            value = int(raw.split()[0])
            if 1 <= value <= 20:
                return value
            _log.warning("Evaluator returned out-of-range value %d, using fallback", value)
        except (ValueError, IndexError):
            _log.warning("Evaluator returned non-integer %r, using fallback", raw)
        return self._fallback
