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

## Voice UX

### TD-VOX-1 — Hands-free acoustic wake-word ("Fante" by voice)
Today, voice mode uses push-to-talk: a key press (Enter) opens the mic, the VAD
captures the utterance, the mic closes. This works perfectly with a parent
supervising. For a more autonomous kid experience, we'd want a continuous
acoustic wake-word detector — say "Fante" out loud (no key press) and the system
starts listening.

Approach when we attack this:
1. **openWakeWord** (open source, ~100MB model). Train a custom wake word for
   "Fante" from ~50 voice samples (provided by us / the kid) via the project's
   notebook. Alternative: **Porcupine** (Picovoice) which has cleaner training
   but requires a free-tier account.
2. New module in fante (or speech-io-hub): a continuous `sounddevice.InputStream`
   feeding chunks to the detector. On detection, hand off to the existing VAD
   capture for the utterance proper.
3. CPU cost on M4 with openWakeWord is ~5-10% baseline. Negligible.
4. `WhisperInput` gains a third `input_mode`: `"wake_word"`, alongside
   `"push_to_talk"` and `"vad"`.

- **Why deferred:** push-to-talk is sufficient with a parent supervising; the
  effort (model train + integration + testing) is medium (~3-4 days).
- **Revisit when:** the kid is old enough to be autonomous in sessions, or
  parent fatigue with pressing Enter justifies the engineering.

### TD-VOX-2 — Hybrid jukebox + RPG (music while adventuring)
Today `jukebox` and `skill` are mutually-exclusive modes: when you're in jukebox
you can't play, when you're in adventure there's no music. The natural evolution
is **music as a layer**, not as a separate mode:

- In adventure mode, the narrator (or the rule check, or a story scene) can
  trigger `music_client.play(mood="tension")` etc. → music plays in the
  background while the RPG continues.
- The kid can still say "fante para" or "fante otra" at any time, and that
  intercepts the music layer without leaving adventure.
- Jukebox-as-mode becomes optional — useful when the kid only wants to listen
  with no game, redundant when music is ambient.

Implementation hints when we attack this:
1. Split `Mode` literal: `interaction_mode = "rpg"` plus a separate
   `music_state` tracked in `GameManager` (or queried from music-hub via
   `/status`).
2. Add hooks in `GameManager.process_turn` (or in the narrator-side) where the
   story can request music: e.g. an event published on `EventBus` like
   `MusicCueRequested(mood="...")` that a `MusicCueSubscriber` translates into
   `music_client.play(...)`.
3. Per-rule metadata in the engine for music cues (analogous to
   `knowledge_topic` / `challenge_category`): `music_mood: "tension"` on a rule
   triggers tension music when that check resolves.
4. Wake-word + music: when wake word fires while music is playing, music ducks
   automatically so the mic captures cleanly (depends on TD-VOX-1 + an explicit
   duck/restore endpoint in music-hub).

- **Why deferred:** the kid is happy with separate jukebox-as-mode right now;
  the architecture supports the future without changes (music-hub is already
  an independent service). The orchestration glue is what's missing.
- **Revisit when:** sessions show the kid wants music while playing (or when
  TD-VOX-1 lands and ambient soundtrack becomes natural).

---

## How to add an entry

1. Pick an area heading (or add a new one).
2. Use the ID convention `TD-<AREA>-<N>` so we can reference items in commits/PRs.
3. Always include the three lines: short summary, **why deferred**, **revisit when**.
4. When an item is implemented, remove it (commit history will preserve the rationale).
5. If an item is promoted to a phase, leave a one-line pointer in this file (like the
   challenge note at the top) so it's discoverable from here too.
