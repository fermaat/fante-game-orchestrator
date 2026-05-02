"""Unit tests for EventBus."""

import pytest

from fante.domain.events import DomainEvent, NarrationGenerated, TurnStarted
from fante.events.bus import EventBus

pytestmark = pytest.mark.unit


def test_subscribers_receive_events_of_the_subscribed_type() -> None:
    bus = EventBus()
    seen: list[TurnStarted] = []
    bus.subscribe(TurnStarted, seen.append)

    bus.publish(TurnStarted(turn_index=1, user_input="hola"))
    bus.publish(NarrationGenerated(turn_index=1, narration="text"))

    assert len(seen) == 1
    assert seen[0].user_input == "hola"


def test_subscribers_to_base_type_receive_all_events() -> None:
    bus = EventBus()
    seen: list[DomainEvent] = []
    bus.subscribe(DomainEvent, seen.append)

    bus.publish(TurnStarted(turn_index=1, user_input="hola"))
    bus.publish(NarrationGenerated(turn_index=1, narration="text"))

    assert len(seen) == 2


def test_failing_subscriber_does_not_break_dispatch() -> None:
    bus = EventBus()

    def raises(event: DomainEvent) -> None:
        raise RuntimeError("subscriber error")

    seen: list[DomainEvent] = []
    bus.subscribe(DomainEvent, raises)
    bus.subscribe(DomainEvent, seen.append)

    bus.publish(TurnStarted(turn_index=1, user_input="hola"))
    assert len(seen) == 1
