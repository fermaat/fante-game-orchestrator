"""KnowledgePort — capability of querying lore / educational content."""

from typing import Any, Protocol


class KnowledgePort(Protocol):
    def query(self, topic: str, context: dict[str, Any] | None = None) -> str:
        """Return a knowledge snippet relevant to topic. Empty string if nothing found."""
        ...
