from datetime import datetime, timezone
import pytest
from sqlalchemy import select

from app.auth import create_access_token, hash_password
from app.models.computer import Computer
from app.models.maintenance import MaintenanceRecord, MaintenanceStatus, MaintenanceType
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

    user = db_session.scalars(select(User).where(User.username == "maint_test_admin")).first()
    if not user:
        user = User(
            username="maint_test_admin",
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

    user = db_session.scalars(select(User).where(User.username == "maint_unprivileged_user")).first()
    if not user:
        user = User(
            username="maint_unprivileged_user",
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
    comp = db_session.get(Computer, 7001)
    if not comp:
        comp = Computer(
            id=7001,
            hostname="MAINT-PC-01",
            ip_address="192.168.1.71",
            mac_address="00:11:22:33:44:71",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp)
        db_session.commit()
        db_session.refresh(comp)
    return comp


@pytest.fixture
def second_computer(db_session):
    comp = db_session.get(Computer, 7002)
    if not comp:
        comp = Computer(
            id=7002,
            hostname="MAINT-PC-02",
            ip_address="192.168.1.72",
            mac_address="00:11:22:33:44:72",
            os_name="Windows",
            os_version="10 Enterprise",
        )
        db_session.add(comp)
        db_session.commit()
        db_session.refresh(comp)
    return comp


def test_unauthenticated_maintenance_rejected(client, sample_computer):
    resp = client.get("/api/maintenance")
    assert resp.status_code == 401

    resp = client.get("/api/maintenance/stats")
    assert resp.status_code == 401

    resp = client.post(
        "/api/maintenance",
        json={"computer_id": sample_computer.id, "maintenance_type": "preventive", "title": "Test"},
    )
    assert resp.status_code == 401

    resp = client.get(f"/api/clients/{sample_computer.id}/maintenance")
    assert resp.status_code == 401


def test_unauthorized_maintenance_rejected(client, unprivileged_user, sample_computer):
    headers = {"Authorization": f"Bearer {unprivileged_user['token']}"}

    resp = client.get("/api/maintenance", headers=headers)
    assert resp.status_code == 403

    resp = client.get("/api/maintenance/stats", headers=headers)
    assert resp.status_code == 403

    resp = client.post(
        "/api/maintenance",
        json={"computer_id": sample_computer.id, "maintenance_type": "preventive", "title": "Fail"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_create_and_get_maintenance(client, test_admin_user, sample_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    payload = {
        "computer_id": sample_computer.id,
        "maintenance_type": "preventive",
        "title": "Quarterly Thermal Paste & Dust Clean",
        "description": "Clean dust filters and replace thermal interface material.",
        "technician_name": "Senior Tech Dave",
        "notes": "Ensure cooling fans operate quietly after reassembly.",
    }

    create_resp = client.post("/api/maintenance", json=payload, headers=headers)
    assert create_resp.status_code == 201
    data = create_resp.json()
    assert data["id"] > 0
    assert data["title"] == "Quarterly Thermal Paste & Dust Clean"
    assert data["computer_id"] == sample_computer.id
    assert data["maintenance_type"] == "preventive"
    assert data["status"] == "scheduled"
    assert data["technician_name"] == "Senior Tech Dave"
    assert data["created_by"] == test_admin_user["user"].id

    maint_id = data["id"]

    # Get by ID
    get_resp = client.get(f"/api/maintenance/{maint_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == maint_id
    assert get_resp.json()["title"] == "Quarterly Thermal Paste & Dust Clean"


def test_create_maintenance_nonexistent_computer(client, test_admin_user):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    payload = {
        "computer_id": 999999,
        "maintenance_type": "hardware",
        "title": "Ghost Computer Repair",
    }

    resp = client.post("/api/maintenance", json=payload, headers=headers)
    assert resp.status_code == 404
    assert "Computer not found" in resp.json()["detail"]


def test_get_nonexistent_maintenance(client, test_admin_user):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    resp = client.get("/api/maintenance/999999", headers=headers)
    assert resp.status_code == 404
    assert "Maintenance record not found" in resp.json()["detail"]


def test_update_maintenance_lifecycle(client, test_admin_user, sample_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    create_resp = client.post(
        "/api/maintenance",
        json={
            "computer_id": sample_computer.id,
            "maintenance_type": "software",
            "title": "OS Security Patch Update",
            "description": "Deploy KB5034441 and verify reboot cycle.",
            "technician_name": "Admin Alex",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    maint_id = create_resp.json()["id"]

    # Transition to in_progress
    patch_resp = client.patch(
        f"/api/maintenance/{maint_id}",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["status"] == "in_progress"
    assert patch_data["started_at"] is not None
    assert patch_data["completed_at"] is None

    # Complete maintenance via /complete endpoint
    complete_resp = client.post(
        f"/api/maintenance/{maint_id}/complete",
        json={
            "work_performed": "KB5034441 installed cleanly, system verified healthy.",
            "notes": "No user issues reported.",
        },
        headers=headers,
    )
    assert complete_resp.status_code == 200
    comp_data = complete_resp.json()
    assert comp_data["status"] == "completed"
    assert comp_data["work_performed"] == "KB5034441 installed cleanly, system verified healthy."
    assert comp_data["completed_at"] is not None

    # Cancel transition
    cancel_resp = client.patch(
        f"/api/maintenance/{maint_id}",
        json={"status": "cancelled"},
        headers=headers,
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
    assert cancel_resp.json()["completed_at"] is None


def test_maintenance_search_and_filtering(client, test_admin_user, sample_computer, second_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    client.post(
        "/api/maintenance",
        json={
            "computer_id": sample_computer.id,
            "maintenance_type": "hardware",
            "title": "RAM Replacement",
            "description": "Replace faulty DDR5 stick in slot 2.",
            "technician_name": "Hardware Specialist",
        },
        headers=headers,
    )
    client.post(
        "/api/maintenance",
        json={
            "computer_id": second_computer.id,
            "maintenance_type": "software",
            "title": "Matlab License Update",
            "description": "Renew lab network license server config.",
            "technician_name": "Software Tech",
        },
        headers=headers,
    )

    # Filter by computer_id
    resp = client.get(f"/api/maintenance?computer_id={sample_computer.id}", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert all(item["computer_id"] == sample_computer.id for item in items)

    # Filter by maintenance_type
    resp = client.get("/api/maintenance?type=hardware", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert all(item["maintenance_type"] == "hardware" for item in items)

    # Search keyword
    resp = client.get("/api/maintenance?search=Matlab", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1
    assert any("Matlab" in item["title"] for item in items)


def test_maintenance_stats_endpoint(client, test_admin_user, sample_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    resp = client.get("/api/maintenance/stats", headers=headers)
    assert resp.status_code == 200
    stats = resp.json()
    assert "total" in stats
    assert "scheduled" in stats
    assert "in_progress" in stats
    assert "completed" in stats
    assert "cancelled" in stats
    assert "preventive" in stats
    assert "hardware" in stats
    assert "software" in stats
    assert stats["total"] >= stats["scheduled"] + stats["in_progress"] + stats["completed"] + stats["cancelled"]

    # Scoped stats for computer
    resp_comp = client.get(f"/api/maintenance/stats?computer_id={sample_computer.id}", headers=headers)
    assert resp_comp.status_code == 200
    comp_stats = resp_comp.json()
    assert comp_stats["total"] <= stats["total"]


def test_computer_scoped_maintenance_endpoint(client, test_admin_user, sample_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    client.post(
        "/api/maintenance",
        json={
            "computer_id": sample_computer.id,
            "maintenance_type": "emergency",
            "title": "Unscheduled Power Supply Swap",
            "description": "PSU fan seized, replacement installed.",
        },
        headers=headers,
    )

    resp = client.get(f"/api/clients/{sample_computer.id}/maintenance", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert all(item["computer_id"] == sample_computer.id for item in data)

    # 404 for nonexistent computer
    resp_404 = client.get("/api/clients/999999/maintenance", headers=headers)
    assert resp_404.status_code == 404


def test_delete_maintenance(client, test_admin_user, sample_computer):
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    create_resp = client.post(
        "/api/maintenance",
        json={
            "computer_id": sample_computer.id,
            "maintenance_type": "corrective",
            "title": "Disposable Maintenance Task",
            "description": "Will be deleted.",
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    maint_id = create_resp.json()["id"]

    del_resp = client.delete(f"/api/maintenance/{maint_id}", headers=headers)
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/maintenance/{maint_id}", headers=headers)
    assert get_resp.status_code == 404
