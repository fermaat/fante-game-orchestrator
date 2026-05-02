"""BridgeNarrator — NarratorPort backed by core-llm-bridge's BridgeEngine.

Builds a system prompt from the player profile via the bridge's PromptManager.
The template is hardcoded for Phase 1.0; Phase 1.5 will move it to YAML.
"""

from typing import cast

from core_llm_bridge import BridgeEngine
from core_llm_bridge.core.base import BaseLLMProvider
from core_llm_bridge.utils.prompt_manager import PromptManager

from fante.domain.profile import Language, PlayerProfile

NARRATOR_TEMPLATE = """\
Eres el narrador de una aventura de rol para $name.

Sobre el personaje:
- Trasfondo: $background
- Le gusta: $preferences
- Atributos: $stats

Idioma de la narración: $language_instruction

Reglas del narrador:
- IMPORTANTE: El protagonista se llama exactamente «$name». Nunca uses otro nombre ni lo sustituyas por ningún otro.
- Háblale en segunda persona ("tú haces", "ves", "intentas").
- Mantén la coherencia entre turnos: recuerda lo que ya ha pasado en la aventura.
- Tono vivo y divertido, apto para una persona joven. Nada que dé miedo.
- Cuando el jugador intente algo arriesgado, describe el intento y luego el resultado de forma clara.
- Frases cortas. Una imagen vívida por respuesta. Termina invitando a que el jugador decida qué hacer.
"""

_LANGUAGE_INSTRUCTION: dict[Language, str] = {
    "es": "Narra siempre en español.",
    "en": "Narrate always in English.",
    "mixed": (
        "Narra en español, pero introduce de vez en cuando palabras o frases cortas en "
        "inglés (entre paréntesis con su traducción) para que el jugador aprenda."
    ),
}


def _build_system_prompt(profile: PlayerProfile) -> str:
    prompts = PromptManager()
    prompts.register("narrator", NARRATOR_TEMPLATE)
    return cast(
        str,
        prompts.render(
            "narrator",
            name=profile.name,
            background=profile.background or "(sin definir)",
            preferences=", ".join(profile.preferences) if profile.preferences else "(ninguna)",
            stats=(
                ", ".join(f"{k}: {v}" for k, v in profile.stats.items())
                if profile.stats
                else "(sin atributos)"
            ),
            language_instruction=_LANGUAGE_INSTRUCTION[profile.language],
        ),
    )


class BridgeNarrator:
    """NarratorPort implementation backed by a `BridgeEngine`."""

    def __init__(
        self,
        provider: BaseLLMProvider,
        profile: PlayerProfile,
        max_history_length: int = 30,
    ) -> None:
        system_prompt = _build_system_prompt(profile)
        self._engine = BridgeEngine(
            provider=provider,
            system_prompt=system_prompt,
            max_history_length=max_history_length,
        )

    def respond(self, user_input: str) -> str:
        response = self._engine.chat(user_input)
        return cast(str, response.text)

    def reset(self) -> None:
        self._engine.clear_history()
