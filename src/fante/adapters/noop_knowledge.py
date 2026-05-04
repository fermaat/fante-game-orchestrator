"""NoopKnowledgeAdapter — KnowledgePort that always returns empty string.

Placeholder until a real knowledge backend (Phase 2.C) is wired in.
"""

from typing import Any


class NoopKnowledgeAdapter:
    """KnowledgePort adapter that returns no knowledge."""

    def query(self, topic: str, context: dict[str, Any] | None = None) -> str:
        return ""
