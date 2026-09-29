"""
Backend tests for Agent Enrollment API (J-04).
Covers POST /api/agent/register:
- Valid enrollment with valid key
- Invalid enrollment key (401)
- Expired enrollment key (401)
- Already-consumed single-use key (401)
- Hostname conflict (409)
- MAC address conflict (409)
- Validation errors / malformed payload (422)
"""

from datetime import datetime, timedelta, timezone
import pytest
from app.models.computer import Computer
from app.models.enrollment_key import EnrollmentKey
from app.models.role import Role
from app.models.user import User
from app.services.enrollment_service import create_enrollment_key


def get_or_create_admin_user(db):
    role = db.get(Role, 1)
    if not role:
        role = Role(id=1, name="admin")
        db.add(role)
        db.commit()

    user = db.get(User, 1)
    if not user:
        user = User(id=1, username="enroll_admin", password_hash="hash", role_id=1)
        db.add(user)
        db.commit()
    return user


def test_enrollment_success(client, db_session):
    """Verify valid enrollment creates computer and credentials, returning 201."""
    admin = get_or_create_admin_user(db_session)
    key_record, plaintext_key = create_enrollment_key(db=db_session, created_by=admin.id)

    payload = {
        "enrollment_key": plaintext_key,
        "device": {
            "hostname": "ENROLL-PC-001",
            "ip_address": "192.168.1.101",
            "mac_address": "11:22:33:44:55:66",
            "os_name": "Windows",
            "os_version": "11 Pro",
        },
    }

    response = client.post("/api/agent/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "agent_id" in data
    assert "client_secret" in data
    assert "computer_id" in data
    assert data["agent_id"].startswith("AGT_")

    # Verify key is marked consumed (used_at)
    db_session.refresh(key_record)
    assert key_record.used_at is not None


def test_enrollment_invalid_key_rejected(client):
    """Verify non-existent enrollment key is rejected with 401."""
    payload = {
        "enrollment_key": "NON_EXISTENT_KEY_12345",
        "device": {
            "hostname": "ENROLL-PC-002",
            "ip_address": "192.168.1.102",
            "mac_address": "11:22:33:44:55:77",
            "os_name": "Windows",
            "os_version": "11 Pro",
        },
    }

    response = client.post("/api/agent/register", json=payload)
    assert response.status_code == 401
    assert "Invalid or expired enrollment key" in response.json()["detail"]


def test_enrollment_expired_key_rejected(client, db_session):
    """Verify expired enrollment key is rejected with 401."""
    admin = get_or_create_admin_user(db_session)
    key_record, plaintext_key = create_enrollment_key(
        db=db_session,
        created_by=admin.id,
    )
    # Manually expire the key
    key_record.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    payload = {
        "enrollment_key": plaintext_key,
        "device": {
            "hostname": "ENROLL-PC-003",
            "ip_address": "192.168.1.103",
            "mac_address": "11:22:33:44:55:88",
            "os_name": "Windows",
            "os_version": "11 Pro",
        },
    }

    response = client.post("/api/agent/register", json=payload)
    assert response.status_code == 401
    assert "Invalid or expired enrollment key" in response.json()["detail"]


def test_enrollment_consumed_key_cannot_be_reused(client, db_session):
    """Verify single-use enrollment key cannot be used a second time."""
    admin = get_or_create_admin_user(db_session)
    key_record, plaintext_key = create_enrollment_key(db=db_session, created_by=admin.id)

    payload1 = {
        "enrollment_key": plaintext_key,
        "device": {
            "hostname": "ENROLL-PC-004A",
            "ip_address": "192.168.1.104",
            "mac_address": "11:22:33:44:55:99",
            "os_name": "Windows",
            "os_version": "11 Pro",
        },
    }
    resp1 = client.post("/api/agent/register", json=payload1)
    assert resp1.status_code == 201

    payload2 = {
        "enrollment_key": plaintext_key,
        "device": {
            "hostname": "ENROLL-PC-004B",
            "ip_address": "192.168.1.105",
            "mac_address": "11:22:33:44:55:AA",
            "os_name": "Windows",
            "os_version": "11 Pro",
        },
    }
    resp2 = client.post("/api/agent/register", json=payload2)
    assert resp2.status_code == 401


def test_enrollment_hostname_conflict(client, db_session):
    """Verify registering an existing hostname returns 409 conflict."""
    admin = get_or_create_admin_user(db_session)
    key_record, plaintext_key = create_enrollment_key(db=db_session, created_by=admin.id)

    # Pre-seed computer with conflicting hostname
    existing = Computer(
        hostname="CONFLICT-HOST",
        ip_address="192.168.1.200",
        mac_address="22:33:44:55:66:77",
        os_name="Windows",
        os_version="11 Pro",
    )
    db_session.add(existing)
    db_session.commit()

    payload = {
        "enrollment_key": plaintext_key,
        "device": {
            "hostname": "CONFLICT-HOST",
            "ip_address": "192.168.1.201",
            "mac_address": "33:44:55:66:77:88",
            "os_name": "Windows",
            "os_version": "11 Pro",
        },
    }
    response = client.post("/api/agent/register", json=payload)
    assert response.status_code == 409
    assert "hostname" in response.json()["detail"].lower()


def test_enrollment_mac_conflict(client, db_session):
    """Verify registering an existing MAC address returns 409 conflict."""
    admin = get_or_create_admin_user(db_session)
    key_record, plaintext_key = create_enrollment_key(db=db_session, created_by=admin.id)

    existing = Computer(
        hostname="DIFF-HOST",
        ip_address="192.168.1.202",
        mac_address="AA:BB:CC:11:22:33",
        os_name="Windows",
        os_version="11 Pro",
    )
    db_session.add(existing)
    db_session.commit()

    payload = {
        "enrollment_key": plaintext_key,
        "device": {
            "hostname": "NEW-HOST-203",
            "ip_address": "192.168.1.203",
            "mac_address": "AA:BB:CC:11:22:33",
            "os_name": "Windows",
            "os_version": "11 Pro",
        },
    }
    response = client.post("/api/agent/register", json=payload)
    assert response.status_code == 409
    assert "mac address" in response.json()["detail"].lower()


def test_enrollment_validation_error_malformed_payload(client):
    """Verify malformed JSON payload returns 422 Unprocessable Entity."""
    # Missing required device fields
    payload = {
        "enrollment_key": "SOME_KEY",
        "device": {
            "hostname": "ONLY-HOSTNAME",
        },
    }
    response = client.post("/api/agent/register", json=payload)
    assert response.status_code == 422
