"""BridgeNarrator — NarratorPort backed by core-llm-bridge's BridgeEngine.

The narrator prompt template lives entirely in `prompts/narrator.yaml`. Language-
and style-specific substitutions are computed in Python (see `_LANGUAGE_INSTRUCTION`
and `_STYLE_INSTRUCTION` below) and injected into the YAML's `$language_instruction`
and `$style_instruction` placeholders.
"""

import re
from pathlib import Path
from typing import Literal, cast

from core_llm_bridge import BridgeEngine
from core_llm_bridge.core.base import BaseLLMProvider
from core_llm_bridge.utils.prompt_manager import PromptManager
from core_utils import logger
from core_utils.profiler import profiler

from fante.domain.profile import Language, PlayerProfile
from fante.domain.rules import CheckResult

NarrationStyle = Literal["concise", "balanced", "rich"]

_DEFAULT_PROMPT_PATH = Path("prompts/narrator.yaml")


_LANGUAGE_INSTRUCTION: dict[Language, str] = {
    "es": "Narra siempre en español.",
    "en": "Narrate always in English.",
    "mixed": (
        "Narra en español, pero introduce de vez en cuando palabras o frases cortas en "
        "inglés (entre paréntesis con su traducción) para que el jugador aprenda."
    ),
}

_STYLE_INSTRUCTION: dict[NarrationStyle, str] = {
    "concise": (
        "Sé MUY breve. Máximo 2 frases cortas por respuesta. "
        "Una imagen y una pregunta. Vocabulario simple, presente, frases directas. "
        "Nada de descripciones largas, ni listas, ni adverbios encadenados. "
        "Si te apetece añadir más detalle, resiste — es mejor breve."
    ),
    "balanced": (
        "Párrafos cortos: máximo 3-4 frases por respuesta. Una imagen vívida por turno. "
        "Cuando el jugador haga algo arriesgado, describe el intento y el resultado de "
        "forma clara, sin extenderte."
    ),
    "rich": (
        "Hasta 5-6 frases por respuesta. Puedes incluir detalles sensoriales "
        "(sonidos, olores, texturas) y una imagen central por turno. "
        "Tono evocador pero sin perderte en digresiones."
    ),
}


def _build_system_prompt(
    profile: PlayerProfile,
    prompt_path: Path = _DEFAULT_PROMPT_PATH,
    style: NarrationStyle = "concise",
) -> str:
    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Narrator prompt YAML not found at {prompt_path}. "
            "The prompt is the single source of truth — restore it from git."
        )
    prompts = PromptManager()
    prompts.load_from_yaml(prompt_path)
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
            style_instruction=_STYLE_INSTRUCTION[style],
        ),
    )


_ECHO_PREFIXES = (
    "(Contexto interno",
    "(Detalle de fondo",
    "[Resultado de acción",
    "[Conocimiento",
)

# Output sanitisers — the prompt forbids URLs / markdown image syntax, but LLMs
# (gemma especially) occasionally include them anyway. We strip them post-hoc so
# the narration is always clean text for the TTS layer.
_MARKDOWN_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^)]*\)")  # keeps the link text
_URL_PATTERN = re.compile(r"https?://\S+")


def _strip_echoed_context(text: str) -> str:
    """Drop leading lines that just mirror the metadata prefix we sent in."""
    lines = text.split("\n")
    while lines and (lines[0].strip().startswith(_ECHO_PREFIXES) or not lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines)


def _strip_unwanted_output(text: str) -> str:
    """Apply all output sanitisers: leading metadata echo + URLs + markdown links."""
    text = _MARKDOWN_IMAGE_PATTERN.sub("", text)  # drop image markdown entirely
    text = _MARKDOWN_LINK_PATTERN.sub(r"\1", text)  # keep link text, drop URL
    text = _URL_PATTERN.sub("", text)  # strip remaining bare URLs
    text = _strip_echoed_context(text)
    # Collapse double spaces that might result from removals
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


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
        prompt_path: Path = _DEFAULT_PROMPT_PATH,
        style: NarrationStyle = "concise",
    ) -> None:
        system_prompt = _build_system_prompt(profile, prompt_path, style=style)
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
        cleaned = _strip_unwanted_output(cast(str, response.text))
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
