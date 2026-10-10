from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from fastapi.testclient import TestClient

from app.auth import create_access_token, hash_password
from app.main import app
from app.models.computer import Computer
from app.models.notification import Notification, NotificationSeverity
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.system_metric import SystemMetric
from app.models.user import User
from app.services import alert_service


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

    user = db_session.scalars(select(User).where(User.username == "notif_test_admin")).first()
    if not user:
        user = User(
            username="notif_test_admin",
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

    user = db_session.scalars(select(User).where(User.username == "notif_unprivileged_user")).first()
    if not user:
        user = User(
            username="notif_unprivileged_user",
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
    comp = db_session.query(Computer).filter(Computer.hostname == "NOTIF-PC-01").first()
    if not comp:
        comp = Computer(
            hostname="NOTIF-PC-01",
            ip_address="192.168.1.81",
            mac_address="AA:99:88:77:66:55",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp)
        db_session.commit()
        db_session.refresh(comp)
    return comp


@pytest.fixture
def second_computer(db_session):
    comp = db_session.query(Computer).filter(Computer.hostname == "NOTIF-PC-02").first()
    if not comp:
        comp = Computer(
            hostname="NOTIF-PC-02",
            ip_address="192.168.1.82",
            mac_address="AA:99:88:77:66:56",
            os_name="Windows",
            os_version="11 Pro",
        )
        db_session.add(comp)
        db_session.commit()
        db_session.refresh(comp)
    return comp


def test_unauthenticated_notifications_rejected():
    client = TestClient(app)
    resp = client.get("/api/notifications")
    assert resp.status_code == 401


def test_unprivileged_user_forbidden(unprivileged_user):
    client = TestClient(app)
    resp = client.get(
        "/api/notifications",
        headers={"Authorization": f"Bearer {unprivileged_user['token']}"},
    )
    assert resp.status_code == 403


def test_notification_stats_and_empty_list(test_admin_user, db_session):
    db_session.query(Notification).delete()
    db_session.commit()

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    resp = client.get("/api/notifications", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []

    stats_resp = client.get("/api/notifications/stats", headers=headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats == {"total": 0, "unread": 0, "critical": 0, "warning": 0, "info": 0}


def test_get_notifications_with_computer_hostname(test_admin_user, sample_computer, db_session):
    db_session.query(Notification).filter(Notification.computer_id == sample_computer.id).delete()
    db_session.commit()

    notif = Notification(
        computer_id=sample_computer.id,
        category="cpu",
        severity=NotificationSeverity.critical,
        message="CPU usage critical: 95.2%",
        is_read=False,
    )
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}
    resp = client.get("/api/notifications", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 1

    matched = next((item for item in items if item["id"] == notif.id), None)
    assert matched is not None
    assert matched["computer_id"] == sample_computer.id
    assert matched["computer_hostname"] == sample_computer.hostname
    assert matched["category"] == "cpu"
    assert matched["severity"] == "critical"
    assert matched["message"] == "CPU usage critical: 95.2%"
    assert matched["is_read"] is False


def test_single_notification_detail_and_404(test_admin_user, sample_computer, db_session):
    notif = Notification(
        computer_id=sample_computer.id,
        category="disk",
        severity=NotificationSeverity.warning,
        message="Disk usage high: 84.5%",
        is_read=False,
    )
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    resp = client.get(f"/api/notifications/{notif.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == notif.id
    assert data["category"] == "disk"
    assert data["computer_hostname"] == sample_computer.hostname

    resp_404 = client.get("/api/notifications/999999", headers=headers)
    assert resp_404.status_code == 404


def test_mark_notification_read(test_admin_user, sample_computer, db_session):
    notif = Notification(
        computer_id=sample_computer.id,
        category="ram",
        severity=NotificationSeverity.warning,
        message="RAM usage high: 82.1%",
        is_read=False,
    )
    db_session.add(notif)
    db_session.commit()
    db_session.refresh(notif)

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    resp = client.patch(f"/api/notifications/{notif.id}/read", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_read"] is True

    # Idempotent call
    resp_again = client.patch(f"/api/notifications/{notif.id}/read", headers=headers)
    assert resp_again.status_code == 200
    assert resp_again.json()["is_read"] is True

    # Check 404 on non-existent
    resp_404 = client.patch("/api/notifications/999999/read", headers=headers)
    assert resp_404.status_code == 404


def test_mark_all_notifications_read(test_admin_user, sample_computer, db_session):
    db_session.query(Notification).filter(Notification.computer_id == sample_computer.id).delete()
    db_session.commit()

    n1 = Notification(computer_id=sample_computer.id, category="cpu", severity=NotificationSeverity.warning, message="CPU high", is_read=False)
    n2 = Notification(computer_id=sample_computer.id, category="ram", severity=NotificationSeverity.critical, message="RAM critical", is_read=False)
    db_session.add_all([n1, n2])
    db_session.commit()

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    resp = client.post(f"/api/notifications/read-all?computer_id={sample_computer.id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["updated_count"] >= 2

    # Verify unread count is 0 for this computer
    stats_resp = client.get(f"/api/notifications/stats?computer_id={sample_computer.id}", headers=headers)
    assert stats_resp.status_code == 200
    assert stats_resp.json()["unread"] == 0


def test_notification_filtering_and_search(test_admin_user, sample_computer, second_computer, db_session):
    db_session.query(Notification).filter(
        Notification.computer_id.in_([sample_computer.id, second_computer.id])
    ).delete()
    db_session.commit()

    n1 = Notification(computer_id=sample_computer.id, category="cpu", severity=NotificationSeverity.critical, message="Unusual CPU spike detected", is_read=False)
    n2 = Notification(computer_id=second_computer.id, category="offline", severity=NotificationSeverity.warning, message="Network interface disconnected", is_read=True)
    db_session.add_all([n1, n2])
    db_session.commit()

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    # Filter by category
    resp_cat = client.get("/api/notifications?category=cpu", headers=headers)
    assert resp_cat.status_code == 200
    items = resp_cat.json()
    assert all(item["category"] == "cpu" for item in items)

    # Filter by severity
    resp_sev = client.get("/api/notifications?severity=critical", headers=headers)
    assert resp_sev.status_code == 200
    items = resp_sev.json()
    assert all(item["severity"] == "critical" for item in items)

    # Filter by unread_only
    resp_unread = client.get("/api/notifications?unread_only=true", headers=headers)
    assert resp_unread.status_code == 200
    items = resp_unread.json()
    assert all(item["is_read"] is False for item in items)

    # Search by message text
    resp_search = client.get("/api/notifications?search=spike", headers=headers)
    assert resp_search.status_code == 200
    assert any("spike" in item["message"].lower() for item in resp_search.json())

    # Search by computer hostname
    resp_host = client.get(f"/api/notifications?search={sample_computer.hostname}", headers=headers)
    assert resp_host.status_code == 200
    assert any(item["computer_hostname"] == sample_computer.hostname for item in resp_host.json())


def test_computer_scoped_notifications(test_admin_user, sample_computer, second_computer, db_session):
    db_session.query(Notification).filter(
        Notification.computer_id.in_([sample_computer.id, second_computer.id])
    ).delete()
    db_session.commit()

    n1 = Notification(computer_id=sample_computer.id, category="cpu", severity=NotificationSeverity.critical, message="Scoped PC1 CPU", is_read=False)
    n2 = Notification(computer_id=second_computer.id, category="ram", severity=NotificationSeverity.warning, message="Scoped PC2 RAM", is_read=False)
    db_session.add_all([n1, n2])
    db_session.commit()

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    resp = client.get(f"/api/clients/{sample_computer.id}/notifications", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["message"] == "Scoped PC1 CPU"
    assert items[0]["computer_id"] == sample_computer.id

    # Non-existent computer returns 404
    resp_404 = client.get("/api/clients/999999/notifications", headers=headers)
    assert resp_404.status_code == 404


def test_delete_notification_and_clear_read(test_admin_user, sample_computer, db_session):
    n1 = Notification(computer_id=sample_computer.id, category="cpu", severity=NotificationSeverity.warning, message="To delete", is_read=False)
    n2 = Notification(computer_id=sample_computer.id, category="ram", severity=NotificationSeverity.info, message="Read to clear", is_read=True)
    db_session.add_all([n1, n2])
    db_session.commit()
    db_session.refresh(n1)
    db_session.refresh(n2)

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {test_admin_user['token']}"}

    # Delete single notification
    del_resp = client.delete(f"/api/notifications/{n1.id}", headers=headers)
    assert del_resp.status_code == 204

    # Verify 404 after deletion
    get_resp = client.get(f"/api/notifications/{n1.id}", headers=headers)
    assert get_resp.status_code == 404

    # Clear all read notifications
    clear_resp = client.delete(f"/api/notifications/clear-read?computer_id={sample_computer.id}", headers=headers)
    assert clear_resp.status_code == 200
    assert clear_resp.json()["deleted_count"] >= 1


@pytest.mark.anyio
async def test_alert_evaluation_and_debounce(sample_computer, db_session):
    db_session.query(Notification).filter(Notification.computer_id == sample_computer.id).delete()
    db_session.commit()

    # Metric breaching critical CPU (>90)
    metric = SystemMetric(
        computer_id=sample_computer.id,
        cpu_usage=95.0,
        ram_usage=50.0,
        disk_usage=40.0,
        network_sent=1.0,
        network_received=1.0,
    )

    await alert_service.evaluate_metric(db_session, sample_computer.id, metric)

    notifs = (
        db_session.query(Notification)
        .filter(Notification.computer_id == sample_computer.id, Notification.category == "cpu")
        .all()
    )
    assert len(notifs) == 1
    assert notifs[0].severity == NotificationSeverity.critical
    assert "95.0%" in notifs[0].message

    # Repeated evaluation within cooldown must not create duplicate
    await alert_service.evaluate_metric(db_session, sample_computer.id, metric)
    notifs_after = (
        db_session.query(Notification)
        .filter(Notification.computer_id == sample_computer.id, Notification.category == "cpu")
        .all()
    )
    assert len(notifs_after) == 1


@pytest.mark.anyio
async def test_notify_offline_event(sample_computer, db_session):
    db_session.query(Notification).filter(
        Notification.computer_id == sample_computer.id, Notification.category == "offline"
    ).delete()
    db_session.commit()

    await alert_service.notify_offline(db_session, sample_computer.id)

    offline_notifs = (
        db_session.query(Notification)
        .filter(Notification.computer_id == sample_computer.id, Notification.category == "offline")
        .all()
    )
    assert len(offline_notifs) == 1
    assert offline_notifs[0].severity == NotificationSeverity.warning
    assert "offline" in offline_notifs[0].message.lower()

    # Repeated notify within cooldown must not duplicate
    await alert_service.notify_offline(db_session, sample_computer.id)
    assert (
        db_session.query(Notification)
        .filter(Notification.computer_id == sample_computer.id, Notification.category == "offline")
        .count()
        == 1
    )
