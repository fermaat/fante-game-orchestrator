"""Domain events emitted by the orchestrator.

Events are immutable. Subscribers attach to the EventBus and react without
modifying the orchestrator.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fante.domain.rules import CheckResult
    from fante.domain.turn import ActionIntent


@dataclass(frozen=True)
class DomainEvent:
    """Marker base class for all domain events."""

    turn_index: int


@dataclass(frozen=True)
class TurnStarted(DomainEvent):
    user_input: str


@dataclass(frozen=True)
class NarrationGenerated(DomainEvent):
    narration: str


@dataclass(frozen=True)
class TurnFinished(DomainEvent):
    pass


@dataclass(frozen=True)
class ActionClassified(DomainEvent):
    intent: "ActionIntent"


@dataclass(frozen=True)
class CheckResolved(DomainEvent):
    result: "CheckResult"
