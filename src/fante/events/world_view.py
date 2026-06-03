"""World view — bridges the EventBus to a WorldPort renderer.

Subscribes a `WorldDirector` to the relevant domain events and pushes the
resulting `SceneState` to the `WorldPort` after each one. Mirrors the
`dad_monitor` installer pattern.
"""

from fante.domain.events import ActionClassified, CheckResolved, TurnFinished
from fante.events.bus import EventBus
from fante.ports.world import WorldPort
from fante.world.director import WorldDirector


def install_world_view(bus: EventBus, world: WorldPort, director: WorldDirector) -> None:
    def _on_action(event: ActionClassified) -> None:
        director.on_action(event.intent)
        world.push(director.build_scene())

    def _on_check(event: CheckResolved) -> None:
        director.on_check(event.result)
        world.push(director.build_scene())

    def _on_turn_finished(event: TurnFinished) -> None:
        director.on_turn_finished()
        world.push(director.build_scene())

    bus.subscribe(ActionClassified, _on_action)
    bus.subscribe(CheckResolved, _on_check)
    bus.subscribe(TurnFinished, _on_turn_finished)
