# fante-game-orchestrator — Claude reference summary

## Purpose
Game-loop orchestrator for a voice/text RPG, primarily designed for Fernando's son
("Fante"). Acts as the central glue: receives player input, queries an LLM narrator
via core-llm-bridge, applies game rules, and (later) routes output to TTS / Godot.

The architecture is **ports & adapters**: the orchestrator depends on Protocol-based
capabilities, and concrete adapters plug in via a composition root. Game-specific
content (profile, prompts) lives in *data*, so the same engine can power other games.

## Architecture

```
src/fante/
├── __init__.py
├── __main__.py             # `python -m fante`
├── main.py                 # CLI entry — calls compose.build_game().run()
├── compose.py              # Composition root: wires adapters → ports → GameManager (incl. jukebox)
├── jukebox/                # NEW — jukebox mode (voice → core-music-hub)
│   ├── __init__.py
│   ├── intent.py           # JukeboxIntentClassifier — LLM parses play/stop/next/list/exit
│   └── handler.py          # JukeboxHandler — intent → MusicHubClient HTTP calls
├── config.py               # FanteSettings (subclass of bridge Settings)
├── manager.py              # GameManager — central orchestrator (knows only ports + bus)
├── ports/                  # Protocol definitions (capabilities)
│   ├── narrator.py         # NarratorPort (respond, reset, get_history, seed_history)
│   ├── io.py               # InputPort, OutputPort
│   ├── rules.py            # RulesPort
│   ├── session.py          # SessionStore
│   └── stores.py           # ProfileStore
├── domain/                 # Game domain types
│   ├── profile.py          # PlayerProfile (versioned), Language, seed_prompt
│   ├── events.py           # TurnStarted, NarrationGenerated, TurnFinished
│   ├── rules.py            # RollResult
│   └── session.py          # Session (turn_index, history, timestamps)
├── cli/                    # CLI utilities
│   └── commands.py         # CommandHandler — /status /roll /save /reset /quit
├── events/                 # Internal pub/sub
│   ├── bus.py              # EventBus (sync, MRO-walking)
│   └── subscribers.py      # install_logging_subscriber
├── turn/                   # Turn-level processing (Phase 2.B)
│   └── classifier.py       # ActionClassifier — LLM call returning ActionIntent | None
└── adapters/               # Concrete implementations of ports
    ├── bridge_narrator.py  # NarratorPort — weaves check_result into narration
    ├── llm_evaluator.py    # PerformanceEvaluatorPort — LLM-as-judge for skill mode
    ├── noop_knowledge.py   # KnowledgePort — no-op (default when copper disabled)
    ├── copper_knowledge.py # KnowledgePort — HTTP client for copper /minds/{mind}/tap
    ├── local_dice.py       # RulesPort — SystemRandom (offline/test fallback)
    ├── mcp_rules.py        # RulesPort + RuleMetaProvider — MCPRulesAdapter (Phase 2.A)
    ├── automatic_challenge.py        # ChallengePort — no-op, falls back to dice
    ├── llm_evaluator_challenge.py    # ChallengePort — wraps LLMPerformanceEvaluator
    ├── math_quick_challenge.py       # ChallengePort — quick arithmetic minigame
    ├── color_naming_challenge.py     # ChallengePort — say-a-color minigame
    ├── json_session_store.py  # SessionStore — ~/.fante/session.json
    ├── stdio_io.py         # StdinInput, StdoutOutput
    ├── whisper_input.py    # InputPort — VAD recording + Whisper STT (Phase 3.3)
    ├── tts_output.py       # OutputPort — TTS synthesis + play via speech-io-hub (Phase 3.3)
    └── json_profile_store.py  # v1→v2 migration aware

challenge/                  # Phase 2.E
    ├── registry.py         # YAML loader for data/challenges/*.yaml
    ├── selector.py         # Picks minigame: category/attribute/age filter + topic bias + recent-N
    └── dispatcher.py       # Routes ChallengeSpec → concrete adapter

domain/
    ├── actor.py            # Actor, profile_to_actor
    ├── turn.py             # ActionIntent
    ├── rules.py            # RollResult, CheckResult, AppliedModifier, PlotDieFace
    ├── challenge.py        # RuleMeta, ChallengeSpec, ChallengeKind, ChallengeCategory
    └── events.py           # + ActionClassified, CheckResolved

data/
├── player_profile.json     # Fante's character sheet (schema_version 2)
├── copper_minds/           # Source content for copper knowledge minds
│   ├── adventure/raw/lore.md
│   ├── math/raw/curriculum.md
│   ├── languages/raw/vocab.md
│   └── lore/raw/world_lore.md
└── challenges/             # Minigame definitions (Phase 2.E)
    ├── math_quick.yaml
    ├── color_naming.yaml
    └── verbose_attempt.yaml

scripts/
└── setup_copper_minds.sh   # Bootstrap: forge + ingest the four copper minds

prompts/
├── narrator.yaml           # Externalised narrator prompt
├── classifier.yaml         # Classifier system prompt
└── evaluator.yaml          # Evaluator system prompt

docs/
├── project_briefing.md
├── IMPLEMENTATION_PLAN.md
├── USER_TESTS.md
└── core_llm_bridge_specs.md

tests/
├── conftest.py             # MockProvider, FakeNarrator/Input/Output/Session/Rules, make_game
├── test_event_bus.py       # unit
├── test_profile.py         # unit (incl. v1→v2 migration)
├── test_actor_translation.py  # unit
├── test_mcp_rules.py       # unit + integration (live server)
├── test_evaluator.py       # functional (MockProvider)
├── test_classifier.py      # functional (MockProvider)
├── test_turn_flow.py       # functional (full action pipeline)
├── test_manager.py         # functional
├── test_narrator.py        # functional (real BridgeNarrator, MockProvider)
├── test_dice.py            # unit
├── test_session_store.py   # unit + functional
├── test_commands.py        # functional (incl. /check)
├── test_dad_monitor.py     # unit
└── test_integration.py     # marker-gated, hits real Ollama
```

## Ports (the abstract surface)

| Port | Phase 1.0 adapter | Future adapters |
|---|---|---|
| `NarratorPort` | `BridgeNarrator` (core-llm-bridge) | swap to a different LLM stack |
| `InputPort` | `StdinInput` | `WhisperInput` (speech-io-hub) |
| `OutputPort` | `StdoutOutput` | `TTSOutput`, `GodotOutput` |
| `ProfileStore` | `JSONProfileStore` | `SqliteProfileStore` |
| `RulesPort` | `MCPRulesAdapter` (Phase 2.A) | `LocalDice` (offline/test fallback) |
| `SessionStore` | `JSONSessionStore` (`~/.fante/session.json`) | `SqliteSessionStore` |

Planned additions (when their first consumer arrives):
- `RulesPort` — Phase 1.5 (`LocalDice`), Phase 2 (`MCPRules` via mcp-game-rules repo)
- `SessionStore` — Phase 1.5
- `WorldPort` — Phase 4 (`GodotWS` via world-engine-godot repo)
- `KnowledgePort` — when needed (e.g. copperminds for lore / educational modules)

## Key classes

**`GameManager`** (`manager.py`) — depends only on ports + EventBus.
- `process_turn(user_input) -> str` — runs one turn, publishes `TurnStarted`/`NarrationGenerated`/`TurnFinished`
- `run()` — blocking REPL loop
- `reset()` — turn counter + narrator memory

**`BridgeNarrator`** (`adapters/bridge_narrator.py`) — `NarratorPort` backed by `BridgeEngine`.
- Builds the system prompt from the profile via the bridge's `PromptManager`
- Template hardcoded for Phase 1.0; YAML in Phase 1.5

**`PlayerProfile`** (`domain/profile.py`) — pydantic v2, versioned (`schema_version: int = 1`).
- `name`, `background`, `preferences`, `stats`, `language: Literal["es","en","mixed"]`

**`EventBus`** (`events/bus.py`) — sync pub/sub, MRO-aware (a `DomainEvent` subscriber sees all subclasses), failures in subscribers are logged and ignored.

## Main entry point

```bash
pdm install --dev          # first time
./scripts/start-stack.sh   # bring up copper (Docker) + speech-io-hub (native)
pdm run python -m fante    # play
./scripts/start-stack.sh stop   # tear the stack down
```

`start-stack.sh` orchestrates the service dependencies: copper runs in Docker,
speech-io-hub runs natively (so Whisper keeps Apple Silicon acceleration). Ollama
and the MCP rules server are not managed by it — Ollama runs separately, the rules
server is spawned by fante as a subprocess. Sub-commands: `start` (default),
`stop`, `restart`, `status`.

## Configuration

Inherits all bridge env vars (`OLLAMA_*`, `ANTHROPIC_*`, `OPENAI_*`, `LOG_*`).

| Env var | Default | Description |
|---|---|---|
| `OLLAMA_DEFAULT_MODEL` | `llama3.2:latest` | Narrator model |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama endpoint |
| `OLLAMA_TIMEOUT` | `300` | Seconds |
| `PLAYER_PROFILE_PATH` | `data/player_profile.json` | Profile JSON path |
| `MAX_HISTORY_LENGTH` | `30` | Messages retained before pruning |
| `LOG_LEVEL` | `INFO` | Bridge + orchestrator logs |
| `FANTE_COPPER_ENABLED` | `false` | Enable copper knowledge integration |
| `FANTE_COPPER_URL` | `http://127.0.0.1:8000` | Copper server base URL |
| `FANTE_COPPER_MIND_MAP` | `{adventure,math,languages,lore}` | JSON mapping topic→mind name |
| `FANTE_CHALLENGE_ENABLED` | `false` | Enable minigame system before checks |
| `FANTE_CHALLENGE_DEFINITIONS_PATH` | `data/challenges` | Directory of minigame YAMLs |
| `FANTE_CHALLENGE_OPTIONAL_PROB` | `0.5` | Activation probability for `challenge: optional` rules |
| `FANTE_CHALLENGE_TOPIC_BIAS` | `2.0` | Weight multiplier when session_topic matches |
| `FANTE_CHALLENGE_RECENT_HISTORY` | `3` | Sliding window of recent picks to exclude |
| `FANTE_JUKEBOX_ENABLED` | `true` | Enable jukebox mode (disabled automatically if music-hub unreachable) |
| `FANTE_MUSIC_HUB_URL` | `http://127.0.0.1:8600` | core-music-hub service base URL |
| `FANTE_JUKEBOX_INTENT_MODEL` | `""` | LLM model for jukebox classifier (empty → ollama_default_model) |
| `FANTE_AUDIO_ENABLED` | `false` | Enable voice mode (WhisperInput + TTSOutput) |
| `FANTE_SPEECH_URL` | `http://127.0.0.1:8500` | core-speech-io-hub service base URL |
| `FANTE_SPEECH_VOCABULARY_PATH` | `data/speech_vocabulary.yaml` | Whisper biasing vocabulary |
| `FANTE_TTS_VOICE` | `""` | TTS voice id (empty → server default) |

## Dependencies

- Runtime: `core-utils`, `core-llm-bridge`, `core-speech-io-hub`, `core-music-hub`, `pyyaml`
- Dev: pytest, pytest-cov, black, mypy, ruff, isort

## Testing

Three layers, all wired in `tests/conftest.py`:

| Layer | Marker | Speed | Scope |
|---|---|---|---|
| Unit | `unit` | <10ms | Pure logic (bus, profile model) |
| Functional | `functional` | <100ms | Real `GameManager` / `BridgeNarrator` with `MockProvider` and port-level fakes |
| Integration | `integration` | seconds | Real Ollama; gated, off by default |

Run:
```bash
./run_local_checks.sh        # black + mypy + functional + unit (fast)
pdm run pytest -m integration -v   # opt-in, requires Ollama running
```

## Phase status

- **Phase 1.0 ✓** — Walking skeleton: ports/adapters, EventBus, runnable terminal RPG, full test suite, integration test green against Ollama.
- **Phase 1.5 ✓** — Polish: externalised prompt YAML, `seed_prompt` opening scene, profiler hook, Dad's Monitor, `RulesPort`+`LocalDice`, `SessionStore`+`JSONSessionStore`, slash commands (`/status /roll /save /reset /quit`), `--reset` CLI flag. 55 tests pass.
- **Phase 2.A ✓** — `PlayerProfile` v2 (Cosmere attributes/skills/tags), `Actor` + `profile_to_actor`, `CheckResult`/`AppliedModifier`/`PlotDieFace` domain types, `MCPRulesAdapter` (persistent subprocess, sync facade), `/check` slash command, `FANTE_RULES_BACKEND` + `MCP_RULES_COMMAND` env vars, `mcp>=1.27` dep. 67 tests pass.
- **Phase 2.B ✓** — `ActionClassifier` + `LLMPerformanceEvaluator` + turn lifecycle (classify→eval→check→narrate), modo dice/skill (`/dice` `/skill`), `KnowledgePort` + `NoopKnowledgeAdapter` stub, `ActionClassified`/`CheckResolved` events. 82 tests pass.
- **Phase 2.C ✓** — `CopperKnowledgeAdapter` (HTTP client for copper `/minds/{mind}/tap`), `NarratorPort.respond` + `BridgeNarrator` extended with `knowledge` param, `GameManager` queries knowledge when topic is set, 4 copper minds (adventure/math/languages/lore) with sample content. `scripts/setup_copper_minds.sh` for bootstrapping.
- **Phase 2.D ✓** — Knowledge topic routing moved to rules engine (`CheckResult.knowledge_topic` from pack YAML) + session-level override (`--topic` CLI flag, `/topic` slash command, `GameManager.session_topic`). 87 tests pass.
- **Phase 2.E ✓** — Challenge / minigame system. New ports `RuleMetaProvider`, `ChallengeSelectorPort`, `ChallengePort`. `ChallengeRegistry` loads `data/challenges/*.yaml`; `ChallengeSelector` filters by category/attribute/age, applies session-topic bias and recent-N exclusion. `ChallengeDispatcher` routes by `adapter_id`. Adapters: `AutomaticChallenge`, `LLMEvaluatorChallenge`, `MathQuickChallenge`, `ColorNamingChallenge`. Requires engine `get_rule_meta` MCP tool (Phase 2.E.1 in `fante-mcp-game-rules`). 107 tests pass.
- **Phase 3.3 ✓** — Audio adapters: `WhisperInput` (VAD + Whisper via `core-speech-io-hub`) and `TTSOutput` (Piper/`say` TTS). `data/speech_vocabulary.yaml` loaded at startup for Whisper biasing. `FANTE_AUDIO_ENABLED` env var switches mode at startup (no live toggle). Text still echoed to stdout in audio mode for the parent. `core-speech-io-hub` git dep added. 117 tests pass.
- **Phase 3.4 ✓** — Jukebox mode. New `"jukebox"` mode in `GameManager.Mode`; `JukeboxIntentClassifier` (LLM, parses play/stop/next/list/exit); `JukeboxHandler` (delegates to `MusicHubClient`); `/jukebox` + `/aventura` slash commands; graceful fallback if `core-music-hub` is unreachable. `core-music-hub` git dep added. 130 tests pass.
- **Phase 3.5** — Character progression: XP, level, level-based check influences. Updates `PlayerProfile` schema.
- **Phase 3.6** — Challenge system depth (tracked via `TD-CH-*` items folded in below):
    - **3.6.1** Cooldown by category (extend recent-history to track categories, not just IDs).
    - **3.6.2** Adaptive difficulty (tune `max_operand`, `time_limit` based on per-player success history; requires a success-stats store).
    - **3.6.3** Minigame DSL (declarative authoring in YAML for common patterns: Q&A, parametric math, multi-question, LLM-judged, choice; no Python adapter required for these kinds).
    - **3.6.4** Multi-turn challenges (cross-turn state; e.g. "say your name across three turns"). Builds on the DSL.
- **Phase 4** — `world-engine-godot` repo → WebSocket `WorldPort`. Sibling repo.
- **Future** — Multi-character / multi-session support (today the system assumes a single `player_profile.json` and one `session.json`). Telemetry-grade persistence for post-session analysis. Not on the active roadmap.

## Consumers / upstream

- **Uses:** `core-llm-bridge` (LLM narration), `core-utils` (settings, logging), `core-music-hub` (jukebox playback)
- **Used by:** nothing — this is the top-level application

## Notes
- Architecture is intentionally generic; the `fante` package name is the project label,
  not a domain coupling. Class names are neutral (`GameManager`, `NarratorAgent`, …).
- Single-machine assumption: localhost services, JSON files, no auth.
- Deferred decisions / known debt tracked in [TECH_DEBT.md](TECH_DEBT.md).
