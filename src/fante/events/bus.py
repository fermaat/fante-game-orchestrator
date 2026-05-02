"""In-process pub/sub for domain events.

Sync dispatch. A subscriber to a base event type also receives subclasses
(MRO walk), so a single `DomainEvent` subscriber sees everything — useful
for logging and replay.
"""

from collections import defaultdict
from collections.abc import Callable
from typing import TypeVar

from core_utils import logger

from fante.domain.events import DomainEvent

E = TypeVar("E", bound=DomainEvent)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[type[DomainEvent], list[Callable[[DomainEvent], None]]] = (
            defaultdict(list)
        )

    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> None:
        self._subscribers[event_type].append(handler)  # type: ignore[arg-type]

    def publish(self, event: DomainEvent) -> None:
        for cls in type(event).__mro__:
            for handler in self._subscribers.get(cls, ()):
                try:
                    handler(event)
                except Exception:
                    # A failing subscriber must not break the game loop.
                    logger.exception(f"Subscriber {handler!r} failed for {event!r}")
