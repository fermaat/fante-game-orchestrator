🐘 Especificación Técnica: fante-game-orchestrator
1. Propósito
fante-game-orchestrator es el punto de entrada único del sistema. Su misión es gestionar el bucle de juego (Game Loop), coordinar la entrada de voz/texto, consultar las reglas de rol y enviar la salida tanto al motor gráfico como al sistema de voz.

Es el "pegamento" que une:

Entrada: speech-io-hub (Whisper).

Cerebro: core-llm-bridge (Llama 3.x via Ollama).

Reglas: mcp-game-rules (Tiradas de dados/Stats).

Salida: world-engine-godot (Visual) y speech-io-hub (TTS).

2. Estructura del Repositorio (Basado en PDM)
Plaintext
fante-game-orchestrator/
├── pyproject.toml
├── .env                     # Claves de API, URLs de Ollama, etc.
├── data/
│   └── player_profile.json  # Ficha de "Fante" (tu hijo)
├── src/
│   └── fante/
│       ├── __init__.py
│       ├── main.py          # Punto de entrada (CLI inicial)
│       ├── manager.py       # El Orquestador central
│       ├── agents/
│       │   └── narrator.py  # Lógica específica del narrador
│       └── connectors/
│           ├── godot.py     # Cliente WebSocket para Godot
│           └── speech.py    # Cliente para el Hub de voz
└── tests/
3. Flujo de Orquestación (The Walking Skeleton)
El funcionamiento seguirá este ciclo de eventos:

Captura: El orquestador recibe texto (o audio transcrito).

Contextualización: Lee el player_profile.json (ej: "Le gustan los elefantes").

Inferencia: Envía el contexto + el input a core-llm-bridge.

Acción (MCP): Si el LLM decide una acción (ej: "Intentas saltar"), el orquestador llama al módulo de reglas.

Difusión: - Envía el texto resultante al TTS.

Envía el comando visual (ej: {"anim": "jump"}) a Godot.

4. Iteración Mínima (MVP - "The Elephant Step")
Para que funcione ASAP, vamos a ignorar Godot y el Audio en la primera versión. El MVP será un RPG de terminal:

Entrada: input() de Python.

Procesamiento: core-llm-bridge con un modelo ligero (Llama 3.2 3B).

Reglas: Una función interna simple roll_dice() (sin MCP todavía).

Salida: print() en consola.

Objetivo del MVP: Confirmar que el BridgeEngine mantiene la memoria del elefante "Fante" durante al menos 5 minutos de charla.

5. Ideas Extra para el "Vibe Coding"
fante-cli: Podrías crear un pequeño comando de terminal para lanzar el juego rápido.

Modo "Papá Monitor": Una pequeña ventana de log donde tú veas en tiempo real qué "pensamientos internos" (Chain of Thought) está teniendo el modelo antes de responderle a tu hijo.

Safety Filter: Una lista de palabras prohibidas o temas (ej: "monstruos dar miedo") que el orquestador filtre antes de enviar el prompt al bridge.