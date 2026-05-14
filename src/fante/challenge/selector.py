"""ChallengeSelector — picks which (if any) minigame to run for a given rule.

Policy:
  1. If rule.challenge == "none" → return None.
  2. If rule.challenge == "optional", roll the activation probability gate.
  3. Filter the registry by category, attribute, and age.
  4. Exclude recently used minigame IDs (sliding window).
  5. Weighted-random pick — minigames whose `topics` include `session_topic`
     get a multiplicative boost.
  6. None of the above match → return None (caller falls back to dice/evaluator).
"""

import random
from collections import deque

from fante.challenge.registry import ChallengeRegistry
from fante.domain.challenge import ChallengeSpec, RuleMeta
from fante.domain.profile import PlayerProfile


class ChallengeSelector:
    def __init__(
        self,
        registry: ChallengeRegistry,
        recent_history_size: int = 3,
        optional_activation_prob: float = 0.5,
        topic_bias_weight: float = 2.0,
        rng: random.Random | None = None,
    ) -> None:
        self._registry = registry
        self._recent: deque[str] = deque(maxlen=recent_history_size)
        self._prob = optional_activation_prob
        self._bias = topic_bias_weight
        self._rng = rng or random.Random()

    def pick(
        self,
        rule_meta: RuleMeta,
        session_topic: str | None,
        profile: PlayerProfile,
    ) -> ChallengeSpec | None:
        if rule_meta.challenge == "none":
            return None
        if rule_meta.challenge_category is None:
            return None
        if rule_meta.challenge == "optional" and self._rng.random() > self._prob:
            return None

        candidates = self._registry.filter(
            category=rule_meta.challenge_category,
            attribute=rule_meta.attribute,
            profile=profile,
        )
        candidates = [c for c in candidates if c.id not in self._recent]
        if not candidates:
            return None

        weights = [
            self._bias if (session_topic and session_topic in c.topics) else 1.0 for c in candidates
        ]
        chosen = self._rng.choices(candidates, weights=weights, k=1)[0]
        self._recent.append(chosen.id)
        return chosen.to_spec(session_topic)
