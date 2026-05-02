"""Domain events emitted by the orchestrator.

Events are immutable. Subscribers attach to the EventBus and react without
modifying the orchestrator. Phase 1.5 will add ProfilerSubscriber,
MonitorSubscriber, etc., on the same surface.
"""

from dataclasses import dataclass


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
