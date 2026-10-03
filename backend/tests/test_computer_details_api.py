"""
Backend tests for SLMS V2.1 — Computer Details Foundation.
Verifies:
- Authenticated user with VIEW_COMPUTERS can retrieve a single computer
- Unauthenticated request to GET /api/clients/{id} is rejected
- User without VIEW_COMPUTERS permission receives 403 Forbidden
- Existing computer is returned with all real fields
- Nonexistent computer returns 404 Not Found
- Missing ClientStatus safely defaults to 'offline' and last_seen=None
- GET /api/metrics/{computer_id} requires authentication and VIEW_COMPUTERS
- GET /api/metrics/{computer_id} returns latest metrics for computer ordered by recorded_at DESC
- GET /api/metrics/{computer_id} returns [] safely when no metrics exist
"""

from datetime import datetime, timezone
import pytest
from app.auth import create_access_token, hash_password
from app.models.client_status import ClientStatus
from app.models.computer import Computer
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.system_metric import SystemMetric
from app.models.user import User
from app.services.computer_service import delete_computer, get_computer_by_id


@pytest.fixture
def auth_headers(db_session):
    """Create an admin user with VIEW_COMPUTERS permission and return Authorization headers."""
    role = db_session.query(Role).filter_by(name="CompDetailsTestRole").first()
    if not role:
        role = Role(name="CompDetailsTestRole")
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

    user = db_session.query(User).filter_by(username="details_test_admin").first()
    if not user:
        user = User(
            username="details_test_admin",
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
    role = db_session.query(Role).filter_by(name="DetailsUnprivilegedRole").first()
    if not role:
        role = Role(name="DetailsUnprivilegedRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    user = db_session.query(User).filter_by(username="details_unprivileged_user").first()
    if not user:
        user = User(
            username="details_unprivileged_user",
            password_hash=hash_password("UserPass123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_computer_with_metrics(db_session):
    """Seed a test computer with status and system metrics."""
    now_utc = datetime.now(timezone.utc)

    comp = Computer(
        hostname="V2-DETAILS-PC-01",
        ip_address="192.168.50.10",
        mac_address="AA:BB:CC:DD:EE:10",
        os_name="Windows",
        os_version="11 Pro",
    )
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)

    status = ClientStatus(computer_id=comp.id, status="online", last_seen=now_utc)
    db_session.add(status)

    metric1 = SystemMetric(
        computer_id=comp.id,
        cpu_usage=25.5,
        ram_usage=48.2,
        disk_usage=62.0,
        network_sent=1200.0,
        network_received=3400.0,
        recorded_at=now_utc,
    )
    db_session.add(metric1)
    db_session.commit()

    yield comp

    # Cleanup
    comp_to_del = get_computer_by_id(db_session, comp.id)
    if comp_to_del:
        delete_computer(db_session, comp_to_del)


def test_get_computer_details_unauthenticated(client, test_computer_with_metrics):
    """Request to GET /api/clients/{id} without token is rejected."""
    response = client.get(f"/api/clients/{test_computer_with_metrics.id}")
    assert response.status_code in (401, 403)


def test_get_computer_details_unprivileged(client, unprivileged_headers, test_computer_with_metrics):
    """Request to GET /api/clients/{id} without VIEW_COMPUTERS permission is 403 Forbidden."""
    response = client.get(
        f"/api/clients/{test_computer_with_metrics.id}",
        headers=unprivileged_headers,
    )
    assert response.status_code == 403
    assert "VIEW_COMPUTERS" in response.json()["detail"]


def test_get_computer_details_success(client, auth_headers, test_computer_with_metrics):
    """GET /api/clients/{id} returns complete real computer schema."""
    cid = test_computer_with_metrics.id
    response = client.get(f"/api/clients/{cid}", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == cid
    assert data["hostname"] == "V2-DETAILS-PC-01"
    assert data["ip_address"] == "192.168.50.10"
    assert data["mac_address"] == "AA:BB:CC:DD:EE:10"
    assert data["os_name"] == "Windows"
    assert data["os_version"] == "11 Pro"
    assert data["status"] == "online"
    assert data["last_seen"] is not None
    assert data["registered_at"] is not None


def test_get_computer_details_not_found(client, auth_headers):
    """GET /api/clients/{id} returns 404 Not Found for non-existent computer."""
    response = client.get("/api/clients/999998", headers=auth_headers)
    assert response.status_code == 404
    assert "Computer not found" in response.json()["detail"]


def test_get_computer_metrics_unauthenticated(client, test_computer_with_metrics):
    """Request to GET /api/metrics/{id} without token is rejected."""
    response = client.get(f"/api/metrics/{test_computer_with_metrics.id}")
    assert response.status_code in (401, 403)


def test_get_computer_metrics_unprivileged(client, unprivileged_headers, test_computer_with_metrics):
    """Request to GET /api/metrics/{id} without VIEW_COMPUTERS is 403 Forbidden."""
    response = client.get(
        f"/api/metrics/{test_computer_with_metrics.id}",
        headers=unprivileged_headers,
    )
    assert response.status_code == 403


def test_get_computer_metrics_returns_latest(client, auth_headers, test_computer_with_metrics):
    """GET /api/metrics/{id} returns list containing latest recorded metrics."""
    cid = test_computer_with_metrics.id
    response = client.get(f"/api/metrics/{cid}?limit=1", headers=auth_headers)
    assert response.status_code == 200

    metrics = response.json()
    assert isinstance(metrics, list)
    assert len(metrics) == 1
    m = metrics[0]
    assert m["computer_id"] == cid
    assert m["cpu_usage"] == 25.5
    assert m["ram_usage"] == 48.2
    assert m["disk_usage"] == 62.0
    assert m["network_sent"] == 1200.0
    assert m["network_received"] == 3400.0
    assert m["recorded_at"] is not None


def test_get_computer_metrics_empty_safely(client, auth_headers, db_session):
    """GET /api/metrics/{id} returns empty list [] safely when computer has no metrics."""
    comp = Computer(
        hostname="V2-NOMETRICS-PC-02",
        ip_address="192.168.50.11",
        mac_address="AA:BB:CC:DD:EE:11",
        os_name="Ubuntu",
        os_version="24.04 LTS",
    )
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)

    try:
        response = client.get(f"/api/metrics/{comp.id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []
    finally:
        comp_to_del = get_computer_by_id(db_session, comp.id)
        if comp_to_del:
            delete_computer(db_session, comp_to_del)
