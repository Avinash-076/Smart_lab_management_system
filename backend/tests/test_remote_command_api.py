from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.auth import create_access_token, hash_password
from app.models.remote_command import RemoteCommand, CommandType, CommandStatus
from app.models.command_result import CommandResult
from app.models.audit_log import AuditLog, AuditResult
from app.models.computer import Computer
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User


@pytest.fixture
def admin_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "CmdAdminRole")).first()
    if not role:
        role = Role(name="CmdAdminRole")
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

    user = db_session.scalars(select(User).where(User.username == "cmd_test_admin")).first()
    if not user:
        user = User(
            username="cmd_test_admin",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def unprivileged_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "CmdReadOnlyRole")).first()
    if not role:
        role = Role(name="CmdReadOnlyRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    perm = db_session.scalars(
        select(RolePermission).where(
            RolePermission.role_id == role.id,
            RolePermission.action_code == "VIEW_COMPUTERS",
        )
    ).first()
    if not perm:
        perm = RolePermission(role_id=role.id, action_code="VIEW_COMPUTERS", allowed=True)
        db_session.add(perm)
    db_session.commit()

    user = db_session.scalars(select(User).where(User.username == "cmd_viewer")).first()
    if not user:
        user = User(
            username="cmd_viewer",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


def test_issue_command_unauthenticated(client: TestClient):
    resp = client.post("/api/commands/1", json={"command_type": "lock"})
    assert resp.status_code == 401


def test_issue_command_unprivileged_role(client: TestClient, registered_agent, unprivileged_user):
    comp_id = registered_agent["computer_id"]
    resp = client.post(
        f"/api/commands/{comp_id}",
        json={"command_type": "lock"},
        headers=unprivileged_user["headers"],
    )
    assert resp.status_code == 403


def test_issue_command_missing_computer(client: TestClient, admin_user):
    resp = client.post(
        "/api/commands/999999",
        json={"command_type": "lock"},
        headers=admin_user["headers"],
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Computer not found"


def test_issue_command_invalid_type(client: TestClient, registered_agent, admin_user):
    comp_id = registered_agent["computer_id"]
    resp = client.post(
        f"/api/commands/{comp_id}",
        json={"command_type": "unrestricted_shell_exec", "payload": "rm -rf /"},
        headers=admin_user["headers"],
    )
    assert resp.status_code == 422


def test_issue_command_payload_too_long(client: TestClient, registered_agent, admin_user):
    comp_id = registered_agent["computer_id"]
    resp = client.post(
        f"/api/commands/{comp_id}",
        json={"command_type": "message", "payload": "A" * 300},
        headers=admin_user["headers"],
    )
    assert resp.status_code == 422


def test_issue_command_offline_target(client: TestClient, registered_agent, admin_user, db_session):
    comp_id = registered_agent["computer_id"]
    resp = client.post(
        f"/api/commands/{comp_id}",
        json={"command_type": "message", "payload": "Lab closing in 10 minutes"},
        headers=admin_user["headers"],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["computer_id"] == comp_id
    assert data["command_type"] == "message"
    assert data["payload"] == "Lab closing in 10 minutes"
    assert data["status"] in ("pending", "delivered")
    assert "created_at" in data
    assert data["result"] is None

    # Check audit log recorded
    audit_entry = db_session.query(AuditLog).filter(
        AuditLog.action == "ISSUE_COMMAND_MESSAGE",
        AuditLog.target_id == comp_id,
    ).first()
    assert audit_entry is not None
    assert audit_entry.result == AuditResult.success


def test_get_command_history(client: TestClient, registered_agent, admin_user):
    comp_id = registered_agent["computer_id"]

    # Issue two commands
    client.post(
        f"/api/commands/{comp_id}",
        json={"command_type": "lock"},
        headers=admin_user["headers"],
    )
    client.post(
        f"/api/commands/{comp_id}",
        json={"command_type": "restart"},
        headers=admin_user["headers"],
    )

    resp = client.get(f"/api/commands/{comp_id}", headers=admin_user["headers"])
    assert resp.status_code == 200
    commands = resp.json()
    assert len(commands) >= 2
    types = [c["command_type"] for c in commands]
    assert "lock" in types
    assert "restart" in types


def test_get_command_details(client: TestClient, registered_agent, admin_user):
    comp_id = registered_agent["computer_id"]
    create_resp = client.post(
        f"/api/commands/{comp_id}",
        json={"command_type": "lock"},
        headers=admin_user["headers"],
    )
    cmd_id = create_resp.json()["id"]

    detail_resp = client.get(f"/api/commands/detail/{cmd_id}", headers=admin_user["headers"])
    assert detail_resp.status_code == 200
    data = detail_resp.json()
    assert data["id"] == cmd_id
    assert data["command_type"] == "lock"

    # Non-existent command details -> 404
    missing_resp = client.get("/api/commands/detail/999999", headers=admin_user["headers"])
    assert missing_resp.status_code == 404


def test_cancel_pending_command(client: TestClient, registered_agent, admin_user, db_session):
    comp_id = registered_agent["computer_id"]
    user = admin_user["user"]

    cmd = RemoteCommand(
        computer_id=comp_id,
        command_type=CommandType.shutdown,
        payload=None,
        status=CommandStatus.pending,
        issued_by=user.id,
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    cancel_resp = client.post(f"/api/commands/{cmd.id}/cancel", headers=admin_user["headers"])
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Check audit log recorded
    audit_entry = db_session.query(AuditLog).filter(
        AuditLog.action == "CANCEL_COMMAND",
        AuditLog.target_id == cmd.id,
    ).first()
    assert audit_entry is not None


def test_cancel_non_pending_command_conflict(client: TestClient, registered_agent, admin_user, db_session):
    comp_id = registered_agent["computer_id"]
    user = admin_user["user"]

    cmd = RemoteCommand(
        computer_id=comp_id,
        command_type=CommandType.lock,
        payload=None,
        status=CommandStatus.executed,
        issued_by=user.id,
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    cancel_resp = client.post(f"/api/commands/{cmd.id}/cancel", headers=admin_user["headers"])
    assert cancel_resp.status_code == 409
    assert "cannot be cancelled" in cancel_resp.json()["detail"]


def test_submit_command_result_lifecycle(client: TestClient, registered_agent, admin_user, db_session):
    comp_id = registered_agent["computer_id"]
    agent_token = registered_agent["token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    user = admin_user["user"]

    cmd = RemoteCommand(
        computer_id=comp_id,
        command_type=CommandType.lock,
        payload=None,
        status=CommandStatus.delivered,
        issued_by=user.id,
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    # Submit result from agent
    result_resp = client.post(
        f"/api/commands/{cmd.id}/result",
        json={"success": True, "message": "Workstation locked successfully"},
        headers=agent_headers,
    )
    assert result_resp.status_code == 201
    res_data = result_resp.json()
    assert res_data["command_id"] == cmd.id
    assert res_data["success"] is True
    assert res_data["message"] == "Workstation locked successfully"
    assert "completed_at" in res_data

    # Verify command status updated to executed and result hydrated
    detail_resp = client.get(f"/api/commands/detail/{cmd.id}", headers=admin_user["headers"])
    assert detail_resp.status_code == 200
    cmd_data = detail_resp.json()
    assert cmd_data["status"] == "executed"
    assert cmd_data["result"] is not None
    assert cmd_data["result"]["success"] is True
    assert cmd_data["result"]["message"] == "Workstation locked successfully"


def test_submit_command_result_wrong_agent_isolation(client: TestClient, registered_agent, admin_user, db_session):
    # Create a command for another computer
    other_comp = Computer(
        hostname="PC-OTHER-CMD",
        ip_address="192.168.1.50",
        mac_address="00:11:22:33:44:55",
        os_name="Windows",
        os_version="11",
    )
    db_session.add(other_comp)
    db_session.commit()
    db_session.refresh(other_comp)

    user = admin_user["user"]
    other_cmd = RemoteCommand(
        computer_id=other_comp.id,
        command_type=CommandType.lock,
        payload=None,
        status=CommandStatus.delivered,
        issued_by=user.id,
    )
    db_session.add(other_cmd)
    db_session.commit()
    db_session.refresh(other_cmd)

    # Attempt to submit result using registered_agent (different computer_id)
    agent_token = registered_agent["token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}

    resp = client.post(
        f"/api/commands/{other_cmd.id}/result",
        json={"success": True, "message": "Malicious result injection"},
        headers=agent_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Command not found"


def test_submit_command_result_idempotency_duplicate(client: TestClient, registered_agent, admin_user, db_session):
    comp_id = registered_agent["computer_id"]
    agent_token = registered_agent["token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    user = admin_user["user"]

    cmd = RemoteCommand(
        computer_id=comp_id,
        command_type=CommandType.restart,
        payload=None,
        status=CommandStatus.delivered,
        issued_by=user.id,
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    # First submission
    resp1 = client.post(
        f"/api/commands/{cmd.id}/result",
        json={"success": True, "message": "Restart scheduled"},
        headers=agent_headers,
    )
    assert resp1.status_code == 201

    # Duplicate identical submission (e.g. network retry)
    resp2 = client.post(
        f"/api/commands/{cmd.id}/result",
        json={"success": True, "message": "Restart scheduled"},
        headers=agent_headers,
    )
    assert resp2.status_code == 201
    assert resp2.json()["id"] == resp1.json()["id"]

    # Verify that only ONE audit log entry was created for this command result
    audit_entries = db_session.query(AuditLog).filter(
        AuditLog.target_id == cmd.id,
        AuditLog.action.like("COMMAND_%"),
    ).all()
    assert len(audit_entries) == 1


def test_submit_command_result_contradictory_conflict(client: TestClient, registered_agent, admin_user, db_session):
    comp_id = registered_agent["computer_id"]
    agent_token = registered_agent["token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    user = admin_user["user"]

    cmd = RemoteCommand(
        computer_id=comp_id,
        command_type=CommandType.restart,
        payload=None,
        status=CommandStatus.delivered,
        issued_by=user.id,
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    # First submission
    resp1 = client.post(
        f"/api/commands/{cmd.id}/result",
        json={"success": True, "message": "Restart scheduled"},
        headers=agent_headers,
    )
    assert resp1.status_code == 201

    # Contradictory second submission
    resp2 = client.post(
        f"/api/commands/{cmd.id}/result",
        json={"success": False, "message": "Restart failed"},
        headers=agent_headers,
    )
    assert resp2.status_code == 409


def test_computer_router_commands_endpoint(client: TestClient, registered_agent, admin_user):
    comp_id = registered_agent["computer_id"]
    resp = client.get(f"/api/clients/{comp_id}/commands", headers=admin_user["headers"])
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    # Non-existent computer -> 404
    missing_resp = client.get("/api/clients/999999/commands", headers=admin_user["headers"])
    assert missing_resp.status_code == 404


def test_submit_command_result_on_cancelled_command_conflict(client: TestClient, registered_agent, admin_user, db_session):
    comp_id = registered_agent["computer_id"]
    agent_token = registered_agent["token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    user = admin_user["user"]

    cmd = RemoteCommand(
        computer_id=comp_id,
        command_type=CommandType.lock,
        payload=None,
        status=CommandStatus.cancelled,
        issued_by=user.id,
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    resp = client.post(
        f"/api/commands/{cmd.id}/result",
        json={"success": True, "message": "Workstation locked"},
        headers=agent_headers,
    )
    assert resp.status_code == 409
    assert "Cancelled command cannot receive a result" in resp.json()["detail"]


def test_submit_command_result_on_pending_command_conflict(client: TestClient, registered_agent, admin_user, db_session):
    comp_id = registered_agent["computer_id"]
    agent_token = registered_agent["token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    user = admin_user["user"]

    cmd = RemoteCommand(
        computer_id=comp_id,
        command_type=CommandType.lock,
        payload=None,
        status=CommandStatus.pending,
        issued_by=user.id,
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    resp = client.post(
        f"/api/commands/{cmd.id}/result",
        json={"success": True, "message": "Workstation locked"},
        headers=agent_headers,
    )
    assert resp.status_code == 409
    assert "Command has not been delivered" in resp.json()["detail"]


def test_submit_command_result_message_too_long(client: TestClient, registered_agent, admin_user, db_session):
    comp_id = registered_agent["computer_id"]
    agent_token = registered_agent["token"]
    agent_headers = {"Authorization": f"Bearer {agent_token}"}
    user = admin_user["user"]

    cmd = RemoteCommand(
        computer_id=comp_id,
        command_type=CommandType.lock,
        payload=None,
        status=CommandStatus.delivered,
        issued_by=user.id,
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    resp = client.post(
        f"/api/commands/{cmd.id}/result",
        json={"success": True, "message": "A" * 300},
        headers=agent_headers,
    )
    assert resp.status_code == 422
