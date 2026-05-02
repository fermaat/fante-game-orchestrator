"""Built-in event subscribers."""

from core_utils import logger

from fante.domain.events import DomainEvent
from fante.events.bus import EventBus


def install_logging_subscriber(bus: EventBus) -> None:
    """Subscribe a debug-level logger to every domain event."""

    def _log(event: DomainEvent) -> None:
        logger.debug(f"event: {type(event).__name__} {event!r}")

    bus.subscribe(DomainEvent, _log)
