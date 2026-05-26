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

from core_utils import logger

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
            logger.debug(f"challenge.gate rule_id={rule_meta.rule_id} -> skip (challenge=none)")
            return None
        if rule_meta.challenge_category is None:
            logger.debug(
                f"challenge.gate rule_id={rule_meta.rule_id} -> skip (no challenge_category)"
            )
            return None
        if rule_meta.challenge == "optional":
            roll = self._rng.random()
            if roll > self._prob:
                logger.debug(
                    f"challenge.gate rule_id={rule_meta.rule_id} -> skip "
                    f"(prob roll {roll:.2f} > threshold {self._prob:.2f})"
                )
                return None

        candidates = self._registry.filter(
            category=rule_meta.challenge_category,
            attribute=rule_meta.attribute,
            profile=profile,
        )
        if not candidates:
            logger.debug(
                f"challenge.gate rule_id={rule_meta.rule_id} -> skip "
                f"(no minigame matches category={rule_meta.challenge_category} "
                f"attribute={rule_meta.attribute})"
            )
            return None
        # Prefer candidates not in recent_history, but if the pool is so small
        # that everything is "recent", fall back to the full set rather than
        # deadlock returning None forever.
        fresh = [c for c in candidates if c.id not in self._recent]
        if fresh:
            candidates = fresh

        weights = [
            self._bias if (session_topic and session_topic in c.topics) else 1.0 for c in candidates
        ]
        chosen = self._rng.choices(candidates, weights=weights, k=1)[0]
        self._recent.append(chosen.id)
        return chosen.to_spec(session_topic)
