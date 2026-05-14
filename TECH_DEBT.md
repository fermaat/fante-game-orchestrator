# Technical debt & deferred decisions

Items consciously left out of past phases. Each entry: **what**, **why deferred**, **revisit when**.

Adding to this list is normal — it's the explicit log of choices we know we'll want to revisit.

---

## Challenge system (deferred from Phase 2.E)

### TD-CH-1 — Multi-turn minigames
Minigames that span several turns (e.g. "say your name once per turn for 3 turns") would require
persisting minigame state across turns and the selector knowing a session is "mid-challenge."
- **Why deferred:** complexity disproportionate to benefit at the start; single-turn covers the
  educational value of all the early ideas.
- **Revisit when:** we have a concrete educational scenario that needs cross-turn buildup
  (e.g. spaced repetition of vocabulary).

### TD-CH-2 — Session-level planning
Pre-compute which turns get minigames at session start (e.g. "minigames at turns 3, 7, 12") instead
of evaluating per-turn with a probability gate.
- **Why deferred:** random + cooldown gives enough variety; planning ahead adds an orthogonal
  scheduling concern.
- **Revisit when:** users complain that minigames feel arbitrary or clustered.

### TD-CH-3 — Adaptive difficulty
Adjust minigame parameters (`max_operand`, `time_limit`…) based on the player's recent success
history.
- **Why deferred:** we don't have a success-history store yet, and `min_age`/`max_age` cover
  the gross calibration.
- **Revisit when:** we have a session-stats subsystem (would naturally provide the input).

### TD-CH-4 — Audio I/O for challenges
Voice input for "say a color" type minigames.
- **Why deferred:** this is Phase 3 (speech-io-hub). The `InputPort`/`OutputPort` seams already
  support it transparently — no design change needed in challenge code.
- **Revisit when:** Phase 3 lands.

### TD-CH-5 — Pure-data minigame DSL
Define a minigame entirely in YAML without writing a Python adapter class.
- **Why deferred:** Python adapter + YAML config is the right ratio when the catalogue is small.
  A DSL only pays off past ~20 minigames.
- **Revisit when:** the `data/challenges/` folder grows past 10–15 distinct minigames.

### TD-CH-6 — Cooldown by category
`recent_history` today excludes by minigame ID. We could also exclude by category to avoid 3
consecutive "mental" minigames even if the IDs differ.
- **Why deferred:** trivial to add later; want to see if it actually happens in real play first.
- **Revisit when:** session logs show clustering of same-category minigames.

---

---

## Copper integration

### TD-COP-2 — Copper `/tap` is slow (~20s observed)
A single knowledge query takes 10–20s end-to-end because copper does two LLM calls
(retrieval + answer) and both use a 32k-context model. Suspected causes, in order of impact:

1. Copper uses the same heavyweight model for tap as for store — configure `COPPER_TAP_MODEL`
   to a smaller/faster model (tap doesn't need the big brain).
2. Fante sends raw JSON as the "question"; semantic retrieval works much better with natural
   language. Convert context dict → human-readable prompt in `CopperKnowledgeAdapter.query`.
3. Knowledge fetch blocks narrator generation. They are independent — could be issued in
   parallel and joined before the narrator call.

- **Why deferred:** we want copper working end-to-end first; perf optimisation is a follow-up.
- **Revisit when:** we have a profiler trace showing actual per-phase costs (use `core_utils.profiler`
  step blocks around the `httpx.post` and around each LLM call inside copper).

---

## How to add an entry

1. Pick an area heading (or add a new one).
2. Use the ID convention `TD-<AREA>-<N>` so we can reference items in commits/PRs.
3. Always include the three lines: short summary, **why deferred**, **revisit when**.
4. When an item is implemented, remove it (commit history will preserve the rationale).
