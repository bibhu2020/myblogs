"""Publish curated news items to the Meridian platform."""
import os
import time

import jwt
import requests

_SECRET = "myblogs-secret-key-2024"
_BASE = os.getenv("SERVER_BASE", "http://localhost:3000")


def _make_agent_jwt() -> str:
    payload = {
        "sub": 0,
        "email": "agent@meridian.internal",
        "role": "admin",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, _SECRET, algorithm="HS256")


def save_news_items(items: list[dict]) -> dict:
    """POST /api/news/refresh — replaces all existing news with fresh items."""
    token = _make_agent_jwt()
    resp = requests.post(
        f"{_BASE}/api/news/refresh",
        json={"items": items},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
