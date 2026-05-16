"""Application settings.

Subclasses the bridge's `Settings` (itself a `CoreSettings`) so all provider
env vars (`OLLAMA_*`, `ANTHROPIC_*`, `OPENAI_*`, `LOG_*`) are available
without re-declaration.
"""

import sys
from pathlib import Path
from typing import Literal

from core_llm_bridge.config import Settings as BridgeSettings


class FanteSettings(BridgeSettings):  # type: ignore[misc]
    model_config = {
        "env_file": [".env", ".env.local"],
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow",
    }

    ollama_default_model: str = "llama3.2:latest"
    player_profile_path: Path = Path("data/player_profile.json")
    max_history_length: int = 30
    narrator_prompt_path: Path = Path("prompts/narrator.yaml")
    fante_monitor: bool = False
    fante_monitor_path: Path = Path("logs/monitor.jsonl")
    fante_session_path: Path = Path("~/.fante/session.json")

    fante_rules_backend: Literal["mcp", "local"] = "mcp"
    mcp_rules_command: list[str] = [sys.executable, "-m", "mcp_game_rules"]

    fante_classifier_enabled: bool = True
    fante_classifier_model: str = ""
    fante_evaluator_model: str = ""
    fante_default_mode: Literal["dice", "skill"] = "skill"
    fante_evaluator_fallback_score: int = 12

    fante_copper_enabled: bool = False
    fante_copper_url: str = "http://127.0.0.1:8000"
    fante_copper_mind_map: dict[str, str] = {
        "adventure": "adventure",
        "math": "math",
        "languages": "languages",
        "lore": "lore",
    }
    # TODO: profile for lowering this
    copper_timeout_seconds: int = 120

    fante_challenge_enabled: bool = False
    fante_challenge_definitions_path: Path = Path("data/challenges")
    fante_challenge_optional_prob: float = 0.5
    fante_challenge_topic_bias: float = 2.0
    fante_challenge_recent_history: int = 3

    fante_audio_enabled: bool = False
    fante_speech_url: str = "http://127.0.0.1:8500"
    fante_speech_vocabulary_path: Path = Path("data/speech_vocabulary.yaml")
    fante_tts_voice: str = ""  # empty → server default


__all__ = ["FanteSettings"]
