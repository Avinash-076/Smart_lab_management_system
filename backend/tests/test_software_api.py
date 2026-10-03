import pytest
from sqlalchemy import select

from app.auth import create_access_token, create_agent_access_token, hash_password
from app.models.computer import Computer
from app.models.agent_credential import AgentCredential
from app.models.software import Software
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User


@pytest.fixture
def test_software_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "Admin")).first()
    if not role:
        role = Role(name="Admin")
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

    user = db_session.scalars(select(User).where(User.username == "sw_test_admin")).first()
    if not user:
        user = User(
            username="sw_test_admin",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token}


@pytest.fixture
def unprivileged_software_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "NoViewRole")).first()
    if not role:
        role = Role(name="NoViewRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    user = db_session.scalars(select(User).where(User.username == "sw_noview_user")).first()
    if not user:
        user = User(
            username="sw_noview_user",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token}


@pytest.fixture
def sample_computers_with_software(db_session):
    # Computer A
    comp_a = db_session.get(Computer, 8001)
    if not comp_a:
        comp_a = Computer(
            id=8001,
            hostname="SW-PC-A",
            ip_address="192.168.1.81",
            mac_address="00:11:22:33:44:81",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp_a)
        db_session.commit()
        db_session.refresh(comp_a)

    # Computer B
    comp_b = db_session.get(Computer, 8002)
    if not comp_b:
        comp_b = Computer(
            id=8002,
            hostname="SW-PC-B",
            ip_address="192.168.1.82",
            mac_address="00:11:22:33:44:82",
            os_name="Windows",
            os_version="10 Enterprise",
        )
        db_session.add(comp_b)
        db_session.commit()
        db_session.refresh(comp_b)

    # Seed software for Comp A
    db_session.query(Software).filter(Software.computer_id.in_([8001, 8002])).delete()
    db_session.commit()

    sw_a1 = Software(
        computer_id=8001,
        name="VS Code",
        version="1.93.0",
        publisher="Microsoft Corporation",
        install_date="2026-01-15",
    )
    sw_a2 = Software(
        computer_id=8001,
        name="Google Chrome",
        version="128.0.6613.120",
        publisher="Google LLC",
        install_date="2026-02-10",
    )
    sw_a3 = Software(
        computer_id=8001,
        name="7-Zip",
        version="24.08",
        publisher="Igor Pavlov",
        install_date="2025-11-01",
    )

    # Seed software for Comp B
    sw_b1 = Software(
        computer_id=8002,
        name="Wireshark",
        version="4.2.6",
        publisher="The Wireshark Team",
        install_date="2026-03-01",
    )

    db_session.add_all([sw_a1, sw_a2, sw_a3, sw_b1])
    db_session.commit()

    return {"comp_a": comp_a, "comp_b": comp_b}


def test_get_software_unauthenticated(client):
    """
    Unauthenticated request to GET /api/clients/{id}/software must return 401.
    """
    res = client.get("/api/clients/8001/software")
    assert res.status_code == 401


def test_get_software_unprivileged(client, unprivileged_software_user):
    """
    User lacking VIEW_COMPUTERS permission must receive 403 Forbidden.
    """
    token = unprivileged_software_user["token"]
    res = client.get(
        "/api/clients/8001/software",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_get_software_nonexistent_computer(client, test_software_user):
    """
    Request for non-existent computer must return 404 Not Found.
    """
    token = test_software_user["token"]
    res = client.get(
        "/api/clients/999999/software",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Computer not found"


def test_get_software_empty_inventory(client, db_session, test_software_user):
    """
    Computer with no software returns an empty list [].
    """
    comp_empty = db_session.get(Computer, 8003)
    if not comp_empty:
        comp_empty = Computer(
            id=8003,
            hostname="SW-PC-EMPTY",
            ip_address="192.168.1.83",
            mac_address="00:11:22:33:44:83",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp_empty)
        db_session.commit()

    db_session.query(Software).filter(Software.computer_id == 8003).delete()
    db_session.commit()

    token = test_software_user["token"]
    res = client.get(
        "/api/clients/8003/software",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_software_success_and_deterministic_order(
    client, test_software_user, sample_computers_with_software
):
    """
    Returns installed software sorted alphabetically by name.
    """
    token = test_software_user["token"]
    res = client.get(
        "/api/clients/8001/software",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3

    # Check alphabetical ordering: "7-Zip" -> "Google Chrome" -> "VS Code"
    names = [item["name"] for item in data]
    assert names == ["7-Zip", "Google Chrome", "VS Code"]

    # Verify schema fields
    item = data[0]
    assert item["name"] == "7-Zip"
    assert item["version"] == "24.08"
    assert item["publisher"] == "Igor Pavlov"
    assert item["install_date"] == "2025-11-01"
    assert item["computer_id"] == 8001
    assert "collected_at" in item


def test_get_software_computer_isolation(
    client, test_software_user, sample_computers_with_software
):
    """
    Computer A's inventory does not leak into Computer B's response.
    """
    token = test_software_user["token"]

    res_a = client.get(
        "/api/clients/8001/software",
        headers={"Authorization": f"Bearer {token}"},
    )
    res_b = client.get(
        "/api/clients/8002/software",
        headers={"Authorization": f"Bearer {token}"},
    )

    names_a = [item["name"] for item in res_a.json()]
    names_b = [item["name"] for item in res_b.json()]

    assert "Wireshark" not in names_a
    assert "VS Code" not in names_b
    assert names_b == ["Wireshark"]


def test_get_software_via_direct_software_route(
    client, test_software_user, sample_computers_with_software
):
    """
    GET /api/software/{computer_id} is also accessible and returns identical data.
    """
    token = test_software_user["token"]
    res = client.get(
        "/api/software/8001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert data[0]["name"] == "7-Zip"


def test_agent_software_upload_and_replacement(
    client, db_session, test_software_user
):
    """
    Agent uploading POST /api/software replaces inventory and deduplicates items.
    """
    comp = db_session.get(Computer, 8005)
    if not comp:
        comp = Computer(
            id=8005,
            hostname="SW-AGENT-PC",
            ip_address="192.168.1.85",
            mac_address="00:11:22:33:44:85",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp)
        db_session.commit()

    agent_cred = db_session.query(AgentCredential).filter_by(agent_id="agent-sw-8005").first()
    if not agent_cred:
        agent_cred = AgentCredential(
            agent_id="agent-sw-8005",
            secret_hash="fake-hash-sw",
            computer_id=comp.id,
            is_active=True,
        )
        db_session.add(agent_cred)
        db_session.commit()

    agent_token = create_agent_access_token({
        "sub": "agent-sw-8005",
        "computer_id": comp.id,
    })

    # Upload software list with duplicate items
    payload = {
        "software": [
            {"name": "Notepad++", "version": "8.6.9", "publisher": "Don Ho", "install_date": "2026-01-01"},
            {"name": "Notepad++", "version": "8.6.9", "publisher": "Don Ho", "install_date": "2026-01-01"},
            {"name": "Git", "version": "2.46.0", "publisher": "The Git Development Community", "install_date": "2026-02-01"},
        ]
    }

    upload_res = client.post(
        "/api/software",
        headers={"Authorization": f"Bearer {agent_token}"},
        json=payload,
    )
    assert upload_res.status_code == 201
    uploaded_data = upload_res.json()
    assert len(uploaded_data) == 2  # Deduplicated from 3 to 2

    # Query via dashboard user endpoint
    user_token = test_software_user["token"]
    get_res = client.get(
        f"/api/clients/{comp.id}/software",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert get_res.status_code == 200
    sw_data = get_res.json()
    assert len(sw_data) == 2
    assert sw_data[0]["name"] == "Git"
    assert sw_data[1]["name"] == "Notepad++"
