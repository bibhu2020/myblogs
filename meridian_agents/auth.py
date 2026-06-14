"""Shared JWT helper for all Meridian agents that call the platform API."""
import base64
import hashlib
import hmac
import json
import os
import time


def make_agent_jwt(name: str = "AI Agent", email: str = "ai-agent@meridian.internal") -> str:
    """Create a short-lived HS256 admin JWT accepted by all Meridian services."""
    secret = os.getenv("JWT_SECRET", "myblogs-secret-key-2024").encode()
    now = int(time.time())

    def b64url(obj: dict) -> str:
        return (
            base64.urlsafe_b64encode(json.dumps(obj, separators=(",", ":")).encode())
            .rstrip(b"=")
            .decode()
        )

    header = b64url({"alg": "HS256", "typ": "JWT"})
    payload = b64url({
        "sub": 0, "id": 0,
        "email": email,
        "name": name,
        "role": "admin",
        "iat": now,
        "exp": now + 3600,
    })
    signing_input = f"{header}.{payload}".encode()
    sig = (
        base64.urlsafe_b64encode(
            hmac.new(secret, signing_input, hashlib.sha256).digest()
        )
        .rstrip(b"=")
        .decode()
    )
    return f"{header}.{payload}.{sig}"
