"""Unit tests for the Dad's Monitor subscriber."""

import json
from pathlib import Path

import pytest

from fante.domain.events import NarrationGenerated, TurnFinished, TurnStarted
from fante.events.bus import EventBus
from fante.events.dad_monitor import install_dad_monitor


@pytest.mark.unit
class TestDadMonitor:
    def test_writes_one_line_per_event(self, tmp_path: Path) -> None:
        sink = tmp_path / "monitor.jsonl"
        bus = EventBus()
        install_dad_monitor(bus, sink)

        bus.publish(TurnStarted(turn_index=1, user_input="hola"))
        bus.publish(NarrationGenerated(turn_index=1, narration="¡Hola!"))
        bus.publish(TurnFinished(turn_index=1))

        lines = sink.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3

    def test_each_line_is_valid_json(self, tmp_path: Path) -> None:
        sink = tmp_path / "monitor.jsonl"
        bus = EventBus()
        install_dad_monitor(bus, sink)
        bus.publish(TurnStarted(turn_index=1, user_input="test"))

        line = sink.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert data["type"] == "TurnStarted"
        assert "ts" in data
        assert data["payload"]["user_input"] == "test"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        sink = tmp_path / "logs" / "nested" / "monitor.jsonl"
        bus = EventBus()
        install_dad_monitor(bus, sink)
        bus.publish(TurnFinished(turn_index=1))
        assert sink.exists()

    def test_appends_across_events(self, tmp_path: Path) -> None:
        sink = tmp_path / "monitor.jsonl"
        bus = EventBus()
        install_dad_monitor(bus, sink)
        bus.publish(TurnStarted(turn_index=1, user_input="a"))
        bus.publish(TurnStarted(turn_index=2, user_input="b"))

        lines = sink.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[1])["payload"]["turn_index"] == 2
