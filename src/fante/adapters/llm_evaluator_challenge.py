"""LLMEvaluatorChallenge — wraps `LLMPerformanceEvaluator` behind the ChallengePort.

This is the "verbose description" challenge: the player demonstrates skill by the
quality and detail of the sentence they typed for this turn. No extra interaction —
we just feed `user_input` to the LLM evaluator and use its score.

Useful as the default for any rule where there's no specific minigame defined.
"""

from fante.domain.challenge import ChallengeSpec
from fante.domain.profile import PlayerProfile
from fante.ports.evaluator import PerformanceEvaluatorPort


class LLMEvaluatorChallenge:
    def __init__(self, evaluator: PerformanceEvaluatorPort) -> None:
        self._evaluator = evaluator

    def run(self, spec: ChallengeSpec, user_input: str, profile: PlayerProfile) -> int:
        # spec.metadata may carry the rule's context; not required by the evaluator.
        return self._evaluator.score(user_input, profile, None)
