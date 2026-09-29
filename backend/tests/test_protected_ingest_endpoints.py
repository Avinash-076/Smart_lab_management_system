"""
Backend tests for Protected Ingest Endpoints (J-05 / Stage 4).
Verifies authentication enforcement across telemetry routes:
- /api/metrics
- /api/software
- /api/processes
- /api/issues
- /api/usage

Verifies:
- Missing Authorization header
- Invalid/Malformed Bearer token
- Expired token
- Wrong token type (user token instead of agent token)
- Inactive/revoked agent credential
- Computer ID mismatch in token
"""

from datetime import datetime, timedelta, timezone
import pytest
from jose import jwt

from app.auth import create_agent_access_token
from app.config import settings
from app.models.agent_credential import AgentCredential
from app.models.computer import Computer

INGEST_ENDPOINTS = [
    ("/api/metrics", {"cpu_usage": 10.0, "ram_usage": 20.0, "disk_usage": 30.0}),
    ("/api/software", {"software": [{"name": "Python", "version": "3.13"}]}),
    ("/api/processes", {"processes": [{"pid": 100, "name": "app.exe", "user": None}]}),
    ("/api/issues/agent", {"title": "High RAM", "description": "RAM exceeded 95%", "severity": "medium"}),
    ("/api/usage", {"sessions": [{"application_name": "Code", "start_time": "2026-09-28T10:00:00Z", "duration_seconds": 60}]}),
]


@pytest.mark.parametrize("endpoint,payload", INGEST_ENDPOINTS)
def test_ingest_endpoint_missing_token_rejected(client, endpoint, payload):
    """Verify posting to telemetry ingest endpoint without Authorization header is rejected."""
    response = client.post(endpoint, json=payload)
    # HTTPBearer returns 401 or 403 when header is absent
    assert response.status_code in (401, 403)


@pytest.mark.parametrize("endpoint,payload", INGEST_ENDPOINTS)
def test_ingest_endpoint_invalid_token_rejected(client, endpoint, payload):
    """Verify posting with an invalid or malformed Bearer token returns 401."""
    headers = {"Authorization": "Bearer invalid.malformed.jwt.token"}
    response = client.post(endpoint, json=payload, headers=headers)
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


@pytest.mark.parametrize("endpoint,payload", INGEST_ENDPOINTS)
def test_ingest_endpoint_expired_token_rejected(client, endpoint, payload):
    """Verify posting with an expired agent token returns 401."""
    expired_claim = {
        "sub": "AGT_EXPIRED",
        "computer_id": 9999,
        "type": "agent",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_claim, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    headers = {"Authorization": f"Bearer {expired_token}"}

    response = client.post(endpoint, json=payload, headers=headers)
    assert response.status_code == 401
    assert "Invalid or expired token" in response.json()["detail"]


@pytest.mark.parametrize("endpoint,payload", INGEST_ENDPOINTS)
def test_ingest_endpoint_wrong_token_type_rejected(client, endpoint, payload):
    """Verify user access token (type='access') cannot be used for agent ingest endpoints."""
    user_claim = {
        "sub": "1",  # user_id
        "type": "access",  # Not "agent"
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    user_token = jwt.encode(user_claim, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    headers = {"Authorization": f"Bearer {user_token}"}

    response = client.post(endpoint, json=payload, headers=headers)
    assert response.status_code == 401
    assert "Invalid token type" in response.json()["detail"]


@pytest.mark.parametrize("endpoint,payload", INGEST_ENDPOINTS)
def test_ingest_endpoint_computer_id_mismatch_rejected(client, db_session, registered_agent, endpoint, payload):
    """Verify agent token whose computer_id does not match database record is rejected."""
    mismatched_token = create_agent_access_token({
        "sub": registered_agent["agent_id"],
        "computer_id": 999999,  # Mismatched computer_id
    })
    headers = {"Authorization": f"Bearer {mismatched_token}"}

    response = client.post(endpoint, json=payload, headers=headers)
    assert response.status_code == 401
    assert "mismatch" in response.json()["detail"].lower()


@pytest.mark.parametrize("endpoint,payload", INGEST_ENDPOINTS)
def test_ingest_endpoint_inactive_agent_rejected(client, db_session, registered_agent, endpoint, payload):
    """Verify disabled or deactivated agent credentials cannot upload telemetry."""
    cred = db_session.query(AgentCredential).filter_by(agent_id=registered_agent["agent_id"]).first()
    cred.is_active = False
    db_session.commit()

    try:
        headers = {"Authorization": f"Bearer {registered_agent['token']}"}
        response = client.post(endpoint, json=payload, headers=headers)
        assert response.status_code == 401
        assert "revoked" in response.json()["detail"].lower()
    finally:
        # Restore active status for registered_agent fixture cleanup
        cred.is_active = True
        db_session.commit()
