"""BridgeNarrator — NarratorPort backed by core-llm-bridge's BridgeEngine.

Loads the narrator prompt from a YAML file (prompts/narrator.yaml by default).
Falls back to the inline template if the file is missing.
"""

from pathlib import Path
from typing import cast

from core_llm_bridge import BridgeEngine
from core_llm_bridge.core.base import BaseLLMProvider
from core_llm_bridge.utils.prompt_manager import PromptManager
from core_utils import logger
from core_utils.profiler import profiler

from fante.domain.profile import Language, PlayerProfile
from fante.domain.rules import CheckResult

_DEFAULT_PROMPT_PATH = Path("prompts/narrator.yaml")

NARRATOR_TEMPLATE = """\
Eres el narrador de una aventura de rol para $name.

Sobre el personaje:
- Trasfondo: $background
- Le gusta: $preferences
- Atributos: $attributes

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
- El turno puede traer entre paréntesis "(Contexto interno — ...)" o "(Detalle de fondo ...)".
  Esa información es SOLO para ti: úsala para enriquecer la narración, pero nunca la repitas
  literalmente en tu respuesta. Tu respuesta debe leerse como narración pura, sin paréntesis
  técnicos, sin corchetes, sin "Source:", sin meta-comentarios.
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
            attributes=", ".join(
                f"{k}: {v}" for k, v in profile.attributes.model_dump().items() if v != 0
            )
            or "(sin atributos)",
            language_instruction=_LANGUAGE_INSTRUCTION[profile.language],
        ),
    )


_ECHO_PREFIXES = (
    "(Contexto interno",
    "(Detalle de fondo",
    "[Resultado de acción",
    "[Conocimiento",
)


def _strip_echoed_context(text: str) -> str:
    """Drop leading lines that just mirror the metadata prefix we sent in."""
    lines = text.split("\n")
    while lines and (lines[0].strip().startswith(_ECHO_PREFIXES) or not lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines)


def _build_check_context(result: CheckResult) -> str:
    outcome = "con éxito" if result.success else "sin éxito"
    seed = f": {result.narration_seed}" if result.narration_seed else ""
    plot = (
        f" Dados de trama: {', '.join(d.value for d in result.plot_dice)}."
        if result.plot_dice
        else ""
    )
    return (
        f"(Contexto interno — el chequeo de '{result.rule_id}' se resolvió {outcome}{seed}.{plot})"
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

    def respond(
        self,
        user_input: str,
        check_result: CheckResult | None = None,
        knowledge: str | None = None,
    ) -> str:
        context_parts = []
        if check_result is not None:
            context_parts.append(_build_check_context(check_result))
        if knowledge is not None:
            context_parts.append(
                f"(Detalle de fondo que puedes integrar en la narración: {knowledge})"
            )
        if context_parts:
            turn_input = "\n".join(context_parts) + "\n\n" + user_input
        else:
            turn_input = user_input
        logger.debug(f"narrator.turn_input (full):\n{turn_input}")
        with profiler.step("llm_call") as s:
            s.tag(model=self._engine.provider.model)
            response = self._engine.chat(turn_input)
        cleaned = _strip_echoed_context(cast(str, response.text))
        if cleaned != response.text:
            # Replace polluted history entry so the pattern doesn't propagate
            history = self._engine.export_history()
            if history and history[-1].get("role") == "assistant":
                history[-1]["content"] = cleaned
                self._engine.import_history(history)
        return cleaned

    def reset(self) -> None:
        self._engine.clear_history()

    def get_history(self) -> list[dict[str, str]]:
        return cast(list[dict[str, str]], self._engine.export_history())

    def seed_history(self, messages: list[dict[str, str]]) -> None:
        self._engine.import_history(messages)
