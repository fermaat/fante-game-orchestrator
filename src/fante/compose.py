"""Composition root — the only place that knows about specific adapters.

Tests build their own composition using fakes; production code calls
`build_game()` to get a fully-wired `GameManager`.
"""

from core_llm_bridge.providers.ollama import OllamaProvider
from core_utils.logger import configure_logger

from fante.adapters import (
    BridgeNarrator,
    JSONProfileStore,
    JSONSessionStore,
    StdinInput,
    StdoutOutput,
)
from fante.config import FanteSettings
from fante.events.bus import EventBus
from fante.events.dad_monitor import install_dad_monitor
from fante.events.subscribers import install_logging_subscriber
from fante.manager import GameManager


def build_game(settings: FanteSettings | None = None, reset: bool = False) -> GameManager:
    settings = settings or FanteSettings()
    configure_logger(settings)

    profile_store = JSONProfileStore(settings.player_profile_path)
    profile = profile_store.load()

    session_store = JSONSessionStore(settings.fante_session_path.expanduser())

    provider = OllamaProvider(
        model=settings.ollama_default_model,
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout,
    )

    narrator = BridgeNarrator(
        provider=provider,
        profile=profile,
        max_history_length=settings.max_history_length,
        prompt_path=settings.narrator_prompt_path,
    )

    if reset:
        session_store.clear()
    else:
        saved = session_store.load()
        if saved is not None:
            narrator.seed_history(saved.history)

    bus = EventBus()
    install_logging_subscriber(bus)
    if settings.fante_monitor:
        install_dad_monitor(bus, settings.fante_monitor_path)

    return GameManager(
        narrator=narrator,
        input_port=StdinInput(),
        output_port=StdoutOutput(),
        profile_store=profile_store,
        bus=bus,
        session_store=session_store,
    )
