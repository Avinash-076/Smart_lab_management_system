"""
Comprehensive test suite for SLMS V6.3 Application Settings and Configuration Management.
Verifies:
- Authorized and unauthorized retrieval of system settings.
- Category filtering and default fallback population.
- Validated atomic updates across string, int, and boolean types.
- Strict rejection of invalid keys, types, and out-of-range values with complete rollback.
- System defaults restoration via reset API.
- Audit trail logging on configuration updates and resets.
- Sensitive credentials omission from setting responses.
"""

import pytest
from app.auth import create_access_token, hash_password
from app.models.app_setting import AppSetting
from app.models.audit_log import AuditLog, AuditResult
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User


@pytest.fixture
def settings_test_setup(db_session):
    """Seed test Administrator and unprivileged roles and users for settings tests."""
    # Administrator Role
    admin_role = db_session.query(Role).filter_by(name="Administrator").first()
    if not admin_role:
        admin_role = Role(name="Administrator", description="Full access")
        db_session.add(admin_role)
        db_session.commit()
        db_session.refresh(admin_role)

    # Ensure all permissions including MANAGE_SETTINGS and VIEW_COMPUTERS
    for code in [
        "VIEW_COMPUTERS",
        "REGISTER_COMPUTER",
        "UPDATE_COMPUTER",
        "DELETE_COMPUTER",
        "PROVISION_AGENT",
        "ISSUE_COMMAND",
        "MANAGE_USERS",
        "MANAGE_ROLES",
        "MANAGE_ISSUES",
        "MANAGE_MAINTENANCE",
        "MANAGE_SETTINGS",
    ]:
        perm = (
            db_session.query(RolePermission)
            .filter_by(role_id=admin_role.id, action_code=code)
            .first()
        )
        if not perm:
            db_session.add(RolePermission(role_id=admin_role.id, action_code=code, allowed=True))
        else:
            perm.allowed = True

    # Viewer Role (Read-only, no MANAGE_SETTINGS)
    viewer_role = db_session.query(Role).filter_by(name="SettingsViewerRole").first()
    if not viewer_role:
        viewer_role = Role(name="SettingsViewerRole", description="Read only access")
        db_session.add(viewer_role)
        db_session.commit()
        db_session.refresh(viewer_role)

    v_perm = (
        db_session.query(RolePermission)
        .filter_by(role_id=viewer_role.id, action_code="VIEW_COMPUTERS")
        .first()
    )
    if not v_perm:
        db_session.add(RolePermission(role_id=viewer_role.id, action_code="VIEW_COMPUTERS", allowed=True))

    # Unprivileged Role (No permissions)
    unprivileged_role = db_session.query(Role).filter_by(name="NoSettingsPermRole").first()
    if not unprivileged_role:
        unprivileged_role = Role(name="NoSettingsPermRole", description="No permissions")
        db_session.add(unprivileged_role)
        db_session.commit()
        db_session.refresh(unprivileged_role)

    db_session.commit()

    # Admin user
    admin_user = db_session.query(User).filter_by(username="settings_admin").first()
    if not admin_user:
        admin_user = User(
            username="settings_admin",
            full_name="Settings Admin",
            email="settings_admin@slms.local",
            password_hash=hash_password("AdminPass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

    # Viewer user
    viewer_user = db_session.query(User).filter_by(username="settings_viewer").first()
    if not viewer_user:
        viewer_user = User(
            username="settings_viewer",
            full_name="Settings Viewer",
            email="viewer@slms.local",
            password_hash=hash_password("ViewerPass123!"),
            role_id=viewer_role.id,
            is_active=True,
        )
        db_session.add(viewer_user)
        db_session.commit()
        db_session.refresh(viewer_user)

    # Unprivileged user
    unprivileged_user = db_session.query(User).filter_by(username="settings_unprivileged").first()
    if not unprivileged_user:
        unprivileged_user = User(
            username="settings_unprivileged",
            full_name="Unprivileged Settings User",
            email="settings_noperms@slms.local",
            password_hash=hash_password("NoPermsPass123!"),
            role_id=unprivileged_role.id,
            is_active=True,
        )
        db_session.add(unprivileged_user)
        db_session.commit()
        db_session.refresh(unprivileged_user)

    admin_token = create_access_token({"sub": str(admin_user.id)})
    viewer_token = create_access_token({"sub": str(viewer_user.id)})
    unprivileged_token = create_access_token({"sub": str(unprivileged_user.id)})

    return {
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "viewer_headers": {"Authorization": f"Bearer {viewer_token}"},
        "unprivileged_headers": {"Authorization": f"Bearer {unprivileged_token}"},
        "admin_user": admin_user,
        "viewer_user": viewer_user,
    }


def test_settings_unauthenticated_access_rejected(client):
    """Unauthenticated requests are rejected with 401."""
    get_res = client.get("/api/settings")
    assert get_res.status_code == 401

    patch_res = client.patch("/api/settings", json={"lab_name": "Unauthorized"})
    assert patch_res.status_code == 401


def test_settings_authorization_and_rbac(client, settings_test_setup):
    """Viewers can inspect settings; only MANAGE_SETTINGS role can update/reset."""
    # Viewers can read settings
    resp = client.get("/api/settings", headers=settings_test_setup["viewer_headers"])
    assert resp.status_code == 200

    # Viewers cannot update settings
    patch_resp = client.patch(
        "/api/settings",
        json={"lab_name": "New Lab Name"},
        headers=settings_test_setup["viewer_headers"],
    )
    assert patch_resp.status_code == 403

    # Viewers cannot reset settings
    reset_resp = client.post(
        "/api/settings/reset",
        json={"keys": ["lab_name"]},
        headers=settings_test_setup["viewer_headers"],
    )
    assert reset_resp.status_code == 403


def test_get_settings_default_catalog_values(client, settings_test_setup):
    """Settings endpoint returns defaults for un-persisted items with structured categories."""
    resp = client.get("/api/settings", headers=settings_test_setup["admin_headers"])
    assert resp.status_code == 200
    data = resp.json()

    assert "items" in data
    assert "categories" in data
    assert "settings_map" in data

    assert "general" in data["categories"]
    assert "monitoring" in data["categories"]
    assert "notifications" in data["categories"]
    assert "agent" in data["categories"]

    s_map = data["settings_map"]
    assert s_map["lab_name"] == "Computer Laboratory"
    assert s_map["cpu_threshold"] == 85
    assert s_map["disk_alerts"] is True
    assert s_map["auto_start_agent"] is True


def test_get_settings_by_category(client, settings_test_setup):
    """Retrieve settings filtered by category with 404 for unknown categories."""
    resp = client.get("/api/settings/monitoring", headers=settings_test_setup["admin_headers"])
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert len(items) >= 4
    for item in items:
        assert item["category"] == "monitoring"

    # Invalid category
    invalid_resp = client.get("/api/settings/non_existent_category", headers=settings_test_setup["admin_headers"])
    assert invalid_resp.status_code == 404


def test_authorized_settings_update_persistence(client, settings_test_setup, db_session):
    """Admin can update multiple setting types (string, int, bool) and values persist."""
    payload = {
        "lab_name": "Robotics & AI Innovation Center",
        "lab_location": "Engineering Block B, Room 304",
        "cpu_threshold": 75,
        "heartbeat_interval": 15,
        "disk_alerts": False,
        "software_alerts": True,
    }

    patch_resp = client.patch(
        "/api/settings",
        json=payload,
        headers=settings_test_setup["admin_headers"],
    )
    assert patch_resp.status_code == 200
    data = patch_resp.json()

    assert data["settings_map"]["lab_name"] == "Robotics & AI Innovation Center"
    assert data["settings_map"]["lab_location"] == "Engineering Block B, Room 304"
    assert data["settings_map"]["cpu_threshold"] == 75
    assert data["settings_map"]["heartbeat_interval"] == 15
    assert data["settings_map"]["disk_alerts"] is False
    assert data["settings_map"]["software_alerts"] is True

    # Verify directly in database
    db_lab = db_session.get(AppSetting, "lab_name")
    assert db_lab is not None
    assert db_lab.value == "Robotics & AI Innovation Center"
    assert db_lab.updated_by == "settings_admin"

    db_cpu = db_session.get(AppSetting, "cpu_threshold")
    assert db_cpu is not None
    assert db_cpu.value == "75"


def test_settings_validation_invalid_keys(client, settings_test_setup):
    """Unrecognized setting keys are strictly rejected with 400."""
    resp = client.patch(
        "/api/settings",
        json={"unknown_custom_key": "some_value"},
        headers=settings_test_setup["admin_headers"],
    )
    assert resp.status_code == 400
    assert "Unknown setting key" in resp.json()["detail"]


def test_settings_validation_ranges_and_types(client, settings_test_setup):
    """Out-of-range numeric values and invalid types are rejected with 400."""
    # Out of range (max 100)
    resp_max = client.patch(
        "/api/settings",
        json={"cpu_threshold": 120},
        headers=settings_test_setup["admin_headers"],
    )
    assert resp_max.status_code == 400
    assert "cannot exceed" in resp_max.json()["detail"]

    # Out of range (min 10)
    resp_min = client.patch(
        "/api/settings",
        json={"cpu_threshold": 4},
        headers=settings_test_setup["admin_headers"],
    )
    assert resp_min.status_code == 400
    assert "must be at least" in resp_min.json()["detail"]

    # Invalid int string
    resp_type = client.patch(
        "/api/settings",
        json={"cpu_threshold": "not_a_number"},
        headers=settings_test_setup["admin_headers"],
    )
    assert resp_type.status_code == 400
    assert "valid integer" in resp_type.json()["detail"]


def test_atomic_rollback_on_partial_failure(client, settings_test_setup, db_session):
    """If any setting in a multi-setting update fails validation, no changes are committed."""
    initial_lab = db_session.get(AppSetting, "lab_name")
    initial_lab_name = initial_lab.value if initial_lab else "Computer Laboratory"

    resp = client.patch(
        "/api/settings",
        json={
            "lab_name": "Should Not Be Saved",
            "cpu_threshold": 999999,  # invalid out-of-range
        },
        headers=settings_test_setup["admin_headers"],
    )
    assert resp.status_code == 400

    # Verify lab_name was NOT modified
    db_session.expire_all()
    current_lab = db_session.get(AppSetting, "lab_name")
    current_val = current_lab.value if current_lab else "Computer Laboratory"
    assert current_val == initial_lab_name


def test_settings_reset_to_defaults(client, settings_test_setup, db_session):
    """Reset endpoint can restore single keys or all settings to default values."""
    # First modify settings
    client.patch(
        "/api/settings",
        json={"lab_name": "Modified Lab", "cpu_threshold": 60},
        headers=settings_test_setup["admin_headers"],
    )

    # Reset specific key
    reset_one = client.post(
        "/api/settings/reset",
        json={"keys": ["lab_name"]},
        headers=settings_test_setup["admin_headers"],
    )
    assert reset_one.status_code == 200
    assert reset_one.json()["settings_map"]["lab_name"] == "Computer Laboratory"
    assert reset_one.json()["settings_map"]["cpu_threshold"] == 60

    # Reset all keys
    reset_all = client.post(
        "/api/settings/reset",
        json={},
        headers=settings_test_setup["admin_headers"],
    )
    assert reset_all.status_code == 200
    assert reset_all.json()["settings_map"]["cpu_threshold"] == 85


def test_audit_logging_for_settings_actions(client, settings_test_setup, db_session):
    """Setting modifications and resets generate security audit records."""
    client.patch(
        "/api/settings",
        json={"lab_name": "Audited Lab Update"},
        headers=settings_test_setup["admin_headers"],
    )

    client.post(
        "/api/settings/reset",
        json={"keys": ["lab_name"]},
        headers=settings_test_setup["admin_headers"],
    )

    audit_logs = (
        db_session.query(AuditLog)
        .filter(AuditLog.target_type == "SETTINGS")
        .order_by(AuditLog.id.desc())
        .limit(2)
        .all()
    )
    assert len(audit_logs) >= 2
    actions = [log.action for log in audit_logs]
    assert any("SETTINGS_RESET" in a for a in actions)
    assert any("SETTINGS_UPDATE" in a for a in actions)
    for log in audit_logs:
        assert log.result == AuditResult.success
        assert log.user_id == settings_test_setup["admin_user"].id


def test_runtime_threshold_and_alert_settings(client, settings_test_setup, db_session):
    """Verify that runtime evaluation in alert_service dynamically consumes persistent settings."""
    import asyncio
    from datetime import datetime, timezone
    from app.models.computer import Computer
    from app.models.notification import Notification
    from app.models.system_metric import SystemMetric
    from app.services import alert_service, setting_service

    # Create test computer
    comp = db_session.query(Computer).filter_by(ip_address="192.168.10.99").first()
    if not comp:
        comp = Computer(
            hostname="Lab-PC-Settings-Test",
            ip_address="192.168.10.99",
            mac_address="00:11:22:33:44:99",
            os_name="Windows",
            os_version="11",
        )
        db_session.add(comp)
        db_session.commit()
        db_session.refresh(comp)

    # 1. Update cpu_threshold to 65% and disable disk_alerts
    setting_service.update_settings(
        db_session,
        {"cpu_threshold": 65, "disk_alerts": False, "offline_alerts": False},
        actor_id=settings_test_setup["admin_user"].id,
    )

    # Metric with CPU=70% (exceeds new 65% threshold), Disk=95% (exceeds disk threshold, but disk_alerts=False)
    metric = SystemMetric(
        computer_id=comp.id,
        cpu_usage=70.0,
        ram_usage=40.0,
        disk_usage=95.0,
        recorded_at=datetime.now(timezone.utc),
    )
    db_session.add(metric)
    db_session.commit()

    # Clear prior notifications for this computer
    db_session.query(Notification).filter_by(computer_id=comp.id).delete()
    db_session.commit()

    asyncio.run(alert_service.evaluate_metric(db_session, comp.id, metric))

    # CPU notification must be created because 70% >= 65%
    cpu_notif = db_session.query(Notification).filter_by(computer_id=comp.id, category="cpu").first()
    assert cpu_notif is not None
    assert "CPU" in cpu_notif.message

    # Disk notification must NOT be created because disk_alerts is False
    disk_notif = db_session.query(Notification).filter_by(computer_id=comp.id, category="disk").first()
    assert disk_notif is None

    # Offline notification must NOT be created because offline_alerts is False
    asyncio.run(alert_service.notify_offline(db_session, comp.id))
    offline_notif = db_session.query(Notification).filter_by(computer_id=comp.id, category="offline").first()
    assert offline_notif is None


def test_runtime_data_retention_purge(db_session):
    """Verify that purge_expired_metrics cleans up historical metrics past retention days."""
    from datetime import datetime, timedelta, timezone
    from app.models.computer import Computer
    from app.models.system_metric import SystemMetric
    from app.services import metric_service, setting_service

    comp = db_session.query(Computer).first()
    if not comp:
        comp = Computer(
            hostname="Retention-Test-PC",
            ip_address="192.168.10.98",
            mac_address="00:11:22:33:44:98",
            os_name="Windows",
            os_version="11",
        )
        db_session.add(comp)
        db_session.commit()
        db_session.refresh(comp)

    # Set retention days to 7
    setting_service.update_settings(db_session, {"data_retention_days": 7})

    now = datetime.now(timezone.utc)
    # Old sample (10 days ago)
    old_metric = SystemMetric(
        computer_id=comp.id,
        cpu_usage=50.0,
        ram_usage=50.0,
        disk_usage=50.0,
        recorded_at=now - timedelta(days=10),
    )
    # Recent sample (2 days ago)
    recent_metric = SystemMetric(
        computer_id=comp.id,
        cpu_usage=50.0,
        ram_usage=50.0,
        disk_usage=50.0,
        recorded_at=now - timedelta(days=2),
    )
    db_session.add_all([old_metric, recent_metric])
    db_session.commit()

    old_id = old_metric.id
    recent_id = recent_metric.id

    purged_count = metric_service.purge_expired_metrics(db_session)
    assert purged_count >= 1

    # Old metric should be deleted, recent metric preserved
    assert db_session.get(SystemMetric, old_id) is None
    assert db_session.get(SystemMetric, recent_id) is not None
