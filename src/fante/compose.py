"""Composition root — the only place that knows about specific adapters.

Tests build their own composition using fakes; production code calls
`build_game()` to get a fully-wired `GameManager`.
"""

from core_llm_bridge.providers.ollama import OllamaProvider
from core_utils import logger
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
from fante.ports.knowledge import KnowledgePort
from fante.events.dad_monitor import install_dad_monitor
from fante.events.subscribers import install_logging_subscriber
from fante.manager import GameManager
from fante.ports import RulesPort
from fante.ports.io import InputPort, OutputPort


def _build_knowledge(settings: FanteSettings) -> KnowledgePort:
    if settings.fante_copper_enabled:
        from fante.adapters.copper_knowledge import CopperKnowledgeAdapter

        return CopperKnowledgeAdapter(
            copper_url=settings.fante_copper_url,
            mind_map=settings.fante_copper_mind_map,
            timeout_seconds=settings.copper_timeout_seconds,
        )
    from fante.adapters.noop_knowledge import NoopKnowledgeAdapter

    return NoopKnowledgeAdapter()


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


def build_game(
    settings: FanteSettings | None = None,
    reset: bool = False,
    session_topic: str | None = None,
) -> GameManager:
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
        style=settings.fante_narration_style,
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
    if settings.fante_world_enabled:
        from fante.adapters.logging_world import LoggingWorldAdapter
        from fante.events.world_view import install_world_view
        from fante.world.director import WorldDirector
        from fante.world.manifest import WorldManifest

        manifest = WorldManifest.from_file(settings.fante_world_manifest_path)
        install_world_view(bus, LoggingWorldAdapter(), WorldDirector(manifest))

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

    knowledge = _build_knowledge(settings)

    # I/O ports are selected first so the challenge adapters can share them
    # (otherwise interactive minigames would always read stdin and print to
    # stdout even in audio mode).
    input_port: InputPort
    output_port: OutputPort

    if settings.fante_audio_enabled:
        from speech_io_hub.client.client import SpeechClient

        from fante.adapters.tts_output import TTSOutput
        from fante.adapters.whisper_input import WhisperInput
        from fante.speech.vocabulary import load_vocabulary

        speech_client = SpeechClient(base_url=settings.fante_speech_url)
        initial_prompt = (
            load_vocabulary(
                settings.fante_speech_vocabulary_path,
                language=profile.language,
            )
            or None
        )
        # Whisper accepts "es" or "en" but not "mixed"; force "es" as the primary
        # transcription language for mixed-mode profiles. The vocabulary still
        # carries both Spanish and English words so the bias works in either.
        stt_language = profile.language if profile.language in ("es", "en") else "es"

        input_port = WhisperInput(
            client=speech_client,
            language=stt_language,
            initial_prompt=initial_prompt,
            input_mode=settings.fante_input_mode,
        )
        output_port = TTSOutput(
            client=speech_client,
            echo_to_stdout=True,
            voice=settings.fante_tts_voice or None,
        )
    else:
        input_port = StdinInput()
        output_port = StdoutOutput()

    # --- Jukebox wiring -------------------------------------------------------
    jukebox_handler = None
    if settings.fante_jukebox_enabled:
        import httpx

        from core_music_hub.client.client import MusicHubClient

        from fante.jukebox.handler import JukeboxHandler
        from fante.jukebox.intent import JukeboxIntentClassifier

        music_client = MusicHubClient(base_url=settings.fante_music_hub_url)
        # Pre-fetch the catalog so the intent classifier knows the aliases at startup.
        # If music-hub is unreachable, skip wiring rather than crashing the whole game.
        try:
            catalog = music_client.catalog()
            aliases = [a for s in catalog for a in [s["id"], *s.get("aliases", [])]]
            jukebox_classifier = JukeboxIntentClassifier(
                provider=_make_provider(settings, settings.fante_jukebox_intent_model),
                known_aliases=aliases,
            )
            jukebox_handler = JukeboxHandler(client=music_client, classifier=jukebox_classifier)
        except httpx.ConnectError as exc:
            # Expected case: music-hub not running. Don't spam the user with a traceback.
            logger.warning(
                f"jukebox: music-hub not reachable at {settings.fante_music_hub_url} "
                f"({exc}). Jukebox mode disabled — start core-music-hub to enable it."
            )
        except Exception:
            logger.exception(
                f"jukebox: unexpected error initialising from "
                f"{settings.fante_music_hub_url}; jukebox mode disabled"
            )

    rule_meta_provider = None
    challenge_selector = None
    challenge = None
    if settings.fante_challenge_enabled and settings.fante_rules_backend == "mcp":
        from fante.adapters.color_naming_challenge import ColorNamingChallenge
        from fante.adapters.math_quick_challenge import MathQuickChallenge
        from fante.adapters.mcp_rules import MCPRulesAdapter
        from fante.adapters.repeat_expression_challenge import RepeatExpressionChallenge
        from fante.challenge.dispatcher import ChallengeDispatcher
        from fante.challenge.registry import ChallengeRegistry
        from fante.challenge.selector import ChallengeSelector

        if isinstance(rules, MCPRulesAdapter):
            rule_meta_provider = rules

        registry = ChallengeRegistry.from_directory(settings.fante_challenge_definitions_path)
        challenge_selector = ChallengeSelector(
            registry=registry,
            recent_history_size=settings.fante_challenge_recent_history,
            optional_activation_prob=settings.fante_challenge_optional_prob,
            topic_bias_weight=settings.fante_challenge_topic_bias,
        )

        # Share the same I/O ports as the rest of the game so interactive
        # minigames are voice-driven in audio mode and keyboard-driven in text mode.
        challenge_adapters: dict[str, object] = {
            "math_quick": MathQuickChallenge(input_port, output_port),
            "color_naming": ColorNamingChallenge(input_port, output_port),
            "repeat_expression": RepeatExpressionChallenge(input_port, output_port),
        }
        challenge = ChallengeDispatcher(adapters=challenge_adapters)  # type: ignore[arg-type]

    game = GameManager(
        narrator=narrator,
        input_port=input_port,
        output_port=output_port,
        profile_store=profile_store,
        bus=bus,
        session_store=session_store,
        rules_port=rules,
        classifier=classifier,
        evaluator=evaluator,
        knowledge=knowledge,
        rule_meta_provider=rule_meta_provider,
        challenge_selector=challenge_selector,
        challenge=challenge,
        jukebox_handler=jukebox_handler,
        wake_words=settings.fante_wake_words,
        session_topic=session_topic,
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
            set_mode_jukebox=(lambda: game.set_mode("jukebox")) if jukebox_handler else None,
            set_session_topic=lambda t: game.set_session_topic(t),
        ),
    )

    return game
