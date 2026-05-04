"""Turn-level domain types."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionIntent:
    """Structured action extracted from player input by the classifier."""

    rule_id: str
    context: dict[str, Any] = field(default_factory=dict)
