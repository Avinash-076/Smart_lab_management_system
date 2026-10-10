from datetime import datetime, timezone
import pytest
from sqlalchemy import select

from app.auth import create_access_token, create_agent_access_token, hash_password
from app.models.computer import Computer
from app.models.agent_credential import AgentCredential
from app.models.issue import Issue, IssueSeverity, IssueStatus, IssueSource
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User


@pytest.fixture
def test_admin_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "Admin")).first()
    if not role:
        role = Role(name="Admin")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    for action_code in ["VIEW_COMPUTERS", "UPDATE_COMPUTER", "DELETE_COMPUTER"]:
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

    user = db_session.scalars(select(User).where(User.username == "issue_test_admin")).first()
    if not user:
        user = User(
            username="issue_test_admin",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token}


@pytest.fixture
def unprivileged_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "ReadOnlyRole")).first()
    if not role:
        role = Role(name="ReadOnlyRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    user = db_session.scalars(select(User).where(User.username == "issue_unprivileged_user")).first()
    if not user:
        user = User(
            username="issue_unprivileged_user",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token}


@pytest.fixture
def sample_computer(db_session):
    comp = db_session.get(Computer, 8001)
    if not comp:
        comp = Computer(
            id=8001,
            hostname="ISSUE-PC-01",
            ip_address="192.168.1.81",
            mac_address="00:11:22:33:44:81",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp)
        db_session.commit()
        db_session.refresh(comp)
    return comp


@pytest.fixture
def second_computer(db_session):
    comp = db_session.get(Computer, 8002)
    if not comp:
        comp = Computer(
            id=8002,
            hostname="ISSUE-PC-02",
            ip_address="192.168.1.82",
            mac_address="00:11:22:33:44:82",
            os_name="Windows",
            os_version="10 Pro",
        )
        db_session.add(comp)
        db_session.commit()
        db_session.refresh(comp)
    return comp


def test_unauthenticated_issues_rejected(client, sample_computer):
    resp = client.get("/api/issues")
    assert resp.status_code == 401

    resp = client.get("/api/issues/stats")
    assert resp.status_code == 401

    resp = client.post("/api/issues", json={"computer_id": sample_computer.id, "title": "Test", "description": "Test"})
    assert resp.status_code == 401

    resp = client.get(f"/api/clients/{sample_computer.id}/issues")
    assert resp.status_code == 401


def test_unauthorized_issues_rejected(client, unprivileged_user, sample_computer):
    headers = {"Authorization": f"Bearer {unprivileged_user['token']}"}

    resp = client.get("/api/issues", headers=headers)
    assert resp.status_code == 403

    resp = client.get("/api/issues/stats", headers=headers)
    assert resp.status_code == 403

    resp = client.post(
        "/api/issues",
        json={"computer_id": sample_computer.id, "title": "Fail", "description": "Fail"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_create_and_get_issue(client, test_admin_user, sample_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    payload = {
        "computer_id": sample_computer.id,
        "title": "High CPU Temperature",
        "description": "CPU core reached 92 degrees Celsius during lab session.",
        "severity": "high",
    }

    create_resp = client.post("/api/issues", json=payload, headers=headers)
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["id"] > 0
    assert data["title"] == "High CPU Temperature"
    assert data["computer_id"] == sample_computer.id
    assert data["severity"] == "high"
    assert data["status"] == "open"
    assert data["source"] == "admin"
    assert data["created_by"] == test_admin_user["user"].id

    issue_id = data["id"]

    # Get by ID
    get_resp = client.get(f"/api/issues/{issue_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == issue_id
    assert get_resp.json()["title"] == "High CPU Temperature"


def test_create_issue_nonexistent_computer(client, test_admin_user):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    payload = {
        "computer_id": 999999,
        "title": "Ghost Computer Issue",
        "description": "Should fail",
    }

    resp = client.post("/api/issues", json=payload, headers=headers)
    assert resp.status_code == 404
    assert "Computer not found" in resp.json()["detail"]


def test_get_nonexistent_issue(client, test_admin_user):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    resp = client.get("/api/issues/999999", headers=headers)
    assert resp.status_code == 404
    assert "Issue not found" in resp.json()["detail"]


def test_update_issue_status_and_lifecycle(client, test_admin_user, sample_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    # Create issue
    create_resp = client.post(
        "/api/issues",
        json={
            "computer_id": sample_computer.id,
            "title": "Low Disk Warning",
            "description": "Drive C has only 2GB free space.",
            "severity": "medium",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    issue_id = create_resp.json()["id"]

    # Transition to in_progress
    patch_resp = client.patch(
        f"/api/issues/{issue_id}",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "in_progress"
    assert patch_resp.json()["resolved_at"] is None

    # Resolve issue via /resolve endpoint
    resolve_resp = client.post(
        f"/api/issues/{issue_id}/resolve",
        json={"resolution_notes": "Cleared temp files and freed 25GB space."},
        headers=headers,
    )
    assert resolve_resp.status_code == 200
    res_data = resolve_resp.json()
    assert res_data["status"] == "resolved"
    assert res_data["resolution_notes"] == "Cleared temp files and freed 25GB space."
    assert res_data["resolved_at"] is not None
    assert res_data["resolved_by"] == test_admin_user["user"].id

    # Reopen issue
    reopen_resp = client.patch(
        f"/api/issues/{issue_id}",
        json={"status": "open"},
        headers=headers,
    )
    assert reopen_resp.status_code == 200
    reopen_data = reopen_resp.json()
    assert reopen_data["status"] == "open"
    assert reopen_data["resolved_at"] is None
    assert reopen_data["resolved_by"] is None
    assert reopen_data["resolution_notes"] is None


def test_issue_search_and_filtering(client, test_admin_user, sample_computer, second_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    # Seed distinct issues
    client.post(
        "/api/issues",
        json={
            "computer_id": sample_computer.id,
            "title": "RAM Leak Detected",
            "description": "Chrome consumes 14GB memory.",
            "severity": "critical",
        },
        headers=headers,
    )
    client.post(
        "/api/issues",
        json={
            "computer_id": second_computer.id,
            "title": "Outdated Python Environment",
            "description": "Python 3.8 installed, requires upgrade.",
            "severity": "low",
        },
        headers=headers,
    )

    # Filter by computer_id
    resp = client.get(f"/api/issues?computer_id={sample_computer.id}", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert all(item["computer_id"] == sample_computer.id for item in items)

    # Filter by severity
    resp = client.get("/api/issues?severity=critical", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert all(item["severity"] == "critical" for item in items)

    # Search keyword
    resp = client.get("/api/issues?search=Python", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert any("Python" in item["title"] for item in items)


def test_issue_stats_endpoint(client, test_admin_user, sample_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    resp = client.get("/api/issues/stats", headers=headers)
    assert resp.status_code == 200
    stats = resp.json()
    assert "total" in stats
    assert "open" in stats
    assert "in_progress" in stats
    assert "resolved" in stats
    assert stats["total"] >= stats["open"] + stats["in_progress"] + stats["resolved"]

    # Stats for specific computer
    resp_comp = client.get(f"/api/issues/stats?computer_id={sample_computer.id}", headers=headers)
    assert resp_comp.status_code == 200
    comp_stats = resp_comp.json()
    assert comp_stats["total"] <= stats["total"]


def test_computer_scoped_issues_endpoint(client, test_admin_user, sample_computer, second_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    client.post(
        "/api/issues",
        json={
            "computer_id": sample_computer.id,
            "title": "Scoped Test Issue",
            "description": "Testing computer sub-resource endpoint.",
            "severity": "medium",
        },
        headers=headers,
    )

    resp = client.get(f"/api/clients/{sample_computer.id}/issues", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert all(item["computer_id"] == sample_computer.id for item in data)

    # 404 for nonexistent computer
    resp_404 = client.get("/api/clients/999999/issues", headers=headers)
    assert resp_404.status_code == 404


def test_delete_issue(client, test_admin_user, sample_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    create_resp = client.post(
        "/api/issues",
        json={
            "computer_id": sample_computer.id,
            "title": "Temporary Issue to Delete",
            "description": "This will be deleted.",
            "severity": "low",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    issue_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/issues/{issue_id}", headers=headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/issues/{issue_id}", headers=headers)
    assert get_resp.status_code == 404
