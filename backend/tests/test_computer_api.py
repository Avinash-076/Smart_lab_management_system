"""
Backend tests for SLMS Computer API / Data Contract (Phase 2).
Verifies:
- GET /api/clients requires authentication and VIEW_COMPUTERS permission
- GET /api/clients response schema (id, hostname, ip_address, mac_address, os_name, os_version, status, last_seen, registered_at)
- Proper serialization of online computers with last_seen
- Proper serialization of offline computers
- Safe handling of computers without ClientStatus records (defaults to 'offline', last_seen=None, no 500 error)
- Multiple computers returned properly
- Empty database behavior
- Status filtering (?status=online, ?status=offline)
- GET /api/clients/{id} single computer retrieval and 404 for non-existent
"""

from datetime import datetime, timezone
import pytest
from app.auth import create_access_token, hash_password
from app.models.client_status import ClientStatus
from app.models.computer import Computer
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.services.computer_service import delete_computer, get_computer_by_id


@pytest.fixture
def auth_headers(db_session):
    """Create an admin user with VIEW_COMPUTERS permission and return Authorization headers."""
    role = db_session.query(Role).filter_by(name="CompTestAdminRole").first()
    if not role:
        role = Role(name="CompTestAdminRole")
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

    user = db_session.query(User).filter_by(username="comp_test_admin").first()
    if not user:
        user = User(
            username="comp_test_admin",
            password_hash=hash_password("AdminPass123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def unprivileged_headers(db_session):
    """Create a user whose role does NOT have VIEW_COMPUTERS permission."""
    role = db_session.query(Role).filter_by(name="UnprivilegedRole").first()
    if not role:
        role = Role(name="UnprivilegedRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    user = db_session.query(User).filter_by(username="unprivileged_user").first()
    if not user:
        user = User(
            username="unprivileged_user",
            password_hash=hash_password("UserPass123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_computers(db_session):
    """Seed distinct test computers (online, offline, and missing status) and clean them up after."""
    created_ids = []
    now_utc = datetime.now(timezone.utc)

    # 1. Online computer
    c1 = Computer(
        hostname="PH2-PC-01-ONLINE",
        ip_address="192.168.20.1",
        mac_address="00:11:22:33:44:01",
        os_name="Windows",
        os_version="11 Pro",
    )
    db_session.add(c1)
    db_session.commit()
    db_session.refresh(c1)
    created_ids.append(c1.id)

    s1 = ClientStatus(computer_id=c1.id, status="online", last_seen=now_utc)
    db_session.add(s1)

    # 2. Offline computer
    c2 = Computer(
        hostname="PH2-PC-02-OFFLINE",
        ip_address="192.168.20.2",
        mac_address="00:11:22:33:44:02",
        os_name="Windows",
        os_version="10 Pro",
    )
    db_session.add(c2)
    db_session.commit()
    db_session.refresh(c2)
    created_ids.append(c2.id)

    s2 = ClientStatus(computer_id=c2.id, status="offline", last_seen=now_utc)
    db_session.add(s2)

    # 3. Computer without ClientStatus record
    c3 = Computer(
        hostname="PH2-PC-03-NOSTATUS",
        ip_address="192.168.20.3",
        mac_address="00:11:22:33:44:03",
        os_name="Ubuntu",
        os_version="22.04 LTS",
    )
    db_session.add(c3)
    db_session.commit()
    db_session.refresh(c3)
    created_ids.append(c3.id)

    db_session.commit()

    yield {
        "online_id": c1.id,
        "offline_id": c2.id,
        "no_status_id": c3.id,
    }

    # Cleanup seeded computers safely
    for cid in created_ids:
        comp = get_computer_by_id(db_session, cid)
        if comp:
            delete_computer(db_session, comp)


def test_get_computers_unauthenticated_rejected(client):
    """Request to GET /api/clients without token is rejected."""
    response = client.get("/api/clients")
    assert response.status_code in (401, 403)


def test_get_computers_without_permission_forbidden(client, unprivileged_headers):
    """User without VIEW_COMPUTERS permission receives 403 Forbidden."""
    response = client.get("/api/clients", headers=unprivileged_headers)
    assert response.status_code == 403
    assert "permission: VIEW_COMPUTERS" in response.json()["detail"]


def test_get_computers_returns_valid_list(client, auth_headers):
    """GET /api/clients returns 200 OK and a list."""
    response = client.get("/api/clients", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_computers_contract_and_status(client, auth_headers, sample_computers):
    """Verify GET /api/clients returns the complete schema with real status and last_seen."""
    response = client.get("/api/clients", headers=auth_headers)
    assert response.status_code == 200
    computers = response.json()
    assert len(computers) >= 3

    comp_map = {c["id"]: c for c in computers}

    # 1. Verify online computer contract
    c1 = comp_map[sample_computers["online_id"]]
    assert c1["hostname"] == "PH2-PC-01-ONLINE"
    assert c1["ip_address"] == "192.168.20.1"
    assert c1["mac_address"] == "00:11:22:33:44:01"
    assert c1["os_name"] == "Windows"
    assert c1["os_version"] == "11 Pro"
    assert c1["status"] == "online"
    assert c1["last_seen"] is not None
    assert c1["registered_at"] is not None

    # 2. Verify offline computer contract
    c2 = comp_map[sample_computers["offline_id"]]
    assert c2["hostname"] == "PH2-PC-02-OFFLINE"
    assert c2["status"] == "offline"
    assert c2["last_seen"] is not None

    # 3. Verify missing ClientStatus record safely defaults to offline without 500 error
    c3 = comp_map[sample_computers["no_status_id"]]
    assert c3["hostname"] == "PH2-PC-03-NOSTATUS"
    assert c3["status"] == "offline"
    assert c3["last_seen"] is None


def test_get_computers_filter_by_status(client, auth_headers, sample_computers):
    """Verify ?status=online and ?status=offline query params filter results correctly."""
    # Query online only
    response_online = client.get("/api/clients?status=online", headers=auth_headers)
    assert response_online.status_code == 200
    online_ids = [c["id"] for c in response_online.json()]
    assert sample_computers["online_id"] in online_ids
    assert sample_computers["offline_id"] not in online_ids

    # Query offline only
    response_offline = client.get("/api/clients?status=offline", headers=auth_headers)
    assert response_offline.status_code == 200
    offline_ids = [c["id"] for c in response_offline.json()]
    assert sample_computers["offline_id"] in offline_ids
    assert sample_computers["online_id"] not in offline_ids


def test_get_single_computer(client, auth_headers, sample_computers):
    """GET /api/clients/{id} returns full computer data, or 404 for non-existent."""
    cid = sample_computers["online_id"]
    response = client.get(f"/api/clients/{cid}", headers=auth_headers)
    assert response.status_code == 200
    comp = response.json()
    assert comp["id"] == cid
    assert comp["hostname"] == "PH2-PC-01-ONLINE"
    assert comp["status"] == "online"
    assert comp["last_seen"] is not None

    # 404 for non-existent computer
    response_404 = client.get("/api/clients/999999", headers=auth_headers)
    assert response_404.status_code == 404
    assert "Computer not found" in response_404.json()["detail"]
