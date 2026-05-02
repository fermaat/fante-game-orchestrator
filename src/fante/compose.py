"""Composition root — the only place that knows about specific adapters.

Tests build their own composition using fakes; production code calls
`build_game()` to get a fully-wired `GameManager`.
"""

from core_llm_bridge.providers.ollama import OllamaProvider
from core_utils.logger import configure_logger

from fante.adapters import (
    BridgeNarrator,
    JSONProfileStore,
    StdinInput,
    StdoutOutput,
)
from fante.config import FanteSettings
from fante.events.bus import EventBus
from fante.events.subscribers import install_logging_subscriber
from fante.manager import GameManager


def build_game(settings: FanteSettings | None = None) -> GameManager:
    settings = settings or FanteSettings()
    configure_logger(settings)

    profile_store = JSONProfileStore(settings.player_profile_path)
    profile = profile_store.load()

    provider = OllamaProvider(
        model=settings.ollama_default_model,
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout,
    )

    narrator = BridgeNarrator(
        provider=provider,
        profile=profile,
        max_history_length=settings.max_history_length,
    )

    bus = EventBus()
    install_logging_subscriber(bus)

    return GameManager(
        narrator=narrator,
        input_port=StdinInput(),
        output_port=StdoutOutput(),
        profile_store=profile_store,
        bus=bus,
    )
