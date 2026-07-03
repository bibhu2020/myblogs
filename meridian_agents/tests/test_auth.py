import base64
import json

from meridian_agents.auth import make_agent_jwt


def _decode_part(part: str) -> dict:
    padding = "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part + padding))


def test_produces_a_three_part_jwt():
    token = make_agent_jwt()
    parts = token.split(".")
    assert len(parts) == 3


def test_header_declares_hs256():
    token = make_agent_jwt()
    header = _decode_part(token.split(".")[0])
    assert header == {"alg": "HS256", "typ": "JWT"}


def test_payload_uses_defaults_and_admin_role():
    token = make_agent_jwt()
    payload = _decode_part(token.split(".")[1])
    assert payload["name"] == "AI Agent"
    assert payload["email"] == "ai-agent@meridian.internal"
    assert payload["role"] == "admin"
    assert payload["sub"] == 0
    assert payload["exp"] == payload["iat"] + 3600


def test_payload_reflects_custom_name_and_email():
    token = make_agent_jwt(name="Custom Agent", email="custom@meridian.internal")
    payload = _decode_part(token.split(".")[1])
    assert payload["name"] == "Custom Agent"
    assert payload["email"] == "custom@meridian.internal"


def test_signature_changes_when_secret_changes(monkeypatch):
    token_a = make_agent_jwt()
    monkeypatch.setenv("JWT_SECRET", "a-different-secret")
    token_b = make_agent_jwt()
    assert token_a.split(".")[2] != token_b.split(".")[2]
    # header/payload structure is identical, only the signature differs
    assert token_a.split(".")[0] == token_b.split(".")[0]
