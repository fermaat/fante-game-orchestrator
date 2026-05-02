"""Domain types for game rules."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RollResult:
    """Result of a dice roll."""

    spec: str
    total: int
    breakdown: list[int]

    def __str__(self) -> str:
        rolls = " + ".join(str(r) for r in self.breakdown)
        if len(self.breakdown) > 1:
            return f"{self.spec} → [{rolls}] = {self.total}"
        return f"{self.spec} → {self.total}"
