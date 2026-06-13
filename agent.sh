#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Load .env from project root into the environment
if [ -f "$ROOT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

usage() {
  cat <<'USAGE'
Meridian Post Agent  (LangGraph / Python edition)

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
  MCP_URL            MCP endpoint (default: https://mishrabP-myblogs.hf.space/api/mcp)
  SERVER_BASE        Media upload base URL (default: https://mishrabP-myblogs.hf.space)
  TOPIC_MODE         Category hint: ai_trending | random_general | AI | Technology | Science |
                       History | Travel | Knowledge  (default: random)
  AGENT_AUTHOR_EMAIL Guest author email (default: ai.researcher@meridian.blog)
  AGENT_AUTHOR_NAME  Guest author display name (default: Meridian AI Researcher)
  AGENT_AUTHOR_PASSWORD  Guest author password (auto-generated if omitted)
  JWT_SECRET         Override JWT signing secret (default: myblogs-secret-key-2024)
  HF_TOKEN           Hugging Face token (for FLUX.1-schnell image fallback)
  GEMINI_API_KEY     Google Gemini key (for Gemini image fallback)
  UNSPLASH_ACCESS_KEY  Unsplash key (for stock photo fallback / Travel category)
USAGE
  exit 1
}

if [ $# -eq 0 ]; then usage; fi

# Ensure Python deps are installed
if ! python3 -c "import langgraph, openai, croniter" 2>/dev/null; then
  echo "📦 Installing Python post_agent dependencies..."
  pip3 install --user -e "$ROOT_DIR[post_agent]" --quiet
  echo "✅ Dependencies installed"
  echo ""
fi

case "$1" in
  run)
    cd "$ROOT_DIR"
    python3 -m post_agent
    ;;
  schedule)
    if [ -z "${2:-}" ]; then
      echo "❌ Error: 'schedule' requires a cron expression"
      echo ""
      usage
    fi
    cd "$ROOT_DIR"
    python3 -m post_agent schedule "$2"
    ;;
  *)
    echo "❌ Unknown command: $1"
    echo ""
    usage
    ;;
esac
