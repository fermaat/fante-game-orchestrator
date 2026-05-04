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
    LocalDice,
    StdinInput,
    StdoutOutput,
)
from fante.cli.commands import CommandHandler
from fante.config import FanteSettings
from fante.events.bus import EventBus
from fante.events.dad_monitor import install_dad_monitor
from fante.events.subscribers import install_logging_subscriber
from fante.manager import GameManager
from fante.ports import RulesPort


def _build_rules(settings: FanteSettings) -> RulesPort:
    if settings.fante_rules_backend == "mcp":
        from fante.adapters.mcp_rules import MCPRulesAdapter

        return MCPRulesAdapter(command=settings.mcp_rules_command)
    return LocalDice()


def _make_provider(settings: FanteSettings, model_override: str) -> OllamaProvider:
    model = model_override or settings.ollama_default_model
    return OllamaProvider(
        model=model,
        base_url=settings.ollama_base_url,
        timeout=settings.ollama_timeout,
    )


def build_game(settings: FanteSettings | None = None, reset: bool = False) -> GameManager:
    settings = settings or FanteSettings()
    configure_logger(settings)

    profile_store = JSONProfileStore(settings.player_profile_path)
    profile = profile_store.load()

    session_store = JSONSessionStore(settings.fante_session_path.expanduser())

    narrator_provider = _make_provider(settings, "")
    narrator = BridgeNarrator(
        provider=narrator_provider,
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

    rules = _build_rules(settings)

    classifier = None
    evaluator = None
    if settings.fante_classifier_enabled and settings.fante_rules_backend == "mcp":
        from fante.adapters.llm_evaluator import LLMPerformanceEvaluator
        from fante.turn.classifier import ActionClassifier

        rule_ids: list[str] = []
        try:
            from fante.adapters.mcp_rules import MCPRulesAdapter

            if isinstance(rules, MCPRulesAdapter):
                # reuse the same adapter — it's already connected
                rule_ids_result = rules._call_tool("list_rules", {})
                raw = rule_ids_result.structuredContent or {}
                rule_ids = raw.get("result", [])
        except Exception:
            pass

        classifier = ActionClassifier(
            provider=_make_provider(settings, settings.fante_classifier_model),
            rule_ids=rule_ids,
        )
        evaluator = LLMPerformanceEvaluator(
            provider=_make_provider(settings, settings.fante_evaluator_model),
            fallback_score=settings.fante_evaluator_fallback_score,
        )

    game = GameManager(
        narrator=narrator,
        input_port=StdinInput(),
        output_port=StdoutOutput(),
        profile_store=profile_store,
        bus=bus,
        session_store=session_store,
        rules_port=rules,
        classifier=classifier,
        evaluator=evaluator,
        default_mode=settings.fante_default_mode,
        command_handler=CommandHandler(
            profile_name=profile.name,
            get_turn_index=lambda: game.turn_index,
            get_session_started_at=lambda: game.session_started_at,
            reset_fn=lambda: game.reset(),
            save_fn=lambda: game.save_session(),
            rules_port=rules,
            get_profile=lambda: profile,
            get_mode=lambda: game.mode,
            set_mode=lambda m: game.set_mode(m),
        ),
    )

    return game
