from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.computer import Computer
from app.models.client_status import ClientStatus
from app.models.remote_command import RemoteCommand, CommandType, CommandStatus
from app.models.command_result import CommandResult
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.auth import hash_password, create_access_token


def create_test_computer(db: Session, hostname: str, ip: str, mac: str, status: str = "online") -> Computer:
    comp = Computer(
        hostname=hostname,
        ip_address=ip,
        mac_address=mac,
        os_name="Windows 11",
        os_version="23H2",
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)

    st = ClientStatus(
        computer_id=comp.id,
        status=status,
        last_seen=datetime.now(timezone.utc),
    )
    db.add(st)
    db.commit()
    db.refresh(comp)
    return comp


def create_user_with_permissions(db: Session, username: str, permissions: list[str]) -> tuple[User, str]:
    role = db.scalars(select(Role).where(Role.name == f"Role_{username}")).first()
    if not role:
        role = Role(name=f"Role_{username}", description="Test Role")
        db.add(role)
        db.commit()
        db.refresh(role)

    for action_code in permissions:
        perm = db.scalars(
            select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.action_code == action_code,
            )
        ).first()
        if not perm:
            perm = RolePermission(role_id=role.id, action_code=action_code, allowed=True)
            db.add(perm)
    db.commit()

    user = User(
        username=username,
        email=f"{username}@test.com",
        password_hash=hash_password("testpass123"),
        role_id=role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return user, token


def test_get_fleet_overview(client: TestClient, db_session: Session):
    admin_user, token = create_user_with_permissions(
        db_session, "admin_overview", ["VIEW_COMPUTERS", "ISSUE_COMMAND"]
    )
    headers = {"Authorization": f"Bearer {token}"}

    c1 = create_test_computer(db_session, "pc-ov-1", "10.0.0.1", "00:11:22:33:44:01", "online")
    c2 = create_test_computer(db_session, "pc-ov-2", "10.0.0.2", "00:11:22:33:44:02", "offline")

    cmd1 = RemoteCommand(
        computer_id=c1.id,
        command_type=CommandType.message,
        payload="Test",
        status=CommandStatus.executed,
        issued_by=admin_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(cmd1)
    db_session.commit()

    res = client.get("/api/commands/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_computers"] >= 2
    assert data["online_computers"] >= 1
    assert data["offline_computers"] >= 1
    assert data["commands_24h"] >= 1
    assert data["commands_24h_success"] >= 1


def test_batch_command_dispatch(client: TestClient, db_session: Session):
    admin_user, token = create_user_with_permissions(
        db_session, "admin_batch", ["VIEW_COMPUTERS", "ISSUE_COMMAND"]
    )
    headers = {"Authorization": f"Bearer {token}"}

    c1 = create_test_computer(db_session, "pc-batch-1", "10.0.1.1", "00:11:22:33:55:01", "online")
    c2 = create_test_computer(db_session, "pc-batch-2", "10.0.1.2", "00:11:22:33:55:02", "offline")

    payload = {
        "computer_ids": [c1.id, c2.id, 999999],  # 999999 is non-existent
        "command_type": "message",
        "payload": "Attention lab students",
    }

    res = client.post("/api/commands/batch", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["total_targets"] == 3
    assert data["dispatched_count"] == 2
    assert data["failed_count"] == 1

    # Check results list
    results = {r["computer_id"]: r for r in data["results"]}
    assert results[c1.id]["success"] is True
    assert results[c1.id]["computer_hostname"] == "pc-batch-1"
    assert results[c2.id]["success"] is True
    assert results[c2.id]["computer_hostname"] == "pc-batch-2"
    assert results[999999]["success"] is False
    assert "not found" in results[999999]["error"].lower()


def test_global_command_history(client: TestClient, db_session: Session):
    admin_user, token = create_user_with_permissions(
        db_session, "admin_history", ["VIEW_COMPUTERS", "ISSUE_COMMAND"]
    )
    headers = {"Authorization": f"Bearer {token}"}

    c1 = create_test_computer(db_session, "pc-hist-1", "10.0.2.1", "00:11:22:33:66:01", "online")
    cmd = RemoteCommand(
        computer_id=c1.id,
        command_type=CommandType.lock,
        payload=None,
        status=CommandStatus.executed,
        issued_by=admin_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    cmd_res = CommandResult(
        command_id=cmd.id,
        success=True,
        message="Workstation locked",
        duration_seconds=1.45,
    )
    db_session.add(cmd_res)
    db_session.commit()

    res = client.get("/api/commands", headers=headers)
    assert res.status_code == 200
    assert "X-Total-Count" in res.headers
    items = res.json()
    assert len(items) >= 1

    # Find the created command
    match = next((item for item in items if item["id"] == cmd.id), None)
    assert match is not None
    assert match["computer_hostname"] == "pc-hist-1"
    assert match["computer_ip"] == "10.0.2.1"
    assert match["command_type"] == "lock"
    assert match["status"] == "executed"
    assert match["duration_seconds"] == 1.45
    assert match["result"]["message"] == "Workstation locked"

    # Test filtering by command_type
    res_type = client.get("/api/commands?command_type=lock", headers=headers)
    assert res_type.status_code == 200
    assert all(item["command_type"] == "lock" for item in res_type.json())

    # Test search by hostname
    res_search = client.get("/api/commands?search=pc-hist-1", headers=headers)
    assert res_search.status_code == 200
    assert any(item["id"] == cmd.id for item in res_search.json())


def test_batch_command_permission_denied(client: TestClient, db_session: Session):
    user, token = create_user_with_permissions(
        db_session, "readonly_user", ["VIEW_COMPUTERS"]
    )
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "computer_ids": [1],
        "command_type": "lock",
    }
    res = client.post("/api/commands/batch", json=payload, headers=headers)
    assert res.status_code == 403
