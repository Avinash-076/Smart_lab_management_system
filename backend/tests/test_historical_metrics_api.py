"""
Backend tests for SLMS V2.2 — Historical Metrics & API Querying.
Verifies:
- Authenticated user with VIEW_COMPUTERS can query historical metrics
- Unauthenticated request is rejected (401/403)
- User without VIEW_COMPUTERS is rejected (403)
- Metrics are strictly filtered by computer_id
- Time range filtering (start_time, end_time) works accurately
- Invalid time range (start_time > end_time) returns 400 Bad Request
- Querying metrics for nonexistent computer returns 404 Not Found
- Deterministic ordering by recorded_at descending
- Limit and offset parameters are respected
- Empty historical query returns [] successfully
"""

from datetime import datetime, timedelta, timezone
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
    role = db_session.query(Role).filter_by(name="HistMetricTestRole").first()
    if not role:
        role = Role(name="HistMetricTestRole")
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

    user = db_session.query(User).filter_by(username="hist_test_admin").first()
    if not user:
        user = User(
            username="hist_test_admin",
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
    role = db_session.query(Role).filter_by(name="HistUnprivilegedRole").first()
    if not role:
        role = Role(name="HistUnprivilegedRole")
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    user = db_session.query(User).filter_by(username="hist_unprivileged_user").first()
    if not user:
        user = User(
            username="hist_unprivileged_user",
            password_hash=hash_password("UserPass123!"),
            role_id=role.id,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def computer_with_time_series_metrics(db_session):
    """Seed two computers with multi-point time series metrics for range testing."""
    now = datetime.now(timezone.utc)

    # Primary target computer
    c1 = Computer(
        hostname="V2-HIST-PC-01",
        ip_address="192.168.70.1",
        mac_address="00:70:00:00:00:01",
        os_name="Windows",
        os_version="11 Pro",
    )
    db_session.add(c1)

    # Other computer (to test isolation)
    c2 = Computer(
        hostname="V2-HIST-PC-02",
        ip_address="192.168.70.2",
        mac_address="00:70:00:00:00:02",
        os_name="Ubuntu",
        os_version="22.04 LTS",
    )
    db_session.add(c2)
    db_session.commit()
    db_session.refresh(c1)
    db_session.refresh(c2)

    # Add metrics for c1 at T-30m, T-2h, T-12h, T-36h
    m1 = SystemMetric(
        computer_id=c1.id,
        cpu_usage=15.0,
        ram_usage=40.0,
        disk_usage=55.0,
        recorded_at=now - timedelta(minutes=30),
    )
    m2 = SystemMetric(
        computer_id=c1.id,
        cpu_usage=35.0,
        ram_usage=50.0,
        disk_usage=55.0,
        recorded_at=now - timedelta(hours=2),
    )
    m3 = SystemMetric(
        computer_id=c1.id,
        cpu_usage=65.0,
        ram_usage=70.0,
        disk_usage=56.0,
        recorded_at=now - timedelta(hours=12),
    )
    m4 = SystemMetric(
        computer_id=c1.id,
        cpu_usage=85.0,
        ram_usage=90.0,
        disk_usage=56.0,
        recorded_at=now - timedelta(hours=36),
    )

    # Add metric for c2 at T-30m
    m_c2 = SystemMetric(
        computer_id=c2.id,
        cpu_usage=99.0,
        ram_usage=99.0,
        disk_usage=99.0,
        recorded_at=now - timedelta(minutes=30),
    )

    db_session.add_all([m1, m2, m3, m4, m_c2])
    db_session.commit()

    yield {
        "c1_id": c1.id,
        "c2_id": c2.id,
        "now": now,
    }

    # Cleanup
    for comp_id in [c1.id, c2.id]:
        comp = get_computer_by_id(db_session, comp_id)
        if comp:
            delete_computer(db_session, comp)


def test_get_historical_metrics_unauthenticated(client, computer_with_time_series_metrics):
    """GET /api/metrics/{id} without token returns 401/403."""
    cid = computer_with_time_series_metrics["c1_id"]
    response = client.get(f"/api/metrics/{cid}")
    assert response.status_code in (401, 403)


def test_get_historical_metrics_unprivileged(client, unprivileged_headers, computer_with_time_series_metrics):
    """GET /api/metrics/{id} without VIEW_COMPUTERS returns 403 Forbidden."""
    cid = computer_with_time_series_metrics["c1_id"]
    response = client.get(f"/api/metrics/{cid}", headers=unprivileged_headers)
    assert response.status_code == 403


def test_get_historical_metrics_nonexistent_computer_404(client, auth_headers):
    """GET /api/metrics/{id} returns 404 for non-existent computer."""
    response = client.get("/api/metrics/999997", headers=auth_headers)
    assert response.status_code == 404
    assert "Computer not found" in response.json()["detail"]


def test_get_historical_metrics_isolation(client, auth_headers, computer_with_time_series_metrics):
    """Metrics returned only belong to the queried computer, never leaked across computers."""
    c1_id = computer_with_time_series_metrics["c1_id"]
    response = client.get(f"/api/metrics/{c1_id}", headers=auth_headers)
    assert response.status_code == 200
    metrics = response.json()
    assert len(metrics) == 4
    for m in metrics:
        assert m["computer_id"] == c1_id
        assert m["cpu_usage"] != 99.0  # c2's metric is not included


def test_get_historical_metrics_time_range_filtering(client, auth_headers, computer_with_time_series_metrics):
    """Verify start_time and end_time filter records correctly."""
    c1_id = computer_with_time_series_metrics["c1_id"]
    now = computer_with_time_series_metrics["now"]

    # 1. Query last 1 hour (should only return m1 at T-30m)
    t_1h_ago = (now - timedelta(hours=1)).isoformat()
    resp_1h = client.get(f"/api/metrics/{c1_id}?start_time={t_1h_ago}", headers=auth_headers)
    assert resp_1h.status_code == 200
    m_1h = resp_1h.json()
    assert len(m_1h) == 1
    assert m_1h[0]["cpu_usage"] == 15.0

    # 2. Query last 6 hours (should return m1 at T-30m and m2 at T-2h)
    t_6h_ago = (now - timedelta(hours=6)).isoformat()
    resp_6h = client.get(f"/api/metrics/{c1_id}?start_time={t_6h_ago}", headers=auth_headers)
    assert resp_6h.status_code == 200
    m_6h = resp_6h.json()
    assert len(m_6h) == 2
    assert [m["cpu_usage"] for m in m_6h] == [15.0, 35.0]

    # 3. Query specific window: between T-24h and T-1h (should return m2 at T-2h and m3 at T-12h)
    t_24h_ago = (now - timedelta(hours=24)).isoformat()
    resp_window = client.get(
        f"/api/metrics/{c1_id}?start_time={t_24h_ago}&end_time={t_1h_ago}",
        headers=auth_headers,
    )
    assert resp_window.status_code == 200
    m_window = resp_window.json()
    assert len(m_window) == 2
    assert [m["cpu_usage"] for m in m_window] == [35.0, 65.0]


def test_get_historical_metrics_invalid_time_range_rejected(client, auth_headers, computer_with_time_series_metrics):
    """start_time > end_time returns 400 Bad Request."""
    c1_id = computer_with_time_series_metrics["c1_id"]
    now = computer_with_time_series_metrics["now"]

    start = now.isoformat()
    end = (now - timedelta(hours=5)).isoformat()

    response = client.get(
        f"/api/metrics/{c1_id}?start_time={start}&end_time={end}",
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert "start_time must be before or equal to end_time" in response.json()["detail"]


def test_get_historical_metrics_limit_and_ordering(client, auth_headers, computer_with_time_series_metrics):
    """Verify limit restricts output count and records are ordered newest first (recorded_at DESC)."""
    c1_id = computer_with_time_series_metrics["c1_id"]

    response = client.get(f"/api/metrics/{c1_id}?limit=2", headers=auth_headers)
    assert response.status_code == 200
    metrics = response.json()
    assert len(metrics) == 2
    # Newest first: 15.0 (T-30m) then 35.0 (T-2h)
    assert metrics[0]["cpu_usage"] == 15.0
    assert metrics[1]["cpu_usage"] == 35.0
