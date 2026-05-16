# Technical debt & deferred decisions

Items consciously left out of past phases. Each entry: **what**, **why deferred**, **revisit when**.

Adding to this list is normal — it's the explicit log of choices we know we'll want to revisit.

> Items previously tracked here as `TD-CH-1`, `TD-CH-3`, `TD-CH-4`, `TD-CH-5`, `TD-CH-6`
> have been promoted to **Phase 3.6** (Challenge system depth) in `SUMMARY.md` — see the
> roadmap there. `TD-CH-2` (session-level minigame planning) was dropped from the backlog
> entirely; random + cooldown is good enough.

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
5. If an item is promoted to a phase, leave a one-line pointer in this file (like the
   challenge note at the top) so it's discoverable from here too.
