#!/usr/bin/env bash
# Bootstrap the four copper minds used by fante.
# Run once after cloning, with copper running.
#
# Reads FANTE_COPPER_URL from .env / .env.local (same var as the Python config).
# Override at call time if needed:
#   FANTE_COPPER_URL=http://other-host:8000 ./scripts/setup_copper_minds.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Source .env files to pick up FANTE_COPPER_URL (gitignored, never committed).
for env_file in "$REPO_ROOT/.env" "$REPO_ROOT/.env.local"; do
  if [ -f "$env_file" ]; then
    set -o allexport
    # shellcheck source=/dev/null
    source "$env_file"
    set +o allexport
  fi
done

if [ -z "${FANTE_COPPER_URL:-}" ]; then
  echo "Error: FANTE_COPPER_URL is not set."
  echo "Add it to .env or pass it inline: FANTE_COPPER_URL=http://... ./scripts/setup_copper_minds.sh"
  exit 1
fi

COPPER_URL="$FANTE_COPPER_URL"
MINDS_DIR="$REPO_ROOT/data/copper_minds"

topic_for() {
  case "$1" in
    adventure) echo "adventure actions and climbing techniques for role-playing games" ;;
    math)      echo "math educational content for role-playing games" ;;
    languages) echo "language learning content for role-playing games" ;;
    lore)      echo "world lore and setting for role-playing games" ;;
  esac
}

for mind in adventure math languages lore; do
  topic="$(topic_for "$mind")"
  echo "→ Forging mind: $mind"
  curl -sf -X POST "$COPPER_URL/minds" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$mind\", \"topic\": \"$topic\", \"model\": \"default\"}" \
    > /dev/null \
    || echo "  (already exists, skipping forge)"

  # Note: per-mind `tap_personality` is intentionally NOT set here. Fante passes
  # `personality: "tap.<topic>"` explicitly in every /tap request, which takes
  # precedence over the mind's config. Avoiding the file edit also makes this
  # script work with copper in Docker (where minds live in a volume the host
  # can't easily reach).

  for raw_file in "$MINDS_DIR/$mind/raw/"*.md; do
    [ -f "$raw_file" ] || continue
    echo "  Ingesting: $(basename "$raw_file")"
    curl -sf -X POST "$COPPER_URL/minds/$mind/store" \
      -F "file=@$raw_file" \
      > /dev/null
  done
done

echo ""
echo "Done. Minds available: adventure, math, languages, lore"
