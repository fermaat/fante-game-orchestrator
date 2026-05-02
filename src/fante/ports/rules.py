"""RulesPort — capability of resolving game mechanics (dice rolls, checks)."""

from typing import Protocol

from fante.domain.rules import RollResult


class RulesPort(Protocol):
    def roll(self, spec: str) -> RollResult:
        """Roll dice according to spec (e.g. '2d6+3') and return the result."""
        ...
