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
Meridian Maintenance Agent  (AutoGen / Python edition)

Usage:
  ./maintenance.sh run                     Run the agent once now
  ./maintenance.sh schedule <cron-expr>    Run on a recurring cron schedule (UTC)

Examples:
  ./maintenance.sh run
  ./maintenance.sh schedule '0 0 1 * *'       # 1st of each month at midnight UTC
  ./maintenance.sh schedule '0 0 * * 0'       # Every Sunday at midnight UTC
  ./maintenance.sh schedule '0 6 * * 1'       # Every Monday at 6am UTC

Required (set in .env or export):
  OPENAI_API_KEY     OpenAI API key (must have GPT-5 access)

Optional:
  MAINTENANCE_MODEL  Model to use (default: gpt-5)
  SERVER_BASE        Meridian API base URL (default: https://mishrabP-myblogs.hf.space)
  SECRET_TOKEN_GITHUB  GitHub personal access token (for Dependabot PR analysis)
  GITHUB_REPO        GitHub repo in owner/repo format (e.g. bibhu2020/myblogs)
USAGE
  exit 1
}

if [ $# -eq 0 ]; then usage; fi

# Ensure Python deps are installed
if ! python3 -c "import autogen_agentchat, croniter" 2>/dev/null; then
  echo "Installing Python maintenance_agent dependencies..."
  pip3 install --user -e "$ROOT_DIR[maintenance]" --quiet
  echo "Dependencies installed"
  echo ""
fi

case "$1" in
  run)
    cd "$ROOT_DIR"
    python3 -m agents.maintenance_agent
    ;;
  schedule)
    if [ -z "${2:-}" ]; then
      echo "Error: 'schedule' requires a cron expression"
      echo ""
      usage
    fi
    cd "$ROOT_DIR"
    python3 -m agents.maintenance_agent schedule "$2"
    ;;
  *)
    echo "Unknown command: $1"
    echo ""
    usage
    ;;
esac
