"""AutomaticChallenge — sentinel adapter meaning "no interaction, fall back to dice".

The selector returns a `ChallengeSpec` pointing to this adapter when the rule is
`challenge: none`, or when no interactive minigame is eligible. `GameManager`
treats the returned 0 as "no player_score → engine rolls the d20."
"""

from fante.domain.challenge import ChallengeSpec
from fante.domain.profile import PlayerProfile


class AutomaticChallenge:
    def run(self, spec: ChallengeSpec, user_input: str, profile: PlayerProfile) -> int:
        return 0
