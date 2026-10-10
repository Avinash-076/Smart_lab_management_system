from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# SUMMARY OVERVIEW
# ============================================================

class ReportOverviewResponse(BaseModel):
    total_computers: int = 0
    online_computers: int = 0
    offline_computers: int = 0
    total_software_records: int = 0
    unique_software_count: int = 0
    total_issues: int = 0
    open_issues: int = 0
    resolved_issues: int = 0
    critical_issues: int = 0
    total_maintenance: int = 0
    pending_maintenance: int = 0
    completed_maintenance: int = 0
    overdue_maintenance: int = 0
    total_commands: int = 0
    executed_commands: int = 0
    failed_commands: int = 0
    total_audit_events: int = 0


# ============================================================
# COMPUTER & UTILIZATION REPORT
# ============================================================

class MetricAverages(BaseModel):
    avg_cpu_percent: float = 0.0
    max_cpu_percent: float = 0.0
    avg_ram_percent: float = 0.0
    max_ram_percent: float = 0.0
    avg_disk_percent: float = 0.0
    max_disk_percent: float = 0.0


class MetricTimelinePoint(BaseModel):
    timestamp: datetime
    avg_cpu: float
    avg_ram: float
    avg_disk: float


class ComputerUtilizationItem(BaseModel):
    id: int
    hostname: str
    ip_address: str
    mac_address: str
    os_name: str
    os_version: str
    status: str
    last_seen: datetime | None = None
    registered_at: datetime
    avg_cpu: float = 0.0
    avg_ram: float = 0.0
    avg_disk: float = 0.0
    sample_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class UtilizationReportResponse(BaseModel):
    period: str
    from_date: datetime
    to_date: datetime
    total_computers: int
    online_computers: int
    offline_computers: int
    metrics_summary: MetricAverages
    timeline: list[MetricTimelinePoint]
    computers: list[ComputerUtilizationItem]


# ============================================================
# SOFTWARE REPORT
# ============================================================

class TopSoftwareItem(BaseModel):
    name: str
    count: int
    publisher: str | None = None


class SoftwareReportItem(BaseModel):
    id: int
    name: str
    version: str | None = None
    publisher: str | None = None
    install_date: str | None = None
    collected_at: datetime
    computer_id: int
    computer_hostname: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SoftwareReportResponse(BaseModel):
    total_records: int
    unique_software_count: int
    top_installed: list[TopSoftwareItem]
    page: int
    limit: int
    total_pages: int
    items: list[SoftwareReportItem]


# ============================================================
# ISSUE REPORT
# ============================================================

class IssueReportItem(BaseModel):
    id: int
    computer_id: int
    computer_hostname: str | None = None
    title: str
    description: str
    severity: str
    status: str
    source: str
    resolution_notes: str | None = None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class IssueReportResponse(BaseModel):
    total_issues: int
    by_status: dict[str, int]
    by_severity: dict[str, int]
    page: int
    limit: int
    total_pages: int
    items: list[IssueReportItem]


# ============================================================
# MAINTENANCE REPORT
# ============================================================

class MaintenanceReportItem(BaseModel):
    id: int
    computer_id: int
    computer_hostname: str | None = None
    title: str
    description: str | None = None
    maintenance_type: str
    status: str
    technician_name: str | None = None
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MaintenanceReportResponse(BaseModel):
    total_records: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    upcoming_count: int
    overdue_count: int
    page: int
    limit: int
    total_pages: int
    items: list[MaintenanceReportItem]


# ============================================================
# COMMAND REPORT
# ============================================================

class CommandReportItem(BaseModel):
    id: int
    computer_id: int
    computer_hostname: str | None = None
    command_type: str
    payload: str | None = None
    status: str
    issued_by: int
    issued_by_username: str | None = None
    created_at: datetime
    success: bool | None = None
    result_message: str | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CommandReportResponse(BaseModel):
    total_commands: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    success_rate: float
    page: int
    limit: int
    total_pages: int
    items: list[CommandReportItem]


# ============================================================
# AUDIT REPORT
# ============================================================

class AuditReportItem(BaseModel):
    id: int
    user_id: int | None = None
    username: str | None = None
    action: str
    target_type: str | None = None
    target_id: int | None = None
    result: str
    ip_address: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditReportResponse(BaseModel):
    total_events: int
    by_action: dict[str, int]
    by_result: dict[str, int]
    page: int
    limit: int
    total_pages: int
    items: list[AuditReportItem]
