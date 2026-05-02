"""Integration test against a real Ollama. Marker-gated, off by default.

Run with:
    pdm run pytest -m integration
"""

import pytest
from core_llm_bridge.providers.ollama import OllamaProvider

from fante.adapters.bridge_narrator import BridgeNarrator
from fante.domain.profile import PlayerProfile

pytestmark = pytest.mark.integration


def _ollama_reachable(provider: OllamaProvider) -> bool:
    try:
        return bool(provider.validate_connection())
    except Exception:
        return False


def test_narrator_remembers_player_name_across_turns() -> None:
    provider = OllamaProvider(model="llama3.2:latest")
    if not _ollama_reachable(provider):
        pytest.skip("Ollama not running on localhost:11434")

    profile = PlayerProfile(
        name="Fante",
        background="Joven explorador",
        preferences=["elefantes"],
        language="es",
    )
    narrator = BridgeNarrator(provider=provider, profile=profile)

    narrator.respond("Hola, ¿quién soy?")
    second = narrator.respond("¿Y qué me gusta?").lower()

    assert "elefante" in second or "fante" in second
