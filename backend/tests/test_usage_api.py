from datetime import datetime, timezone, timedelta
import pytest
from sqlalchemy import select

from app.auth import create_access_token, create_agent_access_token, hash_password
from app.models.computer import Computer
from app.models.agent_credential import AgentCredential
from app.models.usage_session import UsageSession
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User


@pytest.fixture
def test_usage_user(db_session):
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

    user = db_session.scalars(select(User).where(User.username == "usage_test_admin")).first()
    if not user:
        user = User(
            username="usage_test_admin",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token}


@pytest.fixture
def unprivileged_usage_user(db_session):
    role = db_session.scalars(select(Role).where(Role.name == "NoViewUsageRole")).first()
    if not role:
        role = Role(name="NoViewUsageRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    user = db_session.scalars(select(User).where(User.username == "usage_noview_user")).first()
    if not user:
        user = User(
            username="usage_noview_user",
            password_hash=hash_password("Password123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user, "token": token}


@pytest.fixture
def sample_computers_with_usage(db_session):
    # Computer A
    comp_a = db_session.get(Computer, 9101)
    if not comp_a:
        comp_a = Computer(
            id=9101,
            hostname="USAGE-PC-A",
            ip_address="192.168.1.191",
            mac_address="00:11:22:33:44:9A",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp_a)
        db_session.commit()
        db_session.refresh(comp_a)

    # Computer B
    comp_b = db_session.get(Computer, 9102)
    if not comp_b:
        comp_b = Computer(
            id=9102,
            hostname="USAGE-PC-B",
            ip_address="192.168.1.192",
            mac_address="00:11:22:33:44:9B",
            os_name="Windows",
            os_version="10 Enterprise",
        )
        db_session.add(comp_b)
        db_session.commit()
        db_session.refresh(comp_b)

    # Clean prior sessions
    db_session.query(UsageSession).filter(UsageSession.computer_id.in_([9101, 9102])).delete()
    db_session.commit()

    now = datetime.now(timezone.utc)

    # Seed 3 sessions for Computer A
    u_a1 = UsageSession(
        computer_id=9101,
        application_name="Code.exe",
        started_at=now - timedelta(hours=2),
        ended_at=now - timedelta(hours=1),
        duration_seconds=3600,
    )
    u_a2 = UsageSession(
        computer_id=9101,
        application_name="chrome.exe",
        started_at=now - timedelta(hours=4),
        ended_at=now - timedelta(hours=3),
        duration_seconds=3600,
    )
    u_a3 = UsageSession(
        computer_id=9101,
        application_name="PyCharm.exe",
        started_at=now - timedelta(hours=8),
        ended_at=now - timedelta(hours=6),
        duration_seconds=7200,
    )

    # Seed 1 session for Computer B
    u_b1 = UsageSession(
        computer_id=9102,
        application_name="notepad.exe",
        started_at=now - timedelta(hours=1),
        ended_at=now,
        duration_seconds=3600,
    )

    db_session.add_all([u_a1, u_a2, u_a3, u_b1])
    db_session.commit()

    return {"comp_a": comp_a, "comp_b": comp_b, "now": now}


def test_get_usage_unauthenticated(client):
    """
    Unauthenticated request to GET /api/clients/{id}/usage must return 401.
    """
    res = client.get("/api/clients/9101/usage")
    assert res.status_code == 401

    res2 = client.get("/api/usage/9101")
    assert res2.status_code == 401


def test_get_usage_unprivileged(client, unprivileged_usage_user):
    """
    User lacking VIEW_COMPUTERS permission must receive 403 Forbidden.
    """
    token = unprivileged_usage_user["token"]
    res = client.get(
        "/api/clients/9101/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_get_usage_nonexistent_computer(client, test_usage_user):
    """
    Request for non-existent computer must return 404 Not Found.
    """
    token = test_usage_user["token"]
    res = client.get(
        "/api/clients/999999/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Computer not found"


def test_get_usage_empty_list(client, db_session, test_usage_user):
    """
    Computer with no usage history recorded returns an empty list [].
    """
    comp_empty = db_session.get(Computer, 9103)
    if not comp_empty:
        comp_empty = Computer(
            id=9103,
            hostname="USAGE-PC-EMPTY",
            ip_address="192.168.1.193",
            mac_address="00:11:22:33:44:9C",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp_empty)
        db_session.commit()

    db_session.query(UsageSession).filter(UsageSession.computer_id == 9103).delete()
    db_session.commit()

    token = test_usage_user["token"]
    res = client.get(
        "/api/clients/9103/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_get_usage_success_and_deterministic_order(
    client, test_usage_user, sample_computers_with_usage
):
    """
    Returns usage sessions ordered deterministically by started_at desc.
    """
    token = test_usage_user["token"]
    res = client.get(
        "/api/clients/9101/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3

    # Expected order: Code.exe (2h ago) -> chrome.exe (4h ago) -> PyCharm.exe (8h ago)
    names = [item["application_name"] for item in data]
    assert names == ["Code.exe", "chrome.exe", "PyCharm.exe"]

    # Verify schema fields
    item = data[0]
    assert item["application_name"] == "Code.exe"
    assert item["duration_seconds"] == 3600
    assert item["computer_id"] == 9101
    assert "started_at" in item
    assert "ended_at" in item
    assert "created_at" in item


def test_get_usage_time_range_filter(
    client, test_usage_user, sample_computers_with_usage
):
    """
    Querying with start_time filters out older sessions.
    """
    token = test_usage_user["token"]
    now = sample_computers_with_usage["now"]

    # Filter sessions started within the last 3 hours (should only match Code.exe)
    start_filter = (now - timedelta(hours=3)).isoformat()
    res = client.get(
        f"/api/clients/9101/usage?start_time={start_filter}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["application_name"] == "Code.exe"


def test_get_usage_computer_isolation(
    client, test_usage_user, sample_computers_with_usage
):
    """
    Computer A's usage history does not leak into Computer B's response.
    """
    token = test_usage_user["token"]

    res_a = client.get(
        "/api/clients/9101/usage",
        headers={"Authorization": f"Bearer {token}"},
    )
    res_b = client.get(
        "/api/clients/9102/usage",
        headers={"Authorization": f"Bearer {token}"},
    )

    names_a = [item["application_name"] for item in res_a.json()]
    names_b = [item["application_name"] for item in res_b.json()]

    assert "notepad.exe" not in names_a
    assert "Code.exe" not in names_b
    assert names_b == ["notepad.exe"]


def test_get_usage_via_direct_route(
    client, test_usage_user, sample_computers_with_usage
):
    """
    GET /api/usage/{computer_id} returns identical data to GET /api/clients/{computer_id}/usage.
    """
    token = test_usage_user["token"]
    res = client.get(
        "/api/usage/9101",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    assert data[0]["application_name"] == "Code.exe"


def test_agent_usage_upload_and_deduplication(
    client, db_session, test_usage_user
):
    """
    Agent uploading POST /api/usage saves sessions and deduplicates repeated start times.
    """
    comp = db_session.get(Computer, 9105)
    if not comp:
        comp = Computer(
            id=9105,
            hostname="USAGE-AGENT-PC",
            ip_address="192.168.1.195",
            mac_address="00:11:22:33:44:9E",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp)
        db_session.commit()

    agent_cred = db_session.query(AgentCredential).filter_by(agent_id="agent-usage-9105").first()
    if not agent_cred:
        agent_cred = AgentCredential(
            agent_id="agent-usage-9105",
            secret_hash="fake-hash-usage",
            computer_id=comp.id,
            is_active=True,
        )
        db_session.add(agent_cred)
        db_session.commit()

    agent_token = create_agent_access_token({
        "sub": "agent-usage-9105",
        "computer_id": comp.id,
    })

    now = datetime.now(timezone.utc)
    t1 = (now - timedelta(minutes=30)).isoformat()
    t2 = now.isoformat()

    payload = {
        "sessions": [
            {
                "application_name": "blender.exe",
                "started_at": t1,
                "ended_at": t2,
                "duration_seconds": 1800,
            },
            # Duplicate start time for same app (agent re-delivery)
            {
                "application_name": "blender.exe",
                "started_at": t1,
                "ended_at": t2,
                "duration_seconds": 1800,
            },
        ]
    }

    upload_res = client.post(
        "/api/usage",
        headers={"Authorization": f"Bearer {agent_token}"},
        json=payload,
    )
    assert upload_res.status_code == 201
    uploaded_data = upload_res.json()
    assert len(uploaded_data) == 1

    # Verify query via dashboard user endpoint
    user_token = test_usage_user["token"]
    get_res = client.get(
        f"/api/clients/{comp.id}/usage",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert get_res.status_code == 200
    usage_data = get_res.json()
    assert len(usage_data) == 1
    assert usage_data[0]["application_name"] == "blender.exe"
    assert usage_data[0]["duration_seconds"] == 1800


def test_agent_usage_upload_unauthenticated(client):
    """
    Unauthenticated agent upload to POST /api/usage must return 401.
    """
    res = client.post(
        "/api/usage",
        json={"sessions": []},
    )
    assert res.status_code == 401
