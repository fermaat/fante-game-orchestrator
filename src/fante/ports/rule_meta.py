"""RuleMetaProvider — capability of querying a rule's metadata without resolving a check.

Implemented by `MCPRulesAdapter` via the engine's `get_rule_meta` MCP tool. Used by
the challenge layer to decide which minigame (if any) to run before the engine resolves
the action.
"""

from typing import Protocol

from fante.domain.challenge import RuleMeta


class RuleMetaProvider(Protocol):
    def get_rule_meta(self, rule_id: str) -> RuleMeta:
        """Return the rule's metadata. Raises if rule_id is unknown."""
        ...
