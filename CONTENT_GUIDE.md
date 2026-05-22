# Content guide — extending Fante without touching the core

This document maps **what kinds of content** you can add to enrich a session, **where**
each one lives, and **how** to add it. The architecture is designed so most extension
work is YAML/markdown edits — Python code is only needed for genuinely new *kinds* of
minigames.

> If you find yourself writing Python to add new game content, stop. Either the right
> hook already exists (re-read this guide), or there's a missing abstraction that should
> be a small refactor, not a content edit.

---

## What counts as "content" vs "core"

| Layer | Examples | Where |
|---|---|---|
| **Content** (this guide) | Rules, minigames, lore, prompts, player profile | YAML / markdown |
| **Core** (not this guide) | Ports, adapters, GameManager, classifier code | Python in `src/fante/` and the engine/copper repos |

If you change a port signature or add an adapter class, that's core work and lives in a
phase-implementation plan, not in content.

---

## Quick map: what to add → where

| You want to… | Lives in repo | Lives at | Code change? |
|---|---|---|---|
| Add a new game rule (e.g. `juggle`) | `fante-mcp-game-rules` | `src/mcp_game_rules/packs/builtin/*.yaml` | No |
| Make an existing rule trigger copper | `fante-mcp-game-rules` | `*.yaml` → `knowledge_topic: <topic>` | No |
| Make an existing rule trigger a minigame | `fante-mcp-game-rules` | `*.yaml` → `challenge: optional, challenge_category: <cat>` | No |
| Add a new minigame variant of an existing kind (e.g. another color set) | `fante-game-orchestrator` | `data/challenges/*.yaml` | No |
| Add a brand-new kind of minigame (e.g. "spell the word") | `fante-game-orchestrator` | `data/challenges/*.yaml` + a new adapter | Yes — one Python file |
| Expand a copper mind's lore/curriculum | `fante-game-orchestrator` + `copper` | `data/copper_minds/<topic>/raw/*.md` + ingest via script | No |
| Add a brand-new knowledge topic | `fante-game-orchestrator` + `copper` | Forge a new mind + map in config | No |
| Tweak how the narrator speaks | `fante-game-orchestrator` | `prompts/narrator.yaml` | No |
| Tweak how the classifier extracts context | `fante-game-orchestrator` | `prompts/classifier.yaml` | No |
| Change the player character | `fante-game-orchestrator` | `data/player_profile.json` | No |

---

## 1. Game rules (engine repo)

Rules live in YAML packs under `fante-mcp-game-rules/src/mcp_game_rules/packs/builtin/`.
A rule defines: which attribute/skill it uses, base difficulty, modifiers, narration seeds
on success/failure, and the optional hooks that wire knowledge and minigames.

### Example: adding a new rule to an existing pack

In `physics_basic.yaml`:

```yaml
- id: juggle
  description: Juggle several objects at once.
  attribute: speed
  skill: acrobatics
  base_difficulty: 11
  knowledge_topic: adventure          # optional → triggers copper
  challenge: optional                  # → may trigger a minigame
  challenge_category: reflexes         # → tells the orchestrator's selector what kind
  modifiers:
    - when:
        field: context.objects
        op: gte
        value: 4
      delta: 3
      reason: too many objects
  on_success: "You keep them all in the air with practiced ease."
  on_failure: "One escapes and clatters to the floor."
  complexity_tier: 1
```

### Fields cheat sheet

| Field | Optional | Purpose |
|---|---|---|
| `id` | required | unique within engine; classifier matches by this |
| `attribute` | required | which `Attributes` field contributes to the roll |
| `skill` | optional | named skill bonus from the player profile |
| `base_difficulty` | required | DC the player needs to beat |
| `modifiers` | optional | situational +/- delta based on context |
| `on_success` / `on_failure` | optional | seed text the narrator uses |
| `knowledge_topic` | optional | when set, copper queries this topic after the check |
| `challenge` | optional, default `none` | `none` / `optional` / `required` |
| `challenge_category` | optional | `physical` / `mental` / `reflexes` / `language` / `memory` |
| `complexity_tier` | optional, default 1 | 1–5, currently informational |

### Workflow

1. Edit/create YAML in the engine repo.
2. `./run_local_checks.sh` in the engine repo.
3. Bump engine version, commit, push, release.
4. In fante: `pdm lock && pdm install`.

---

## 2. Minigames — variants vs new kinds

There are **two ways** to add a minigame, depending on whether you need new Python logic.

### 2a. New variant of an existing kind — pure YAML

If you want another set of colours, another arithmetic config, etc., add a YAML file to
`data/challenges/`:

```yaml
# data/challenges/color_naming_animals.yaml
id: color_naming_animals
adapter: color_naming                 # ← reuses the existing ColorNamingChallenge class
categories: [physical, language]
attributes: [awareness, presence]
topics: [adventure, lore]
min_age: 3
max_age: 9
prompt: "Antes de actuar, dime:"
config:
  pool:
    - prompt: "¿De qué color es un león?"
      accepted: [amarillo, dorado, marrón, marron, "marrón claro"]
    - prompt: "¿De qué color es un pingüino?"
      accepted: [negro, "blanco y negro", blanco]
```

That's it. Reload fante and the selector can pick this one.

#### Writing good `accepted` lists (lessons from real play)

The `accepted` list is the set of strings the player can say that count as "right".
A few rules of thumb after observing real sessions:

- **The adapter normalizes case, strips accents, and strips trailing plural `s` on each
  token.** `"MARRON"`, `"marrón"`, `"marrones"` all match the single entry `"marrón"`.
  You don't need to list both singular and plural forms.
- **Spanish gender agreement is NOT normalized.** Include both forms when the noun
  is feminine:
  - `"nieve"` (f) → must include both `blanco` AND `blanca`
  - `"cueva"` (f) → `oscuro` AND `oscura`
  - `"sangre"` (f) → `rojo` AND `roja`
  - Conversely, adjectives that don't change with gender (marrón, café, azul, verde,
    gris, naranja) only need one entry.
- **Plural variants are auto-handled.** Thanks to plural normalization, listing
  `verde` already accepts `verdes`. List both ONLY if the spelling differs in
  unrelated ways (rare for colour names).
- **Anticipate "almost right" answers from a child.** For a "wet wood" prompt, kids
  often say `oscuro` or `negro` even though `marrón` is the "right" answer; if those
  are acceptable to you, include them. It's better to be generous than punitive —
  the scoring is binary (17 for match, 9 for "tried but missed").
- **Combinatorial colours**: `"rojo y naranja"`, `"azul oscuro"`, `"verde claro"`
  — kids do say these, especially when prompted "what colour is fire?". Include the
  ones that feel natural; you don't need to enumerate every possible permutation.

Quick checklist before committing a new pool entry:

1. Is the noun in the question feminine? → add the `-a` variants.
2. Is the noun plural? → add the plural variants.
3. What would a 2–4 year old actually say if shown the thing? → include those even
   if "less correct".
4. Are there compound answers that are obvious from the prompt? → include them too.

If you find yourself wishing for fuzzy matching (e.g. accepting `roi` for `rojo`),
that's a signal that the adapter could be smarter — open a TECH_DEBT entry rather
than padding the YAML with every misspelling.

### 2b. Brand-new kind of minigame — YAML + adapter

If the existing adapters can't do what you want, add one Python file in
`src/fante/adapters/` and a YAML registry entry.

**Example: spell-the-word minigame**

`src/fante/adapters/spell_word_challenge.py`:

```python
import random
from fante.domain.challenge import ChallengeSpec
from fante.domain.profile import PlayerProfile
from fante.ports.io import InputPort, OutputPort

class SpellWordChallenge:
    def __init__(
        self,
        input_port: InputPort,
        output_port: OutputPort,
        rng: random.Random | None = None,
    ) -> None:
        self._in = input_port
        self._out = output_port
        self._rng = rng or random.Random()

    def run(self, spec: ChallengeSpec, user_input: str, profile: PlayerProfile) -> int:
        words: list[str] = spec.metadata.get("config", {}).get("words", [])
        if not words:
            return 0
        word = self._rng.choice(words)
        self._out.emit(f"Deletrea la palabra: {word.upper()}")
        answer = self._in.read()
        if answer is None:
            return 0
        if answer.strip().lower() == word.lower():
            return 18
        return 7
```

`data/challenges/spell_word.yaml`:

```yaml
id: spell_word
adapter: spell_word
categories: [language, memory]
attributes: [intellect, awareness]
topics: [languages]
min_age: 5
max_age: 99
prompt: ""
config:
  words: [elefante, casa, montaña, río, libro]
```

`src/fante/compose.py` — register the new adapter in `_build_challenge()`:

```python
from fante.adapters.spell_word_challenge import SpellWordChallenge
...
challenge_adapters["spell_word"] = SpellWordChallenge(adapters_in, adapters_out)
```

That's the minimum bar for a new minigame kind: one adapter class, one registry YAML,
one registration line in compose.

### When does a minigame fire?

The selector picks a minigame when **all** of these hold:

1. The rule has `challenge: optional` or `challenge: required` and a `challenge_category`.
2. If `optional`, an internal probability gate passes (default 50%, see `FANTE_CHALLENGE_OPTIONAL_PROB`).
3. The registry has at least one minigame whose `categories` include the rule's `challenge_category`.
4. The minigame's `attributes` are empty OR include the rule's `attribute`.
5. The player's `profile.age` (if set) falls within `[min_age, max_age]`.
6. The minigame ID isn't in the recent-history sliding window (default size 3).

Minigames whose `topics` include the `session_topic` get a 2× weight in the random pick
(see `FANTE_CHALLENGE_TOPIC_BIAS`).

---

## 3. Knowledge content (copper minds)

Each "topic" Fante can query (`adventure`, `math`, `languages`, `lore`) corresponds to a
copper mind. Minds live on disk in `~/.copper/minds/<name>/`, but their **source content**
lives in this repo under `data/copper_minds/<topic>/raw/*.md` for reproducibility.

### Adding content to an existing mind

1. Add or edit markdown files in `data/copper_minds/<topic>/raw/`.
2. Re-run the bootstrap script — it forges any new minds and re-ingests all raw content:
   ```bash
   ./scripts/setup_copper_minds.sh
   ```
3. Verify with a direct tap:
   ```bash
   curl -s -X POST "$FANTE_COPPER_URL/minds/<topic>/tap" \
     -H "Content-Type: application/json" \
     -d '{"question": "test", "personality": "tap.<topic>"}' | jq .answer
   ```

### Adding a brand-new topic

For a new educational area (e.g. `geography`):

1. Add markdown sources at `data/copper_minds/geography/raw/*.md`.
2. Add the topic to `FanteSettings.fante_copper_mind_map` (or override via env):
   ```
   FANTE_COPPER_MIND_MAP={"adventure":"adventure","math":"math","geography":"geography",...}
   ```
3. Add a personality prompt in **copper** at `src/copper/prompts/tap.geography.yaml` — see
   `FANTE_TAP_PERSONALITIES.md` in the copper repo for format and voice guidelines.
4. Re-run the bootstrap; it'll forge `geography` and ingest.
5. To make a rule use the new topic, set `knowledge_topic: geography` on that rule in the
   engine.

> The bootstrap script lives at `scripts/setup_copper_minds.sh`. It reads
> `FANTE_COPPER_URL` from `.env`, forges any missing minds, sets `tap_personality`, and
> ingests all `data/copper_minds/<topic>/raw/*.md` files.

---

## 4. Player profile

The player character sheet is JSON at `data/player_profile.json`. Editable fields:

```json
{
  "schema_version": 2,
  "name": "Fante",
  "age": 6,
  "background": "Joven explorador con un elefante de peluche",
  "preferences": ["elefantes", "rocas brillantes", "treparlo todo"],
  "attributes": {"strength": 3, "speed": 5, "intellect": 4, ...},
  "skills": {"athletics": 1, "acrobatics": 2},
  "tags": ["pequeño", "curioso"],
  "language": "mixed",
  "seed_prompt": "Estás en la entrada de un bosque..."
}
```

| Field | Effect |
|---|---|
| `name`, `background`, `preferences` | Narrator-side colour; surfaces in narration |
| `age` | Filters which minigames apply (`min_age`/`max_age`) |
| `attributes` | Engine rolls use these as bonuses |
| `skills` | Named bonuses keyed to rule skills (e.g. `athletics` boosts `climb`) |
| `tags` | Used by engine modifiers (e.g. `heavy_armor`) |
| `language` | `es` / `en` / `mixed` — narrator language mode |
| `seed_prompt` | First-turn opening scene the narrator builds from |

No restart needed — fante reads the file each session.

---

## 5. Narrator / classifier / evaluator prompts

Three YAML prompts live in `prompts/`:

| File | What it shapes |
|---|---|
| `narrator.yaml` | Voice, language rules, how internal context is consumed |
| `classifier.yaml` | How the classifier picks a `rule_id` and extracts context fields |
| `evaluator.yaml` | How the LLM scores a player input as a performance |

Edit any of these and the next process restart picks them up. Useful for:

- Adjusting tone for a younger/older player
- Adding new context fields the classifier should extract (e.g. `weather: rain`)
- Tweaking the evaluator's grading rubric

> When you add a new context field via the classifier, make sure the engine has a
> matching modifier in some rule's YAML, otherwise the field is parsed but unused.

### Narration style (length / verbosity)

`narrator.yaml` does NOT hardcode how many sentences the narrator writes. Length and
density live in a separate **style** dimension, controlled by `FANTE_NARRATION_STYLE`
in `.env`. The three preset styles are defined in
[src/fante/adapters/bridge_narrator.py](src/fante/adapters/bridge_narrator.py)
(`_STYLE_INSTRUCTION` dict) and injected into the narrator prompt at startup as
the `$style_instruction` placeholder:

| Value | Length target | When to use |
|---|---|---|
| `concise` (default) | 2 short sentences max | Young child playing by voice — Fante's case |
| `balanced` | 3–4 sentences with one vivid image | School-age child, or text mode |
| `rich` | 5–6 sentences with sensory detail | Adult playing, or "demo" sessions |

Switch with `FANTE_NARRATION_STYLE=balanced` in `.env` and restart. No code change
required.

To **tune the wording** of a style (e.g. push `balanced` to be a bit longer), edit
the corresponding entry in `_STYLE_INSTRUCTION`. To **add a new style**, append a
new key to the `NarrationStyle` literal and to `_STYLE_INSTRUCTION`; setting it in
`.env` will then pick it up.

---

## Common tasks at a glance

| Task | Files | Code? | Restart? |
|---|---|---|---|
| New rule | engine `*.yaml` | no | new engine release + `pdm install` |
| New rule with copper hook | engine `*.yaml` (set `knowledge_topic`) | no | engine release |
| New rule with minigame hook | engine `*.yaml` (set `challenge` + `challenge_category`) | no | engine release |
| New colour set for `color_naming` | `data/challenges/*.yaml` | no | fante restart |
| New kind of minigame | `data/challenges/*.yaml` + new adapter + register in compose | yes (1 py file) | fante restart |
| More copper lore | `data/copper_minds/<topic>/raw/*.md` + bootstrap script | no | nothing |
| New copper topic | markdown + mind_map config + copper personality | no (copper side YAML) | bootstrap script |
| Update character | `data/player_profile.json` | no | next session |
| Change narrator voice | `prompts/narrator.yaml` | no | fante restart |
| Change narration length/style | `FANTE_NARRATION_STYLE` in `.env` (`concise`/`balanced`/`rich`) | no | fante restart |
| Add a new narration style | `_STYLE_INSTRUCTION` in `bridge_narrator.py` + literal update | yes (1 py file) | fante restart |
| Teach classifier a new context field | `prompts/classifier.yaml` + engine modifier | no | fante restart + engine release if modifier changed |

---

## Verification habits

- After **engine YAML** edits: `./run_local_checks.sh` in the engine repo.
- After **challenge YAML** edits: `pdm run pytest tests/test_challenge_selector.py -v` to ensure the YAML parses.
- After **copper content** edits: re-run the bootstrap script, then `curl` the `/tap` endpoint directly to verify the personality + content combination.
- After **narrator/classifier prompt** edits: run the e2e once and check the relevant `DEBUG` logs:
  - `narrator.turn_input (full): ...` for what's reaching the narrator
  - `ActionClassified intent=...` for what the classifier returned
  - `challenge.meta / challenge.pick / challenge.run` for the minigame phase

If a content addition silently does nothing in play, the cause is almost always:

1. Engine release not picked up here (`pdm lock && pdm install`).
2. Rule isn't annotated with `challenge` / `knowledge_topic`.
3. Registry filters excluded the candidate (wrong category, age, recent-history collision).
4. `FANTE_CHALLENGE_ENABLED` or `FANTE_COPPER_ENABLED` is `false`.
