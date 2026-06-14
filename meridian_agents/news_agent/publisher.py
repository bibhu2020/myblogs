"""Publish curated news items to the Meridian platform."""
import os

import requests

from ..auth import make_agent_jwt

_BASE = os.getenv("SERVER_BASE", "http://localhost:3000")


def save_news_items(items: list[dict]) -> dict:
    """POST /api/news/refresh — replaces all existing news with fresh items."""
    token = make_agent_jwt(name="News Agent", email="news-agent@meridian.internal")
    resp = requests.post(
        f"{_BASE}/api/news/refresh",
        json={"items": items},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
