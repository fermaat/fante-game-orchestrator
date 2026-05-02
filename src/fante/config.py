"""Application settings.

Subclasses the bridge's `Settings` (itself a `CoreSettings`) so all provider
env vars (`OLLAMA_*`, `ANTHROPIC_*`, `OPENAI_*`, `LOG_*`) are available
without re-declaration.
"""

from pathlib import Path

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


__all__ = ["FanteSettings"]
