"""ChallengeSelectorPort — capability of choosing which (if any) minigame to run.

The selector implementation lives in `fante.challenge.selector` and consults a
`ChallengeRegistry` of minigame definitions, applying filters (category, attribute,
age), session-topic bias, and recent-history exclusion to produce a `ChallengeSpec`
or `None` ("no minigame this turn → fall back to dice/evaluator").
"""

from typing import Protocol

from fante.domain.challenge import ChallengeSpec, RuleMeta
from fante.domain.profile import PlayerProfile


class ChallengeSelectorPort(Protocol):
    def pick(
        self,
        rule_meta: RuleMeta,
        session_topic: str | None,
        profile: PlayerProfile,
    ) -> ChallengeSpec | None:
        """Return a ChallengeSpec to run, or None to skip the minigame phase."""
        ...
