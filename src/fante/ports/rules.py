"""RulesPort — capability of resolving game mechanics (dice rolls, checks)."""

from typing import Any, Protocol

from fante.domain.actor import Actor
from fante.domain.rules import CheckResult, RollResult


class RulesPort(Protocol):
    def roll(self, spec: str) -> RollResult:
        """Roll dice according to spec (e.g. '2d6+3') and return the result."""
        ...

    def check(
        self,
        rule_id: str,
        actor: Actor,
        context: dict[str, Any] | None = None,
        player_score: int | None = None,
    ) -> CheckResult:
        """Resolve an action check for actor against rule_id."""
        ...
