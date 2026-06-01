#!/usr/bin/env bash
# start-stack.sh — bring the Fante service stack up or down with one command.
#
# Manages three background services:
#   - copper         → Docker  (knowledge backend, port 8000)
#   - speech-io-hub  → native  (STT/TTS, port 8500) — kept native so Whisper
#                               keeps Apple Silicon (Metal) acceleration
#   - core-music-hub → native  (jukebox + scoring, port 8600)
#
# NOT managed here (run/spawned separately):
#   - Ollama          → system service; this script only checks reachability
#   - mcp-game-rules  → fante spawns it as a subprocess on its own
#
# Usage:
#   ./scripts/start-stack.sh [start]   # bring everything up (default)
#   ./scripts/start-stack.sh stop      # bring everything down
#   ./scripts/start-stack.sh restart   # stop + start
#   ./scripts/start-stack.sh status    # show what's running
#
# Sibling repos are expected at ../copper, ../core-speech-io-hub and
# ../core-music-hub. Override with COPPER_DIR / SPEECH_DIR / MUSIC_DIR env
# vars if elsewhere.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECTS_DIR="$(cd "$REPO_ROOT/.." && pwd)"

COPPER_DIR="${COPPER_DIR:-$PROJECTS_DIR/copper}"
SPEECH_DIR="${SPEECH_DIR:-$PROJECTS_DIR/core-speech-io-hub}"
MUSIC_DIR="${MUSIC_DIR:-$PROJECTS_DIR/core-music-hub}"

COPPER_URL="${COPPER_URL:-http://127.0.0.1:8000}"
SPEECH_URL="${SPEECH_URL:-http://127.0.0.1:8500}"
MUSIC_URL="${MUSIC_URL:-http://127.0.0.1:8600}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"

SPEECH_PIDFILE="/tmp/fante-speech-io-hub.pid"
SPEECH_LOG="/tmp/fante-speech-io-hub.log"
MUSIC_PIDFILE="/tmp/fante-music-hub.pid"
MUSIC_LOG="/tmp/fante-music-hub.log"

# ---------- helpers --------------------------------------------------------

_speech_running() {
  [ -f "$SPEECH_PIDFILE" ] && kill -0 "$(cat "$SPEECH_PIDFILE")" 2>/dev/null
}

_music_running() {
  [ -f "$MUSIC_PIDFILE" ] && kill -0 "$(cat "$MUSIC_PIDFILE")" 2>/dev/null
}

_wait_for() {
  # _wait_for <url> <label> <timeout_s>
  local url="$1" label="$2" timeout="${3:-30}" elapsed=0
  while ! curl -sf "$url" >/dev/null 2>&1; do
    sleep 1
    elapsed=$((elapsed + 1))
    if [ "$elapsed" -ge "$timeout" ]; then
      echo "  ✗ $label did not become ready within ${timeout}s"
      return 1
    fi
  done
  echo "  ✓ $label ready"
}

# ---------- start ----------------------------------------------------------

start() {
  [ -d "$COPPER_DIR" ] || { echo "Error: copper repo not found at $COPPER_DIR"; exit 1; }
  [ -d "$SPEECH_DIR" ] || { echo "Error: speech-io-hub repo not found at $SPEECH_DIR"; exit 1; }
  [ -d "$MUSIC_DIR" ]  || { echo "Error: core-music-hub repo not found at $MUSIC_DIR"; exit 1; }

  echo "→ Starting copper (Docker)..."
  (cd "$COPPER_DIR" && docker compose up -d)
  _wait_for "$COPPER_URL/minds" "copper" 120 || true

  echo "→ Starting speech-io-hub (native)..."
  if _speech_running; then
    echo "  (already running, pid $(cat "$SPEECH_PIDFILE") — use 'restart' to force a fresh launch)"
  else
    (
      cd "$SPEECH_DIR"
      nohup pdm run python -m speech_io_hub > "$SPEECH_LOG" 2>&1 &
      echo $! > "$SPEECH_PIDFILE"
    )
    # 300s timeout to accommodate first-time Whisper model downloads (especially
    # turbo / large-v3, which are 800MB-1.5GB and take minutes on first start).
    # After the first run the model is cached and startup is sub-10s.
    _wait_for "$SPEECH_URL/health" "speech-io-hub" 300 || {
      echo "  speech-io-hub log tail:"
      tail -n 15 "$SPEECH_LOG" | sed 's/^/    /'
    }
  fi
  # /health exists in every version — verify the running server actually
  # exposes the STT+TTS routes, otherwise it's a stale build (missing 3.2).
  # This check runs whether we launched the server or found it already alive.
  _routes="$(curl -sf "$SPEECH_URL/openapi.json" 2>/dev/null \
    | python3 -c 'import sys,json; print(" ".join(json.load(sys.stdin)["paths"]))' 2>/dev/null || true)"
  for route in /transcribe /synthesize; do
    case " $_routes " in
      *" $route "*) ;;
      *) echo "  ⚠ speech-io-hub is missing $route — running a stale build?" ;;
    esac
  done

  echo "→ Starting core-music-hub (native)..."
  if _music_running; then
    echo "  (already running, pid $(cat "$MUSIC_PIDFILE") — use 'restart' to force a fresh launch)"
  else
    (
      cd "$MUSIC_DIR"
      nohup pdm run python -m core_music_hub > "$MUSIC_LOG" 2>&1 &
      echo $! > "$MUSIC_PIDFILE"
    )
    _wait_for "$MUSIC_URL/health" "core-music-hub" 30 || {
      echo "  core-music-hub log tail:"
      tail -n 15 "$MUSIC_LOG" | sed 's/^/    /'
    }
  fi

  echo "→ Checking Ollama..."
  if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
    echo "  ✓ Ollama reachable"
  else
    echo "  ⚠ Ollama not reachable at $OLLAMA_URL — start it before running fante"
  fi

  echo ""
  echo "Stack up. speech-io-hub log: $SPEECH_LOG"
  echo "Play with:  pdm run python -m fante"
}

# ---------- stop -----------------------------------------------------------

stop() {
  echo "→ Stopping core-music-hub..."
  if _music_running; then
    kill "$(cat "$MUSIC_PIDFILE")" 2>/dev/null || true
  fi
  pkill -f "python -m core_music_hub" 2>/dev/null || true
  rm -f "$MUSIC_PIDFILE"
  echo "  ✓ stopped"

  echo "→ Stopping speech-io-hub..."
  if _speech_running; then
    kill "$(cat "$SPEECH_PIDFILE")" 2>/dev/null || true
  fi
  # Catch the uvicorn child pdm may have spawned under its own PID.
  pkill -f "python -m speech_io_hub" 2>/dev/null || true
  rm -f "$SPEECH_PIDFILE"
  echo "  ✓ stopped"

  echo "→ Stopping copper (Docker)..."
  if [ -d "$COPPER_DIR" ]; then
    (cd "$COPPER_DIR" && docker compose down)
    echo "  ✓ stopped"
  else
    echo "  (copper repo not found, skipping)"
  fi
}

# ---------- status ---------------------------------------------------------

_probe() {
  curl -sf "$1" >/dev/null 2>&1 && echo "up" || echo "down"
}

status() {
  echo "copper:         $(_probe "$COPPER_URL/minds")"
  echo "speech-io-hub:  $(_probe "$SPEECH_URL/health")"
  echo "core-music-hub: $(_probe "$MUSIC_URL/health")"
  echo "ollama:         $(_probe "$OLLAMA_URL/api/tags")"
}

# ---------- dispatch -------------------------------------------------------

case "${1:-start}" in
  start)   start ;;
  stop)    stop ;;
  restart) stop; echo; start ;;
  status)  status ;;
  *)       echo "Usage: $0 [start|stop|restart|status]"; exit 1 ;;
esac
