"""PerformanceEvaluatorPort — scores player engagement for skill-mode checks."""

from typing import Any, Protocol

from fante.domain.profile import PlayerProfile


class PerformanceEvaluatorPort(Protocol):
    def score(
        self,
        player_input: str,
        profile: PlayerProfile,
        context: dict[str, Any] | None = None,
    ) -> int:
        """Return a score in [1, 20] representing player engagement/intent."""
        ...
