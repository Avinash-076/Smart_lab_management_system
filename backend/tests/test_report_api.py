"""
Comprehensive test suite for SLMS V6.2 Reports and Reporting APIs.
Tests:
- Authorized and unauthorized report access across all domains.
- High-level overview statistics calculation.
- Computer and lab utilization metrics, time periods, and date validations.
- Software inventory reporting with search, filtering, and application aggregations.
- Issue tracking reports with severity and status metrics.
- Maintenance operations reports with status, type, upcoming, and overdue metrics.
- Remote command execution reports with outcome rates.
- Audit log activity reports and security filters.
- Sanitized CSV report exports with formula injection defense.
- Date range validation (from_date > to_date returns 400).
"""

from datetime import datetime, timedelta, timezone
import pytest

from app.auth import create_access_token, hash_password
from app.models.audit_log import AuditLog, AuditResult
from app.models.client_status import ClientStatus
from app.models.command_result import CommandResult
from app.models.computer import Computer
from app.models.issue import Issue, IssueSeverity, IssueSource, IssueStatus
from app.models.maintenance import MaintenanceRecord, MaintenanceStatus, MaintenanceType
from app.models.remote_command import CommandStatus, CommandType, RemoteCommand
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.software import Software
from app.models.system_metric import SystemMetric
from app.models.user import User


@pytest.fixture
def reports_fixture(db_session):
    """Seed comprehensive test data for all reporting domains."""
    # Ensure Admin role with all permissions
    admin_role = db_session.query(Role).filter_by(name="Administrator").first()
    if not admin_role:
        admin_role = Role(name="Administrator", description="Full access")
        db_session.add(admin_role)
        db_session.commit()
        db_session.refresh(admin_role)

    all_permissions = [
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
    ]
    for code in all_permissions:
        perm = (
            db_session.query(RolePermission)
            .filter_by(role_id=admin_role.id, action_code=code)
            .first()
        )
        if not perm:
            db_session.add(RolePermission(role_id=admin_role.id, action_code=code, allowed=True))
        else:
            perm.allowed = True

    # Unprivileged role
    unprivileged_role = db_session.query(Role).filter_by(name="NoReportRole").first()
    if not unprivileged_role:
        unprivileged_role = Role(name="NoReportRole", description="No permissions")
        db_session.add(unprivileged_role)
        db_session.commit()
        db_session.refresh(unprivileged_role)

    db_session.commit()

    # Admin user
    admin_user = db_session.query(User).filter_by(username="reports_admin").first()
    if not admin_user:
        admin_user = User(
            username="reports_admin",
            full_name="Reports Administrator",
            email="reports_admin@slms.local",
            password_hash=hash_password("ReportsAdminPass123!"),
            role_id=admin_role.id,
            is_active=True,
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)

    # Unprivileged user
    unprivileged_user = db_session.query(User).filter_by(username="reports_unprivileged").first()
    if not unprivileged_user:
        unprivileged_user = User(
            username="reports_unprivileged",
            full_name="Unprivileged User",
            email="unprivileged@slms.local",
            password_hash=hash_password("UnprivilegedPass123!"),
            role_id=unprivileged_role.id,
            is_active=True,
        )
        db_session.add(unprivileged_user)
        db_session.commit()
        db_session.refresh(unprivileged_user)

    # Computers
    now = datetime.now(timezone.utc)
    c1 = db_session.query(Computer).filter_by(hostname="PC-REPORT-01").first()
    if not c1:
        c1 = Computer(
            hostname="PC-REPORT-01",
            ip_address="192.168.99.101",
            mac_address="DE:AD:BE:EF:00:01",
            os_name="Windows",
            os_version="11 Pro",
            registered_at=now - timedelta(days=10),
        )
        db_session.add(c1)
        db_session.commit()
        db_session.refresh(c1)

    c2 = db_session.query(Computer).filter_by(hostname="PC-REPORT-02").first()
    if not c2:
        c2 = Computer(
            hostname="PC-REPORT-02",
            ip_address="192.168.99.102",
            mac_address="DE:AD:BE:EF:00:02",
            os_name="Windows",
            os_version="10 Enterprise",
            registered_at=now - timedelta(days=5),
        )
        db_session.add(c2)
        db_session.commit()
        db_session.refresh(c2)

    # Statuses
    s1 = db_session.query(ClientStatus).filter_by(computer_id=c1.id).first()
    if not s1:
        s1 = ClientStatus(computer_id=c1.id, status="online", last_seen=now)
        db_session.add(s1)
    else:
        s1.status = "online"
        s1.last_seen = now

    s2 = db_session.query(ClientStatus).filter_by(computer_id=c2.id).first()
    if not s2:
        s2 = ClientStatus(computer_id=c2.id, status="offline", last_seen=now - timedelta(hours=5))
        db_session.add(s2)
    else:
        s2.status = "offline"
        s2.last_seen = now - timedelta(hours=5)

    db_session.commit()

    # Telemetry metrics
    m1 = SystemMetric(
        computer_id=c1.id,
        cpu_usage=35.5,
        ram_usage=62.0,
        disk_usage=45.0,
        recorded_at=now - timedelta(hours=2),
    )
    m2 = SystemMetric(
        computer_id=c1.id,
        cpu_usage=55.0,
        ram_usage=70.0,
        disk_usage=45.0,
        recorded_at=now - timedelta(hours=1),
    )
    m3 = SystemMetric(
        computer_id=c2.id,
        cpu_usage=20.0,
        ram_usage=40.0,
        disk_usage=30.0,
        recorded_at=now - timedelta(hours=3),
    )
    db_session.add_all([m1, m2, m3])

    # Software records
    sw1 = Software(
        computer_id=c1.id,
        name="Google Chrome",
        version="136.0.0",
        publisher="Google LLC",
        install_date="2026-01-10",
        collected_at=now - timedelta(days=2),
    )
    sw2 = Software(
        computer_id=c2.id,
        name="Google Chrome",
        version="136.0.0",
        publisher="Google LLC",
        install_date="2026-01-12",
        collected_at=now - timedelta(days=2),
    )
    sw3 = Software(
        computer_id=c1.id,
        name="Visual Studio Code",
        version="1.99.0",
        publisher="Microsoft Corporation",
        install_date="2026-02-01",
        collected_at=now - timedelta(days=1),
    )
    # Inject formula character in software name to test CSV formula injection defense
    sw_formula = Software(
        computer_id=c2.id,
        name="=cmd|'/C calc'!A0",
        version="1.0.0",
        publisher="Dangerous Software Corp",
        install_date="2026-03-01",
        collected_at=now - timedelta(days=1),
    )
    db_session.add_all([sw1, sw2, sw3, sw_formula])

    # Issues
    iss1 = Issue(
        computer_id=c1.id,
        title="High CPU Load Detected",
        description="CPU spiked over threshold during lab session",
        severity=IssueSeverity.high,
        status=IssueStatus.open,
        source=IssueSource.system,
        created_at=now - timedelta(days=1),
        created_by=admin_user.id,
    )
    iss2 = Issue(
        computer_id=c2.id,
        title="Offline computer network issue",
        description="Unable to contact agent",
        severity=IssueSeverity.critical,
        status=IssueStatus.resolved,
        source=IssueSource.admin,
        created_at=now - timedelta(days=3),
        resolved_at=now - timedelta(days=1),
        resolution_notes="Power supply reconnected",
        created_by=admin_user.id,
        resolved_by=admin_user.id,
    )
    db_session.add_all([iss1, iss2])

    # Maintenance records
    maint1 = MaintenanceRecord(
        computer_id=c1.id,
        title="Quarterly Hardware Inspection",
        description="Clean dust filters and check RAM seats",
        maintenance_type=MaintenanceType.preventive,
        status=MaintenanceStatus.scheduled,
        technician_name="Alice Smith",
        scheduled_at=now + timedelta(days=2),  # Upcoming
        created_at=now - timedelta(days=1),
        created_by=admin_user.id,
    )
    maint2 = MaintenanceRecord(
        computer_id=c2.id,
        title="Urgent Power Unit Replacement",
        description="Replace failing PSU",
        maintenance_type=MaintenanceType.corrective,
        status=MaintenanceStatus.scheduled,
        technician_name="Bob Jones",
        scheduled_at=now - timedelta(days=1),  # Overdue
        created_at=now - timedelta(days=4),
        created_by=admin_user.id,
    )
    maint3 = MaintenanceRecord(
        computer_id=c1.id,
        title="Software update batch",
        description="Updated developer tooling",
        maintenance_type=MaintenanceType.software,
        status=MaintenanceStatus.completed,
        technician_name="Alice Smith",
        completed_at=now - timedelta(days=2),
        created_at=now - timedelta(days=3),
        created_by=admin_user.id,
    )
    db_session.add_all([maint1, maint2, maint3])

    # Remote Commands
    cmd1 = RemoteCommand(
        computer_id=c1.id,
        command_type=CommandType.restart,
        status=CommandStatus.executed,
        issued_by=admin_user.id,
        created_at=now - timedelta(hours=4),
    )
    db_session.add(cmd1)
    db_session.commit()
    db_session.refresh(cmd1)

    res1 = CommandResult(
        command_id=cmd1.id,
        success=True,
        message="System restart initiated successfully",
        completed_at=now - timedelta(hours=4) + timedelta(seconds=15),
    )
    db_session.add(res1)

    cmd2 = RemoteCommand(
        computer_id=c2.id,
        command_type=CommandType.lock,
        status=CommandStatus.failed,
        issued_by=admin_user.id,
        created_at=now - timedelta(hours=6),
    )
    db_session.add(cmd2)
    db_session.commit()
    db_session.refresh(cmd2)

    res2 = CommandResult(
        command_id=cmd2.id,
        success=False,
        message="Client offline, command timed out",
        completed_at=now - timedelta(hours=6) + timedelta(minutes=5),
    )
    db_session.add(res2)

    # Audit Logs
    audit1 = AuditLog(
        user_id=admin_user.id,
        action="CREATE_USER",
        target_type="user",
        target_id=admin_user.id,
        result=AuditResult.success,
        ip_address="127.0.0.1",
        created_at=now - timedelta(days=2),
    )
    audit2 = AuditLog(
        user_id=admin_user.id,
        action="ISSUE_COMMAND",
        target_type="command",
        target_id=cmd1.id,
        result=AuditResult.success,
        ip_address="127.0.0.1",
        created_at=now - timedelta(hours=4),
    )
    db_session.add_all([audit1, audit2])

    db_session.commit()

    admin_token = create_access_token({"sub": str(admin_user.id)})
    unprivileged_token = create_access_token({"sub": str(unprivileged_user.id)})

    return {
        "admin_user": admin_user,
        "admin_headers": {"Authorization": f"Bearer {admin_token}"},
        "unprivileged_headers": {"Authorization": f"Bearer {unprivileged_token}"},
        "c1": c1,
        "c2": c2,
    }


# ============================================================
# AUTHORIZATION TESTS
# ============================================================

def test_reports_unauthorized_access(client):
    """Endpoints require authentication token."""
    assert client.get("/api/reports/summary").status_code == 401
    assert client.get("/api/reports/utilization").status_code == 401
    assert client.get("/api/reports/software").status_code == 401
    assert client.get("/api/reports/issues").status_code == 401
    assert client.get("/api/reports/maintenance").status_code == 401
    assert client.get("/api/reports/commands").status_code == 401
    assert client.get("/api/reports/audit").status_code == 401
    assert client.get("/api/reports/export").status_code == 401


def test_reports_forbidden_access(client, reports_fixture):
    """Endpoints reject users without required RBAC permissions."""
    headers = reports_fixture["unprivileged_headers"]
    assert client.get("/api/reports/summary", headers=headers).status_code == 403
    assert client.get("/api/reports/utilization", headers=headers).status_code == 403
    assert client.get("/api/reports/software", headers=headers).status_code == 403
    assert client.get("/api/reports/issues", headers=headers).status_code == 403
    assert client.get("/api/reports/maintenance", headers=headers).status_code == 403
    assert client.get("/api/reports/commands", headers=headers).status_code == 403
    assert client.get("/api/reports/audit", headers=headers).status_code == 403
    assert client.get("/api/reports/export", headers=headers).status_code == 403


# ============================================================
# REPORT OVERVIEW / SUMMARY TESTS
# ============================================================

def test_report_overview_metrics(client, reports_fixture):
    """GET /api/reports/summary returns accurate cross-domain counts."""
    resp = client.get("/api/reports/summary", headers=reports_fixture["admin_headers"])
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_computers"] >= 2
    assert data["online_computers"] >= 1
    assert data["offline_computers"] >= 1
    assert data["total_software_records"] >= 4
    assert data["unique_software_count"] >= 3
    assert data["total_issues"] >= 2
    assert data["open_issues"] >= 1
    assert data["resolved_issues"] >= 1
    assert data["total_maintenance"] >= 3
    assert data["pending_maintenance"] >= 2
    assert data["completed_maintenance"] >= 1
    assert data["overdue_maintenance"] >= 1
    assert data["total_commands"] >= 2
    assert data["executed_commands"] >= 1
    assert data["failed_commands"] >= 1
    assert data["total_audit_events"] >= 2


# ============================================================
# COMPUTER & UTILIZATION REPORT TESTS
# ============================================================

def test_utilization_report_periods_and_breakdown(client, reports_fixture):
    """GET /api/reports/utilization calculates metrics for 24h, 7d, 30d periods."""
    resp = client.get(
        "/api/reports/utilization?period=24h",
        headers=reports_fixture["admin_headers"],
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["period"] == "24h"
    assert "metrics_summary" in data
    assert data["metrics_summary"]["avg_cpu_percent"] > 0
    assert len(data["computers"]) >= 2

    # Check computer breakdown fields
    comp1 = next(c for c in data["computers"] if c["hostname"] == "PC-REPORT-01")
    assert comp1["status"] == "online"
    assert comp1["avg_cpu"] > 0
    assert comp1["sample_count"] >= 2

    # Check invalid date range rejection
    bad_dates_resp = client.get(
        "/api/reports/utilization?from_date=2026-10-10T00:00:00Z&to_date=2026-10-01T00:00:00Z",
        headers=reports_fixture["admin_headers"],
    )
    assert bad_dates_resp.status_code == 400
    assert "from_date must be before or equal to to_date" in bad_dates_resp.json()["detail"]


# ============================================================
# SOFTWARE INVENTORY REPORT TESTS
# ============================================================

def test_software_inventory_report(client, reports_fixture):
    """GET /api/reports/software provides search, pagination, and top applications."""
    resp = client.get(
        "/api/reports/software?page=1&limit=10",
        headers=reports_fixture["admin_headers"],
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_records"] >= 4
    assert len(data["items"]) >= 4
    assert len(data["top_installed"]) >= 1
    assert any(t["name"] == "Google Chrome" for t in data["top_installed"])

    # Search filter
    search_resp = client.get(
        "/api/reports/software?search=Visual Studio",
        headers=reports_fixture["admin_headers"],
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert len(search_data["items"]) >= 1
    assert all("Visual Studio" in item["name"] for item in search_data["items"])


# ============================================================
# ISSUE TRACKING REPORT TESTS
# ============================================================

def test_issue_tracking_report(client, reports_fixture):
    """GET /api/reports/issues aggregates by status and severity with filters."""
    resp = client.get(
        "/api/reports/issues",
        headers=reports_fixture["admin_headers"],
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_issues"] >= 2
    assert "open" in data["by_status"]
    assert "resolved" in data["by_status"]
    assert "high" in data["by_severity"]
    assert "critical" in data["by_severity"]

    # Filter by severity
    crit_resp = client.get(
        "/api/reports/issues?severity=critical",
        headers=reports_fixture["admin_headers"],
    )
    assert crit_resp.status_code == 200
    assert len(crit_resp.json()["items"]) >= 1
    assert all(item["severity"] == "critical" for item in crit_resp.json()["items"])


# ============================================================
# MAINTENANCE REPORT TESTS
# ============================================================

def test_maintenance_operations_report(client, reports_fixture):
    """GET /api/reports/maintenance groups by status, type, upcoming, and overdue."""
    resp = client.get(
        "/api/reports/maintenance",
        headers=reports_fixture["admin_headers"],
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_records"] >= 3
    assert data["upcoming_count"] >= 1
    assert data["overdue_count"] >= 1
    assert "preventive" in data["by_type"]
    assert "corrective" in data["by_type"]
    assert "software" in data["by_type"]


# ============================================================
# REMOTE COMMANDS REPORT TESTS
# ============================================================

def test_remote_commands_report(client, reports_fixture):
    """GET /api/reports/commands returns command breakdown and success rates."""
    resp = client.get(
        "/api/reports/commands",
        headers=reports_fixture["admin_headers"],
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_commands"] >= 2
    assert data["by_type"].get("restart", 0) >= 1
    assert data["by_type"].get("lock", 0) >= 1
    assert data["by_status"].get("executed", 0) >= 1
    assert data["by_status"].get("failed", 0) >= 1
    assert 0.0 <= data["success_rate"] <= 100.0


# ============================================================
# AUDIT LOG ACTIVITY REPORT TESTS
# ============================================================

def test_audit_activity_report(client, reports_fixture):
    """GET /api/reports/audit aggregates audit events by action and result."""
    resp = client.get(
        "/api/reports/audit",
        headers=reports_fixture["admin_headers"],
    )
    assert resp.status_code == 200
    data = resp.json()

    assert data["total_events"] >= 2
    assert "CREATE_USER" in data["by_action"]
    assert "ISSUE_COMMAND" in data["by_action"]
    assert data["by_result"].get("success", 0) >= 2


# ============================================================
# CSV EXPORT AND FORMULA INJECTION DEFENSE TESTS
# ============================================================

def test_csv_export_and_formula_injection_defense(client, reports_fixture):
    """GET /api/reports/export outputs sanitized CSV with proper MIME headers."""
    # Test utilization export
    util_resp = client.get(
        "/api/reports/export?report_type=utilization",
        headers=reports_fixture["admin_headers"],
    )
    assert util_resp.status_code == 200
    assert "text/csv" in util_resp.headers["Content-Type"]
    assert 'attachment; filename="SLMS-Computer-Utilization-Report-' in util_resp.headers["Content-Disposition"]
    assert "PC-REPORT-01" in util_resp.text

    # Test software export and formula injection defense
    sw_resp = client.get(
        "/api/reports/export?report_type=software",
        headers=reports_fixture["admin_headers"],
    )
    assert sw_resp.status_code == 200
    assert "text/csv" in sw_resp.headers["Content-Type"]
    # The malicious formula "=cmd|'/C calc'!A0" must be escaped to "'=cmd|'/C calc'!A0"
    assert "'=cmd|'/C calc'!A0" in sw_resp.text
    # Raw unescaped formula must NOT be present at the start of a cell
    assert ',"=cmd' not in sw_resp.text

    # Test issues export
    iss_resp = client.get(
        "/api/reports/export?report_type=issues",
        headers=reports_fixture["admin_headers"],
    )
    assert iss_resp.status_code == 200
    assert "High CPU Load Detected" in iss_resp.text

    # Test maintenance export
    maint_resp = client.get(
        "/api/reports/export?report_type=maintenance",
        headers=reports_fixture["admin_headers"],
    )
    assert maint_resp.status_code == 200
    assert "Quarterly Hardware Inspection" in maint_resp.text

    # Test commands export
    cmd_resp = client.get(
        "/api/reports/export?report_type=commands",
        headers=reports_fixture["admin_headers"],
    )
    assert cmd_resp.status_code == 200
    assert "restart" in cmd_resp.text

    # Test audit export
    audit_resp = client.get(
        "/api/reports/export?report_type=audit",
        headers=reports_fixture["admin_headers"],
    )
    assert audit_resp.status_code == 200
    assert "CREATE_USER" in audit_resp.text
