"""Dad's Monitor — writes every DomainEvent as a JSON line to a sink file.

Enabled via FANTE_MONITOR=1. Useful for Fernando to watch what the game is
doing while the kid plays:

    FANTE_MONITOR=1 python -m fante
    # in another terminal:
    tail -f logs/monitor.jsonl
"""

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path

from fante.domain.events import DomainEvent
from fante.events.bus import EventBus


def install_dad_monitor(bus: EventBus, sink_path: Path) -> None:
    sink_path.parent.mkdir(parents=True, exist_ok=True)

    def _write(event: DomainEvent) -> None:
        line = json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": type(event).__name__,
                "payload": dataclasses.asdict(event),
            },
            ensure_ascii=False,
        )
        with open(sink_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    bus.subscribe(DomainEvent, _write)
