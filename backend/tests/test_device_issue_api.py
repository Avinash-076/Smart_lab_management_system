"""
Integration tests for Agent Device Issue Ingestion, Idempotency, and Recovery (Phase 5 & 6).
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import select

from app.auth import create_access_token, create_agent_access_token, hash_password
from app.models.computer import Computer
from app.models.agent_credential import AgentCredential
from app.models.audit_log import AuditLog
from app.models.issue import Issue, IssueSeverity, IssueStatus, IssueSource
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User


@pytest.fixture
def device_test_setup(db_session):
    """Set up two computers and their registered agent credentials."""
    comp1 = db_session.get(Computer, 9101)
    if not comp1:
        comp1 = Computer(
            id=9101,
            hostname="LAB-PC-01",
            ip_address="192.168.10.101",
            mac_address="AA:BB:CC:DD:01:01",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp1)

    comp2 = db_session.get(Computer, 9102)
    if not comp2:
        comp2 = Computer(
            id=9102,
            hostname="LAB-PC-02",
            ip_address="192.168.10.102",
            mac_address="AA:BB:CC:DD:01:02",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp2)
    db_session.commit()

    cred1 = db_session.scalars(select(AgentCredential).where(AgentCredential.computer_id == 9101)).first()
    if not cred1:
        cred1 = AgentCredential(
            agent_id="agent_lab_01",
            computer_id=9101,
            secret_hash="secret1",
            is_active=True,
        )
        db_session.add(cred1)

    cred2 = db_session.scalars(select(AgentCredential).where(AgentCredential.computer_id == 9102)).first()
    if not cred2:
        cred2 = AgentCredential(
            agent_id="agent_lab_02",
            computer_id=9102,
            secret_hash="secret2",
            is_active=True,
        )
        db_session.add(cred2)
    db_session.commit()

    token1 = create_agent_access_token({"sub": "agent_lab_01", "computer_id": 9101})
    token2 = create_agent_access_token({"sub": "agent_lab_02", "computer_id": 9102})

    return {
        "comp1": comp1,
        "comp2": comp2,
        "token1": token1,
        "token2": token2,
    }


def test_agent_create_device_issue_and_audit(client, device_test_setup, db_session):
    """Agent creates unauthorized device issue with audit log and idempotency."""
    token = device_test_setup["token1"]
    payload = {
        "title": "Unauthorized USB Storage: Kingston DataTraveler 3.0",
        "description": "• Device Name: Kingston DataTraveler 3.0\n• Category: usb_storage\n• Status: UNAUTHORIZED",
        "severity": "critical",
        "idempotency_key": "issue_9101_device_abc123_inc001",
    }

    res = client.post(
        "/api/issues/agent",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["computer_id"] == 9101
    assert data["title"] == payload["title"]
    assert data["severity"] == "critical"
    assert data["status"] == "open"
    assert data["source"] == "agent"

    # Verify Audit Log
    audit = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "AGENT_ISSUE_CREATED",
            AuditLog.target_id == data["id"],
        )
    ).first()
    assert audit is not None


def test_agent_device_issue_idempotent(client, device_test_setup):
    """Repeated delivery of the same idempotency key returns the existing issue."""
    token = device_test_setup["token1"]
    payload = {
        "title": "Unauthorized USB Storage: SanDisk Ultra",
        "description": "SanDisk USB flash drive detected",
        "severity": "critical",
        "idempotency_key": "issue_9101_sandisk_001",
    }

    res1 = client.post("/api/issues/agent", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 201
    issue_id_1 = res1.json()["id"]

    res2 = client.post("/api/issues/agent", json=payload, headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 201
    issue_id_2 = res2.json()["id"]
    assert issue_id_1 == issue_id_2


def test_agent_recover_device_issue(client, device_test_setup, db_session):
    """When a device is unplugged, agent calls recover endpoint to resolve the active issue."""
    token = device_test_setup["token1"]
    create_payload = {
        "title": "Unauthorized USB Storage: PNY Flash Drive",
        "description": "PNY flash drive attached",
        "severity": "critical",
        "idempotency_key": "issue_9101_pny_001",
    }
    create_res = client.post("/api/issues/agent", json=create_payload, headers={"Authorization": f"Bearer {token}"})
    assert create_res.status_code == 201
    issue_id = create_res.json()["id"]

    # Now agent confirms physical disconnection and calls /agent/recover
    recover_payload = {
        "idempotency_key": "issue_9101_pny_001",
        "title": "Unauthorized USB Storage: PNY Flash Drive",
        "recovery_notes": "[Automated Recovery] Device confirmed removed at 2026-10-19T09:00:00Z",
    }
    rec_res = client.post("/api/issues/agent/recover", json=recover_payload, headers={"Authorization": f"Bearer {token}"})
    assert rec_res.status_code == 200
    rec_data = rec_res.json()
    assert rec_data["id"] == issue_id
    assert rec_data["status"] == "resolved"
    assert rec_data["resolved_at"] is not None
    assert "Device confirmed removed" in rec_data["resolution_notes"]

    # Verify audit log
    audit = db_session.scalars(
        select(AuditLog).where(
            AuditLog.action == "AGENT_ISSUE_RECOVERED",
            AuditLog.target_id == issue_id,
        )
    ).first()
    assert audit is not None


def test_agent_cannot_recover_other_computer_issue(client, device_test_setup):
    """Agent for Computer 2 cannot resolve or modify Computer 1's issues."""
    token1 = device_test_setup["token1"]
    token2 = device_test_setup["token2"]

    # Agent 1 creates issue on Computer 1
    create_payload = {
        "title": "Unauthorized Device: Wireless Dongle",
        "description": "Dongle on Comp 1",
        "severity": "high",
        "idempotency_key": "issue_9101_dongle_01",
    }
    res = client.post("/api/issues/agent", json=create_payload, headers={"Authorization": f"Bearer {token1}"})
    assert res.status_code == 201

    # Agent 2 attempts to recover Computer 1's issue
    recover_payload = {
        "idempotency_key": "issue_9101_dongle_01",
        "title": "Unauthorized Device: Wireless Dongle",
        "recovery_notes": "Attempting cross-computer recover",
    }
    cross_res = client.post("/api/issues/agent/recover", json=recover_payload, headers={"Authorization": f"Bearer {token2}"})
    assert cross_res.status_code == 404
    assert "not found" in cross_res.json()["detail"].lower()


def test_manage_issues_permission_allowed(client, db_session):
    """User with MANAGE_ISSUES permission can manage issues without needing UPDATE_COMPUTER."""
    role = db_session.scalars(select(Role).where(Role.name == "LabTechnicianRole")).first()
    if not role:
        role = Role(name="LabTechnicianRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    # Give ONLY VIEW_COMPUTERS and MANAGE_ISSUES (No UPDATE_COMPUTER!)
    for code in ["VIEW_COMPUTERS", "MANAGE_ISSUES"]:
        p = db_session.scalars(select(RolePermission).where(RolePermission.role_id == role.id, RolePermission.action_code == code)).first()
        if not p:
            db_session.add(RolePermission(role_id=role.id, action_code=code, allowed=True))
    db_session.commit()

    tech_user = db_session.scalars(select(User).where(User.username == "lab_technician")).first()
    if not tech_user:
        tech_user = User(
            username="lab_technician",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(tech_user)
        db_session.commit()
        db_session.refresh(tech_user)

    user_token = create_access_token({"sub": str(tech_user.id)})

    # Test create issue
    res = client.post(
        "/api/issues",
        json={
            "computer_id": 9101,
            "title": "Keyboard Key Stuck",
            "description": "Spacebar stuck",
            "severity": "low",
        },
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res.status_code == 201
    issue_id = res.json()["id"]

    # Test resolve issue
    res_resolve = client.post(
        f"/api/issues/{issue_id}/resolve",
        json={"resolution_notes": "Cleaned keyboard"},
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "resolved"
