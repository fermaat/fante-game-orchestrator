"""BridgeNarrator — NarratorPort backed by core-llm-bridge's BridgeEngine.

Loads the narrator prompt from a YAML file (prompts/narrator.yaml by default).
Falls back to the inline template if the file is missing.
"""

from pathlib import Path
from typing import cast

from core_llm_bridge import BridgeEngine
from core_llm_bridge.core.base import BaseLLMProvider
from core_llm_bridge.utils.prompt_manager import PromptManager
from core_utils.profiler import profiler

from fante.domain.profile import Language, PlayerProfile

_DEFAULT_PROMPT_PATH = Path("prompts/narrator.yaml")

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
- Párrafos cortos: máximo 3-4 frases por respuesta. Una imagen vívida por turno.
- Cuando el jugador intente algo arriesgado, describe el intento y el resultado de forma clara.
- Termina siempre invitando a que el jugador decida qué hace a continuación.
- Para el modo mixto: introduce palabras o frases cortas en inglés entre paréntesis con su traducción.
"""

_LANGUAGE_INSTRUCTION: dict[Language, str] = {
    "es": "Narra siempre en español.",
    "en": "Narrate always in English.",
    "mixed": (
        "Narra en español, pero introduce de vez en cuando palabras o frases cortas en "
        "inglés (entre paréntesis con su traducción) para que el jugador aprenda."
    ),
}


def _build_system_prompt(
    profile: PlayerProfile,
    prompt_path: Path | None = _DEFAULT_PROMPT_PATH,
) -> str:
    prompts = PromptManager()
    if prompt_path is not None and prompt_path.exists():
        prompts.load_from_yaml(prompt_path)
    else:
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
        prompt_path: Path | None = _DEFAULT_PROMPT_PATH,
    ) -> None:
        system_prompt = _build_system_prompt(profile, prompt_path)
        self._engine = BridgeEngine(
            provider=provider,
            system_prompt=system_prompt,
            max_history_length=max_history_length,
        )

    def respond(self, user_input: str) -> str:
        with profiler.step("llm_call") as s:
            s.tag(model=self._engine.provider.model)
            response = self._engine.chat(user_input)
        return cast(str, response.text)

    def reset(self) -> None:
        self._engine.clear_history()

    def get_history(self) -> list[dict[str, str]]:
        return cast(list[dict[str, str]], self._engine.export_history())

    def seed_history(self, messages: list[dict[str, str]]) -> None:
        self._engine.import_history(messages)
