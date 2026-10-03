import pytest
from sqlalchemy import select

from app.auth import create_access_token, create_agent_access_token, hash_password
from app.models.computer import Computer
from app.models.agent_credential import AgentCredential
from app.models.process import Process
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User


@pytest.fixture
def test_process_user(db_session):
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

    user = db_session.scalars(select(User).where(User.username == "proc_test_admin")).first()
    if not user:
        user = User(
            username="proc_test_admin",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token}


@pytest.fixture
def unprivileged_process_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "NoViewProcRole")).first()
    if not role:
        role = Role(name="NoViewProcRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    user = db_session.scalars(select(User).where(User.username == "proc_noview_user")).first()
    if not user:
        user = User(
            username="proc_noview_user",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token}


@pytest.fixture
def sample_computers_with_processes(db_session):
    # Computer A
    comp_a = db_session.get(Computer, 9001)
    if not comp_a:
        comp_a = Computer(
            id=9001,
            hostname="PROC-PC-A",
            ip_address="192.168.1.91",
            mac_address="00:11:22:33:44:91",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp_a)
        db_session.commit()
        db_session.refresh(comp_a)

    # Computer B
    comp_b = db_session.get(Computer, 9002)
    if not comp_b:
        comp_b = Computer(
            id=9002,
            hostname="PROC-PC-B",
            ip_address="192.168.1.92",
            mac_address="00:11:22:33:44:92",
            os_name="Windows",
            os_version="10 Enterprise",
        )
        db_session.add(comp_b)
        db_session.commit()
        db_session.refresh(comp_b)

    # Clean any prior processes
    db_session.query(Process).filter(Process.computer_id.in_([9001, 9002])).delete()
    db_session.commit()

    # Seed processes for Comp A
    p_a1 = Process(
        computer_id=9001,
        pid=1234,
        name="chrome.exe",
        user=None,
        cpu_percent=12.5,
        memory_percent=5.2,
        status="running",
        start_time="2026-10-01T08:00:00Z",
    )
    p_a2 = Process(
        computer_id=9001,
        pid=5678,
        name="code.exe",
        user=None,
        cpu_percent=25.0,
        memory_percent=8.1,
        status="running",
        start_time="2026-10-01T08:15:00Z",
    )
    p_a3 = Process(
        computer_id=9001,
        pid=9101,
        name="explorer.exe",
        user=None,
        cpu_percent=1.2,
        memory_percent=2.0,
        status="running",
        start_time="2026-10-01T07:30:00Z",
    )

    # Seed processes for Comp B
    p_b1 = Process(
        computer_id=9002,
        pid=2222,
        name="notepad.exe",
        user=None,
        cpu_percent=0.1,
        memory_percent=0.5,
        status="running",
        start_time="2026-10-01T09:00:00Z",
    )

    db_session.add_all([p_a1, p_a2, p_a3, p_b1])
    db_session.commit()

    return {"comp_a": comp_a, "comp_b": comp_b}


def test_get_processes_unauthenticated(client):
    """
    Unauthenticated request to GET /api/clients/{id}/processes must return 401.
    """
    res = client.get("/api/clients/9001/processes")
    assert res.status_code == 401

    res2 = client.get("/api/processes/9001")
    assert res2.status_code == 401


def test_get_processes_unprivileged(client, unprivileged_process_user):
    """
    User lacking VIEW_COMPUTERS permission must receive 403 Forbidden.
    """
    token = unprivileged_process_user["token"]
    res = client.get(
        "/api/clients/9001/processes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_get_processes_nonexistent_computer(client, test_process_user):
    """
    Request for non-existent computer must return 404 Not Found.
    """
    token = test_process_user["token"]
    res = client.get(
        "/api/clients/999999/processes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Computer not found"


def test_get_processes_empty_list(client, db_session, test_process_user):
    """
    Computer with no running processes recorded returns an empty list [].
    """
    comp_empty = db_session.get(Computer, 9003)
    if not comp_empty:
        comp_empty = Computer(
            id=9003,
            hostname="PROC-PC-EMPTY",
            ip_address="192.168.1.93",
            mac_address="00:11:22:33:44:93",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp_empty)
        db_session.commit()

    db_session.query(Process).filter(Process.computer_id == 9003).delete()
    db_session.commit()

    token = test_process_user["token"]
    res = client.get(
        "/api/clients/9003/processes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_processes_success_and_deterministic_order(
    client, test_process_user, sample_computers_with_processes
):
    """
    Returns running processes ordered deterministically by CPU% desc, Memory% desc, name asc, pid asc.
    """
    token = test_process_user["token"]
    res = client.get(
        "/api/clients/9001/processes",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3

    # Expected order:
    # 1. code.exe (cpu: 25.0)
    # 2. chrome.exe (cpu: 12.5)
    # 3. explorer.exe (cpu: 1.2)
    names = [item["name"] for item in data]
    assert names == ["code.exe", "chrome.exe", "explorer.exe"]

    # Verify schema fields
    item = data[0]
    assert item["name"] == "code.exe"
    assert item["pid"] == 5678
    assert item["cpu_percent"] == 25.0
    assert item["memory_percent"] == 8.1
    assert item["status"] == "running"
    assert item["computer_id"] == 9001
    assert "collected_at" in item


def test_get_processes_computer_isolation(
    client, test_process_user, sample_computers_with_processes
):
    """
    Computer A's processes do not leak into Computer B's response.
    """
    token = test_process_user["token"]

    res_a = client.get(
        "/api/clients/9001/processes",
        headers={"Authorization": f"Bearer {token}"},
    )
    res_b = client.get(
        "/api/clients/9002/processes",
        headers={"Authorization": f"Bearer {token}"},
    )

    names_a = [item["name"] for item in res_a.json()]
    names_b = [item["name"] for item in res_b.json()]

    assert "notepad.exe" not in names_a
    assert "code.exe" not in names_b
    assert names_b == ["notepad.exe"]


def test_get_processes_via_direct_route(
    client, test_process_user, sample_computers_with_processes
):
    """
    GET /api/processes/{computer_id} returns identical data to GET /api/clients/{computer_id}/processes.
    """
    token = test_process_user["token"]
    res = client.get(
        "/api/processes/9001",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert data[0]["name"] == "code.exe"


def test_agent_process_upload_snapshot_replacement(
    client, db_session, test_process_user
):
    """
    Agent uploading POST /api/processes replaces the previous snapshot completely.
    """
    comp = db_session.get(Computer, 9005)
    if not comp:
        comp = Computer(
            id=9005,
            hostname="PROC-AGENT-PC",
            ip_address="192.168.1.95",
            mac_address="00:11:22:33:44:95",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp)
        db_session.commit()

    agent_cred = db_session.query(AgentCredential).filter_by(agent_id="agent-proc-9005").first()
    if not agent_cred:
        agent_cred = AgentCredential(
            agent_id="agent-proc-9005",
            secret_hash="fake-hash-proc",
            computer_id=comp.id,
            is_active=True,
        )
        db_session.add(agent_cred)
        db_session.commit()

    agent_token = create_agent_access_token({
        "sub": "agent-proc-9005",
        "computer_id": comp.id,
    })

    # 1. Initial snapshot upload
    initial_payload = {
        "processes": [
            {"pid": 100, "name": "initial_app.exe", "cpu_percent": 5.0, "memory_percent": 2.0, "status": "running"},
            {"pid": 200, "name": "background_task.exe", "cpu_percent": 1.0, "memory_percent": 1.0, "status": "running"},
        ]
    }

    res1 = client.post(
        "/api/processes",
        headers={"Authorization": f"Bearer {agent_token}"},
        json=initial_payload,
    )
    assert res1.status_code == 201
    assert len(res1.json()) == 2

    # Verify query
    user_token = test_process_user["token"]
    get_res1 = client.get(
        f"/api/clients/{comp.id}/processes",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert get_res1.status_code == 200
    assert len(get_res1.json()) == 2
    assert get_res1.json()[0]["name"] == "initial_app.exe"

    # 2. Second snapshot upload (initial_app is terminated, new_app has started)
    second_payload = {
        "processes": [
            {"pid": 300, "name": "new_app.exe", "cpu_percent": 15.0, "memory_percent": 4.0, "status": "running"},
            {"pid": 200, "name": "background_task.exe", "cpu_percent": 1.5, "memory_percent": 1.0, "status": "running"},
        ]
    }

    res2 = client.post(
        "/api/processes",
        headers={"Authorization": f"Bearer {agent_token}"},
        json=second_payload,
    )
    assert res2.status_code == 201
    assert len(res2.json()) == 2

    # Verify snapshot replacement: initial_app.exe is gone
    get_res2 = client.get(
        f"/api/clients/{comp.id}/processes",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert get_res2.status_code == 200
    proc_names = [p["name"] for p in get_res2.json()]
    assert "initial_app.exe" not in proc_names
    assert "new_app.exe" in proc_names
    assert "background_task.exe" in proc_names
    assert proc_names[0] == "new_app.exe"  # Higher CPU (15.0 vs 1.5)


def test_agent_process_upload_unauthenticated(client):
    """
    Unauthenticated agent upload to POST /api/processes must return 401.
    """
    res = client.post(
        "/api/processes",
        json={"processes": [{"pid": 100, "name": "test.exe"}]},
    )
    assert res.status_code == 401
