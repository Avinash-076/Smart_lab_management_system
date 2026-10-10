from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.auth import create_access_token, hash_password
from app.models.audit_log import AuditLog, AuditResult
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.services import audit_service


@pytest.fixture
def audit_admin_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "AuditAdminRole")).first()
    if not role:
        role = Role(name="AuditAdminRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    for action_code in ["VIEW_COMPUTERS", "ISSUE_COMMAND", "UPDATE_COMPUTER", "DELETE_COMPUTER"]:
        perm = db_session.scalars(
            select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.action_code == action_code,
            )
        ).first()
        if not perm:
            perm = RolePermission(role_id=role.id, action_code=action_code, allowed=True)
            db_session.add(perm)
    db_session.commit()

    user = db_session.scalars(select(User).where(User.username == "audit_admin")).first()
    if not user:
        user = User(
            username="audit_admin",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def audit_unprivileged_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "AuditNoPermRole")).first()
    if not role:
        role = Role(name="AuditNoPermRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    user = db_session.scalars(select(User).where(User.username == "audit_noperm_user")).first()
    if not user:
        user = User(
            username="audit_noperm_user",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_audit_logs_unauthenticated(client: TestClient):
    resp = client.get("/api/audit-logs")
    assert resp.status_code == 401


def test_audit_logs_unprivileged(client: TestClient, audit_unprivileged_user):
    resp = client.get("/api/audit-logs", headers=audit_unprivileged_user["headers"])
    assert resp.status_code == 403


def test_audit_logs_list_and_pagination(client: TestClient, audit_admin_user, db_session):
    user = audit_admin_user["user"]
    # Seed 15 audit logs
    for i in range(15):
        audit_service.log_action(
            db=db_session,
            result=AuditResult.success if i % 2 == 0 else AuditResult.failure,
            action=f"TEST_ACTION_{i}",
            user_id=user.id,
            target_type="TEST",
            target_id=i,
        )

    resp = client.get("/api/audit-logs?page=1&limit=10", headers=audit_admin_user["headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "total_pages" in data
    assert data["page"] == 1
    assert data["limit"] == 10
    assert len(data["items"]) == 10
    assert data["total"] >= 15
    assert data["total_pages"] >= 2


def test_audit_logs_filter_by_action(client: TestClient, audit_admin_user, db_session):
    user = audit_admin_user["user"]
    audit_service.log_action(
        db=db_session,
        result=AuditResult.success,
        action="SPECIAL_AUDIT_ACTION_ABC",
        user_id=user.id,
    )

    resp = client.get(
        "/api/audit-logs?action=SPECIAL_AUDIT_ACTION_ABC",
        headers=audit_admin_user["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert all(item["action"] == "SPECIAL_AUDIT_ACTION_ABC" for item in data["items"])


def test_audit_logs_filter_by_result(client: TestClient, audit_admin_user, db_session):
    user = audit_admin_user["user"]
    audit_service.log_action(
        db=db_session,
        result=AuditResult.failure,
        action="FAILED_SECURITY_EVENT",
        user_id=user.id,
    )

    resp = client.get(
        "/api/audit-logs?result=failure&action=FAILED_SECURITY_EVENT",
        headers=audit_admin_user["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert all(item["result"] == "failure" for item in data["items"])


def test_audit_logs_filter_by_target(client: TestClient, audit_admin_user, db_session):
    user = audit_admin_user["user"]
    audit_service.log_action(
        db=db_session,
        result=AuditResult.success,
        action="TARGET_FILTER_ACTION",
        user_id=user.id,
        target_type="COMPUTER",
        target_id=8888,
    )

    resp = client.get(
        "/api/audit-logs?target_type=COMPUTER&target_id=8888",
        headers=audit_admin_user["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["target_type"] == "COMPUTER"
    assert data["items"][0]["target_id"] == 8888


def test_audit_logs_search(client: TestClient, audit_admin_user, db_session):
    user = audit_admin_user["user"]
    audit_service.log_action(
        db=db_session,
        result=AuditResult.success,
        action="UNIQUE_SEARCH_ACTION_XYZ",
        user_id=user.id,
    )

    resp = client.get(
        "/api/audit-logs?search=SEARCH_ACTION_XYZ",
        headers=audit_admin_user["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert "UNIQUE_SEARCH_ACTION_XYZ" in data["items"][0]["action"]


def test_audit_log_details(client: TestClient, audit_admin_user, db_session):
    user = audit_admin_user["user"]
    entry = audit_service.log_action(
        db=db_session,
        result=AuditResult.success,
        action="SINGLE_DETAIL_ACTION",
        user_id=user.id,
        target_type="TEST",
        target_id=42,
        ip_address="192.168.1.100",
    )

    resp = client.get(f"/api/audit-logs/{entry.id}", headers=audit_admin_user["headers"])
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["id"] == entry.id
    assert detail["action"] == "SINGLE_DETAIL_ACTION"
    assert detail["username"] == user.username
    assert detail["ip_address"] == "192.168.1.100"
    assert detail["result"] == "success"


def test_audit_log_details_not_found(client: TestClient, audit_admin_user):
    resp = client.get("/api/audit-logs/9999999", headers=audit_admin_user["headers"])
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Audit log entry not found"


def test_audit_service_sanitization(db_session, audit_admin_user):
    user = audit_admin_user["user"]
    long_action = "  ACTION_" + "A" * 200 + "  "
    long_target = "  TARGET_" + "B" * 100 + "  "
    entry = audit_service.log_action(
        db=db_session,
        result=AuditResult.success,
        action=long_action,
        target_type=long_target,
        user_id=user.id,
    )
    assert len(entry.action) <= 100
    assert not entry.action.startswith(" ")
    assert len(entry.target_type) <= 50
    assert not entry.target_type.startswith(" ")


def test_audit_logs_date_filters(client: TestClient, audit_admin_user, db_session):
    user = audit_admin_user["user"]
    now = datetime.now(timezone.utc)
    entry = audit_service.log_action(
        db=db_session,
        result=AuditResult.success,
        action="DATE_FILTER_ACTION",
        user_id=user.id,
    )

    date_from = (now - timedelta(minutes=5)).isoformat()
    date_to = (now + timedelta(minutes=5)).isoformat()

    resp = client.get(
        f"/api/audit-logs?action=DATE_FILTER_ACTION&date_from={date_from}&date_to={date_to}",
        headers=audit_admin_user["headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) >= 1
    assert data["items"][0]["id"] == entry.id
