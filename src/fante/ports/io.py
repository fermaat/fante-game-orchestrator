"""InputPort / OutputPort — player-facing I/O capabilities.

Sync in Phase 1.0; async variants will be added when streaming/voice arrives.
"""

from typing import Protocol


class InputPort(Protocol):
    """Source of player utterances. Returns None when the input stream ends
    (e.g. EOF, user typed `quit`)."""

    def read(self) -> str | None: ...


class OutputPort(Protocol):
    """Sink for narration delivered to the player."""

    def emit(self, text: str) -> None: ...
