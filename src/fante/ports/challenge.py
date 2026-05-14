"""ChallengePort — capability of running an interactive challenge for the player."""

from typing import Protocol

from fante.domain.challenge import ChallengeSpec
from fante.domain.profile import PlayerProfile


class ChallengePort(Protocol):
    def run(self, spec: ChallengeSpec, user_input: str, profile: PlayerProfile) -> int:
        """Present the challenge and return a player score in [0, 20].

        `user_input` is the original sentence the player typed for this turn —
        challenges may use it as context (e.g. the LLM evaluator scores it
        directly; interactive minigames typically ignore it). Adapters use the
        orchestrator's IO ports (StdinInput/StdoutOutput) so the same code
        works for terminal and (future) audio. The score is injected into the
        rules engine as `player_score`."""
        ...
