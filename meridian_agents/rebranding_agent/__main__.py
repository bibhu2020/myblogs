"""Entry point: python -m meridian_agents.rebranding_agent"""
import sys
from .main import run_rebranding

try:
    run_rebranding()
except Exception as e:
    print(f"\nRebranding agent failed: {e}", file=sys.stderr)
    sys.exit(1)
