import uuid
import pytest
from app.auth import create_access_token, create_agent_access_token, hash_password
from app.models.agent_credential import AgentCredential
from app.models.computer import Computer
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User


@pytest.fixture
def auth_headers(db_session):
    """Create an admin user with VIEW_COMPUTERS permission and return Authorization headers."""
    role = db_session.query(Role).filter_by(name="HardwareTestAdminRole").first()
    if not role:
        role = Role(name="HardwareTestAdminRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    perm = (
        db_session.query(RolePermission)
        .filter_by(role_id=role.id, action_code="VIEW_COMPUTERS")
        .first()
    )
    if not perm:
        perm = RolePermission(role_id=role.id, action_code="VIEW_COMPUTERS", allowed=True)
        db_session.add(perm)
        db_session.commit()

    user = db_session.query(User).filter_by(username="hw_test_admin").first()
    if not user:
        user = User(
            username="hw_test_admin",
            password_hash=hash_password("AdminPass123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def registered_computer_and_agent(db_session):
    """Fixture providing a registered computer and an active agent credential."""
    uid = uuid.uuid4().hex[:6].upper()
    mac = f"AA:BB:CC:{uid[0:2]}:{uid[2:4]}:{uid[4:6]}"
    hostname = f"LAB-HW-{uid}"

    comp = Computer(
        hostname=hostname,
        ip_address="192.168.1.150",
        mac_address=mac,
        os_name="Windows 11 Pro",
        os_version="23H2",
    )
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)

    cred = AgentCredential(
        agent_id=f"agent-{uid}",
        secret_hash="fake-secret-hash",
        computer_id=comp.id,
        is_active=True,
    )
    db_session.add(cred)
    db_session.commit()
    db_session.refresh(cred)

    token = create_agent_access_token({
        "sub": cred.agent_id,
        "computer_id": comp.id,
    })

    yield comp, cred, token

    try:
        db_session.delete(comp)
        db_session.commit()
    except Exception:
        db_session.rollback()


def test_hardware_upload_requires_agent_token(client):
    """Verify posting hardware without agent token is rejected."""
    payload = {"processor_name": "Intel Core i7"}
    res = client.post("/api/clients/hardware", json=payload)
    assert res.status_code in (401, 403)


def test_hardware_upload_and_fetch(client, registered_computer_and_agent, auth_headers):
    """Verify an agent can upload hardware specifications and admin can fetch them."""
    computer, _, token = registered_computer_and_agent

    hardware_payload = {
        "manufacturer": "Dell Inc.",
        "model": "OptiPlex 7080",
        "serial_number": "8CNOXH3",
        "system_type": "64-bit Operating System",
        "bios_version": "Dell 1.18.0",
        "bios_date": "15-03-2023",
        "processor_name": "Intel(R) Core(TM) i5-10400",
        "processor_cores": 6,
        "processor_threads": 12,
        "processor_base_speed": "2.90 GHz",
        "processor_max_speed": "4.30 GHz",
        "ram_total_gb": 16.0,
        "ram_usable_gb": 15.8,
        "ram_type": "DDR4",
        "ram_speed": "2666 MHz",
        "ram_slots_used": 2,
        "ram_slots_total": 2,
        "storage_drives_count": 1,
        "storage_total_gb": 512.0,
        "storage_type": "SSD",
        "storage_health": "Good (92%)",
        "gpu_name": "Intel(R) UHD Graphics 630",
        "gpu_memory_mb": 128.0,
        "gpu_driver_version": "31.0.101.5333",
        "subnet_mask": "255.255.255.0",
        "default_gateway": "192.168.1.1",
        "dns_servers": "8.8.8.8",
        "connection_type": "Wi-Fi",
        "motherboard_manufacturer": "Dell Inc.",
        "motherboard_model": "0J7V1T",
        "motherboard_chipset": "Intel Comet Lake",
        "motherboard_serial": "/7V1T3M3",
        "os_install_date": "10-02-2024",
        "last_boot_time": "Today, 06:15 AM",
        "power_plan": "Balanced",
        "agent_version": "1.2.6",
    }

    # Upload from agent
    upload_res = client.post(
        "/api/clients/hardware",
        json=hardware_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert upload_res.status_code == 200
    uploaded_data = upload_res.json()
    assert uploaded_data["computer_id"] == computer.id
    assert uploaded_data["processor_name"] == "Intel(R) Core(TM) i5-10400"
    assert uploaded_data["manufacturer"] == "Dell Inc."
    assert uploaded_data["ram_total_gb"] == 16.0

    # Fetch computer details as admin
    get_res = client.get(
        f"/api/clients/{computer.id}",
        headers=auth_headers,
    )
    assert get_res.status_code == 200
    comp_data = get_res.json()
    assert "hardware" in comp_data
    assert comp_data["hardware"] is not None
    assert comp_data["hardware"]["processor_name"] == "Intel(R) Core(TM) i5-10400"
    assert comp_data["hardware"]["model"] == "OptiPlex 7080"
    assert comp_data["hardware"]["power_plan"] == "Balanced"

    # Fetch hardware sub-resource directly
    hw_res = client.get(
        f"/api/clients/{computer.id}/hardware",
        headers=auth_headers,
    )
    assert hw_res.status_code == 200
    hw_data = hw_res.json()
    assert hw_data["motherboard_model"] == "0J7V1T"


def test_hardware_subsequent_update(client, registered_computer_and_agent, auth_headers):
    """Verify subsequent hardware upload updates the existing record instead of duplicating."""
    computer, _, token = registered_computer_and_agent

    client.post(
        "/api/clients/hardware",
        json={"processor_name": "Old CPU", "ram_total_gb": 8.0},
        headers={"Authorization": f"Bearer {token}"},
    )

    update_res = client.post(
        "/api/clients/hardware",
        json={"processor_name": "Upgraded CPU", "ram_total_gb": 32.0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_res.status_code == 200

    hw_res = client.get(
        f"/api/clients/{computer.id}/hardware",
        headers=auth_headers,
    )
    assert hw_res.status_code == 200
    assert hw_res.json()["processor_name"] == "Upgraded CPU"
    assert hw_res.json()["ram_total_gb"] == 32.0


def test_computer_without_hardware_returns_null(client, db_session, auth_headers):
    """Verify computer without hardware returns null cleanly."""
    uid = uuid.uuid4().hex[:6].upper()
    mac = f"EE:FF:00:{uid[0:2]}:{uid[2:4]}:{uid[4:6]}"
    comp = Computer(
        hostname=f"LAB-NOHW-{uid}",
        ip_address="192.168.1.155",
        mac_address=mac,
        os_name="Linux",
        os_version="Ubuntu 22.04",
    )
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)

    res = client.get(f"/api/clients/{comp.id}", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["hardware"] is None

    try:
        db_session.delete(comp)
        db_session.commit()
    except Exception:
        db_session.rollback()
