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
├── compose.py              # Composition root: wires adapters → ports → GameManager
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
└── adapters/               # Concrete implementations of ports
    ├── bridge_narrator.py  # NarratorPort via core-llm-bridge BridgeEngine
    ├── local_dice.py       # RulesPort — SystemRandom, parses XdY±Z
    ├── json_session_store.py  # SessionStore — ~/.fante/session.json
    ├── stdio_io.py         # StdinInput, StdoutOutput
    └── json_profile_store.py

data/
└── player_profile.json     # Fante's character sheet

prompts/
└── narrator.yaml           # Externalised narrator prompt (fallback to inline)

docs/
├── project_briefing.md
├── IMPLEMENTATION_PLAN.md
├── USER_TESTS.md
└── core_llm_bridge_specs.md

tests/
├── conftest.py             # MockProvider, FakeNarrator/Input/Output/Session, make_game
├── test_event_bus.py       # unit
├── test_profile.py         # unit
├── test_manager.py         # functional
├── test_narrator.py        # functional (real BridgeNarrator, MockProvider)
├── test_dice.py            # unit
├── test_session_store.py   # unit + functional
├── test_commands.py        # functional
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
| `RulesPort` | `LocalDice` | `MCPRulesAdapter` (Phase 2) |
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
pdm run python -m fante    # play
```

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

## Dependencies

- Runtime: `core-utils`, `core-llm-bridge`, `pyyaml`
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
- **Phase 2** — `mcp-game-rules` repo (created manually) → `MCPRulesAdapter`. Possibly `KnowledgePort` + `CopperKnowledgeAdapter` for richer lore / educational modules.
- **Phase 3** — `speech-io-hub` repo → Whisper input + TTS output. Async at the orchestrator seam.
- **Phase 4** — `world-engine-godot` repo → WebSocket `WorldPort`.

## Consumers / upstream

- **Uses:** `core-llm-bridge` (LLM narration), `core-utils` (settings, logging)
- **Used by:** nothing — this is the top-level application

## Notes
- Architecture is intentionally generic; the `fante` package name is the project label,
  not a domain coupling. Class names are neutral (`GameManager`, `NarratorAgent`, …).
- Single-machine assumption: localhost services, JSON files, no auth.
