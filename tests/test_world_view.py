"""Functional tests for the world-view seam.

Drive real domain events through a real WorldDirector + install_world_view,
capturing the SceneState pushed to a fake WorldPort. Verifies the
event → scene contract without any renderer.
"""

import pytest

from fante.domain.events import ActionClassified, CheckResolved, TurnFinished
from fante.domain.rules import CheckResult, PlotDieFace
from fante.domain.scene import SceneState
from fante.domain.turn import ActionIntent
from fante.events.bus import EventBus
from fante.events.world_view import install_world_view
from fante.world.director import WorldDirector
from fante.world.manifest import ActorManifest, WorldManifest


def _make_manifest() -> WorldManifest:
    return WorldManifest(
        protagonist="fante",
        default_background="home",
        backgrounds=["home", "forest", "cave"],
        actors={
            "fante": ActorManifest(poses=["idle", "climbing"], moods=["neutral", "happy", "sad"])
        },
        fx=["sparkle", "puff"],
        action_poses={"climb": "climbing"},
        topic_backgrounds={"adventure": "forest"},
        outcome_fx={"success": "sparkle", "failure": "puff"},
    )


def _make_check(success: bool = True, topic: str | None = None) -> CheckResult:
    return CheckResult(
        rule_id="climb",
        pack_name="physics_basic",
        d20_rolls=[15],
        kept_roll=15,
        attribute_bonus=3,
        skill_bonus=0,
        situational_modifier=0,
        total=18,
        difficulty=12,
        success=success,
        plot_dice=[PlotDieFace.BLANK],
        applied_modifiers=[],
        narration_seed=None,
        knowledge_topic=topic,
    )


class FakeWorldPort:
    """Records every SceneState pushed to it."""

    def __init__(self) -> None:
        self.pushed: list[SceneState] = []

    def push(self, scene: SceneState) -> None:
        self.pushed.append(scene)

    @property
    def last(self) -> SceneState:
        return self.pushed[-1]


@pytest.fixture
def wired() -> tuple[EventBus, FakeWorldPort]:
    bus = EventBus()
    world = FakeWorldPort()
    install_world_view(bus, world, WorldDirector(_make_manifest()))
    return bus, world


@pytest.mark.functional
class TestWorldView:
    def test_action_sets_protagonist_pose(self, wired: tuple[EventBus, FakeWorldPort]) -> None:
        bus, world = wired
        bus.publish(ActionClassified(turn_index=1, intent=ActionIntent(rule_id="climb")))

        scene = world.last
        assert scene.actors[0].id == "fante"
        assert scene.actors[0].pose == "climbing"

    def test_unknown_action_falls_back_to_idle(self, wired: tuple[EventBus, FakeWorldPort]) -> None:
        bus, world = wired
        bus.publish(ActionClassified(turn_index=1, intent=ActionIntent(rule_id="teleport")))
        assert world.last.actors[0].pose == "idle"

    def test_success_adds_fx_and_topic_background(
        self, wired: tuple[EventBus, FakeWorldPort]
    ) -> None:
        bus, world = wired
        bus.publish(
            CheckResolved(turn_index=1, result=_make_check(success=True, topic="adventure"))
        )

        scene = world.last
        assert scene.fx == ["sparkle"]
        assert scene.actors[0].mood == "happy"
        assert scene.background == "forest"

    def test_failure_uses_puff_and_sad_mood(self, wired: tuple[EventBus, FakeWorldPort]) -> None:
        bus, world = wired
        bus.publish(CheckResolved(turn_index=1, result=_make_check(success=False)))

        scene = world.last
        assert scene.fx == ["puff"]
        assert scene.actors[0].mood == "sad"

    def test_turn_finished_returns_to_rest(self, wired: tuple[EventBus, FakeWorldPort]) -> None:
        bus, world = wired
        bus.publish(ActionClassified(turn_index=1, intent=ActionIntent(rule_id="climb")))
        bus.publish(CheckResolved(turn_index=1, result=_make_check(success=True)))
        bus.publish(TurnFinished(turn_index=1))

        scene = world.last
        assert scene.actors[0].pose == "idle"
        assert scene.actors[0].mood == "neutral"
        assert scene.fx == []


@pytest.mark.unit
class TestWorldManifest:
    def test_loads_real_data_manifest(self) -> None:
        from pathlib import Path

        manifest = WorldManifest.from_file(Path("data/world_manifest.yaml"))
        assert manifest.protagonist == "fante"
        assert manifest.has_pose("fante", "climbing")
        assert manifest.has_background("forest")
        assert manifest.action_poses["climb"] == "climbing"
