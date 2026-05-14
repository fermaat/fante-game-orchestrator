"""Domain types for the challenge / minigame system.

A challenge is a small interactive (or automatic) test the player goes through
before the rules engine resolves a check. Its output is a `player_score` (0–20)
that the engine consumes via the existing `rules.check(..., player_score=...)`
path.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

ChallengeKind = Literal["none", "optional", "required"]
ChallengeCategory = Literal["physical", "mental", "reflexes", "language", "memory"]


@dataclass(frozen=True)
class RuleMeta:
    """Subset of a Rule's metadata needed before resolving a check.

    Comes from `MCPRulesAdapter.get_rule_meta` (engine MCP tool of the same name).
    """

    rule_id: str
    pack_name: str
    attribute: str | None
    skill: str | None
    base_difficulty: int
    knowledge_topic: str | None
    challenge: ChallengeKind
    challenge_category: ChallengeCategory | None


@dataclass
class ChallengeSpec:
    """A concrete challenge instance ready to be run.

    Built by the `ChallengeSelector` from a registry definition plus runtime
    context. `adapter_id` tells the factory which adapter implements this kind
    of challenge.
    """

    id: str
    adapter_id: str
    prompt: str
    category: ChallengeCategory
    metadata: dict[str, Any] = field(default_factory=dict)
