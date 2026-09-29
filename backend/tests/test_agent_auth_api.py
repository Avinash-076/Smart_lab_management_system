"""
Backend tests for Agent REST Authentication API (J-05).
Covers POST /api/agent/auth:
- Valid credentials return JWT access token and expires_in (200)
- Invalid client secret rejected (401)
- Unknown agent_id rejected (401)
- Inactive/disabled agent rejected (401)
- Token payload verification (type='agent', sub=agent_id, computer_id)
- Malformed request payload rejected (422)
"""

import pytest
from app.auth import decode_token, hash_secret
from app.models.agent_credential import AgentCredential
from app.models.computer import Computer


@pytest.fixture
def agent_with_known_secret(db_session):
    """Seed a computer and agent credential with a known client secret."""
    import uuid
    suffix = uuid.uuid4().hex[:6]
    mac = ":".join(f"{(uuid.uuid4().int >> (8 * i)) & 0xff:02x}" for i in range(6))

    computer = Computer(
        hostname=f"AUTH-PC-{suffix}",
        ip_address="192.168.1.150",
        mac_address=mac,
        os_name="Windows",
        os_version="11 Pro",
    )
    db_session.add(computer)
    db_session.commit()
    db_session.refresh(computer)

    secret = "known-super-secret-key-12345678"
    credential = AgentCredential(
        agent_id=f"AGT_{suffix}",
        secret_hash=hash_secret(secret),
        computer_id=computer.id,
        is_active=True,
    )
    db_session.add(credential)
    db_session.commit()
    db_session.refresh(credential)

    return {
        "computer_id": computer.id,
        "agent_id": credential.agent_id,
        "client_secret": secret,
        "credential": credential,
    }


def test_agent_auth_success(client, agent_with_known_secret):
    """Verify valid agent_id + client_secret returns 200 with JWT access_token."""
    payload = {
        "agent_id": agent_with_known_secret["agent_id"],
        "client_secret": agent_with_known_secret["client_secret"],
    }
    response = client.post("/api/agent/auth", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["expires_in"] == 900  # 15 minutes

    # Decode and verify JWT claims
    claims = decode_token(data["access_token"])
    assert claims["type"] == "agent"
    assert claims["sub"] == agent_with_known_secret["agent_id"]
    assert claims["computer_id"] == agent_with_known_secret["computer_id"]


def test_agent_auth_invalid_secret_rejected(client, agent_with_known_secret):
    """Verify incorrect client_secret returns 401 Unauthorized."""
    payload = {
        "agent_id": agent_with_known_secret["agent_id"],
        "client_secret": "WRONG_SECRET_VALUE",
    }
    response = client.post("/api/agent/auth", json=payload)
    assert response.status_code == 401
    assert "Invalid or revoked credential" in response.json()["detail"]


def test_agent_auth_unknown_agent_rejected(client):
    """Verify non-existent agent_id returns 401 Unauthorized."""
    payload = {
        "agent_id": "AGT_DOES_NOT_EXIST",
        "client_secret": "some_random_secret",
    }
    response = client.post("/api/agent/auth", json=payload)
    assert response.status_code == 401
    assert "Invalid or revoked credential" in response.json()["detail"]


def test_agent_auth_inactive_agent_rejected(client, db_session, agent_with_known_secret):
    """Verify disabled/revoked agent credential returns 401 Unauthorized."""
    cred = agent_with_known_secret["credential"]
    cred.is_active = False
    db_session.commit()

    payload = {
        "agent_id": agent_with_known_secret["agent_id"],
        "client_secret": agent_with_known_secret["client_secret"],
    }
    response = client.post("/api/agent/auth", json=payload)
    assert response.status_code == 401
    assert "Invalid or revoked credential" in response.json()["detail"]


def test_agent_auth_malformed_payload(client):
    """Verify missing required fields in request returns 422 Unprocessable Entity."""
    payload = {"agent_id": "AGT_INCOMPLETE"}
    response = client.post("/api/agent/auth", json=payload)
    assert response.status_code == 422
