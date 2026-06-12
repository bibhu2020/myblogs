#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$ROOT_DIR/agent"

# Load .env from project root into the environment
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

usage() {
  cat <<'USAGE'
Meridian AI Blog Agent

Usage:
  ./agent.sh run                     Run the agent once now
  ./agent.sh schedule <cron-expr>    Run on a recurring cron schedule (UTC)

Examples:
  ./agent.sh run
  ./agent.sh schedule '0 8 * * 1'       # Every Monday at 8am UTC
  ./agent.sh schedule '0 8 * * 1,4'     # Monday and Thursday at 8am UTC
  ./agent.sh schedule '0 0 * * *'       # Daily at midnight UTC

Required (set in .env or export):
  OPENAI_API_KEY     OpenAI API key (must have DALL-E 3 + GPT-4o access)
  MCP_API_KEY        Meridian MCP server key

Optional overrides:
  MCP_URL            MCP endpoint (default: https://mishrabp-myblogs.hf.space/api/mcp)
  SERVER_BASE        Media upload base URL (default: https://mishrabp-myblogs.hf.space)
  AGENT_AUTHOR_EMAIL Guest author email (default: ai.researcher@meridian.blog)
  AGENT_AUTHOR_NAME  Guest author display name (default: Meridian AI Researcher)
  AGENT_AUTHOR_PASSWORD  Guest author password (auto-generated if omitted)
  JWT_SECRET         Override JWT signing secret (default: myblogs-secret-key-2024)
USAGE
  exit 1
}

if [ $# -eq 0 ]; then usage; fi

# Install agent dependencies if needed
if [ ! -d "$AGENT_DIR/node_modules" ]; then
  echo "📦 Installing agent dependencies..."
  npm --prefix "$AGENT_DIR" install --silent
  echo "✅ Dependencies installed"
  echo ""
fi

case "$1" in
  run)
    node "$AGENT_DIR/index.js"
    ;;
  schedule)
    if [ -z "${2:-}" ]; then
      echo "❌ Error: 'schedule' requires a cron expression"
      echo ""
      usage
    fi
    export CRON_SCHEDULE="$2"
    node "$AGENT_DIR/schedule.js"
    ;;
  *)
    echo "❌ Unknown command: $1"
    echo ""
    usage
    ;;
esac
