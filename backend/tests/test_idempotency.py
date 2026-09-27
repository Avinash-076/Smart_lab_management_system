"""
Backend Idempotency Verification Tests for Phase 3.

Verifies server-side idempotency across:
1. Command result resubmissions (response lost scenario)
2. Agent issue deduplication
3. Usage session deduplication
4. System metrics deduplication via idempotency_key
"""

import concurrent.futures
import threading
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.remote_command import RemoteCommand, CommandStatus
from app.models.command_result import CommandResult
from app.models.issue import Issue, IssueStatus
from app.models.usage_session import UsageSession
from app.models.system_metric import SystemMetric
from app.models.software import Software
from app.models.process import Process


def get_or_create_test_user(db_session):
    from app.models.role import Role
    from app.models.user import User

    role = db_session.get(Role, 1)
    if not role:
        role = Role(id=1, name="admin")
        db_session.add(role)
        db_session.commit()

    user = db_session.get(User, 1)
    if not user:
        user = User(id=1, username="testadmin", password_hash="fakehash", role_id=1)
        db_session.add(user)
        db_session.commit()
    return user


def test_command_result_idempotent_retry(client, registered_agent, db_session):
    """
    Verify that if a client executes a command, submits the result,
    but the response is lost and the client retries, the server accepts
    the duplicate submission idempotently and returns the existing result
    without raising 409 Conflict or creating duplicate records.
    """
    computer_id = registered_agent["computer_id"]
    token = registered_agent["token"]
    user = get_or_create_test_user(db_session)

    # Create a command in delivered status
    cmd = RemoteCommand(
        computer_id=computer_id,
        command_type="restart",
        payload=None,
        status=CommandStatus.delivered,
        issued_by=user.id,
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"success": True, "message": "Reboot scheduled"}

    # First submission
    resp1 = client.post(f"/api/commands/{cmd.id}/result", json=payload, headers=headers)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["success"] is True
    assert data1["message"] == "Reboot scheduled"

    # Simulate response lost: Client retries identical submission
    resp2 = client.post(f"/api/commands/{cmd.id}/result", json=payload, headers=headers)
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert data2["id"] == data1["id"]
    assert data2["message"] == data1["message"]

    # Verify database has exactly 1 CommandResult row for this command
    results = db_session.query(CommandResult).filter_by(command_id=cmd.id).all()
    assert len(results) == 1


def test_agent_issue_idempotent_deduplication(client, registered_agent, db_session):
    """
    Verify that if an agent reports an open issue multiple times
    (e.g. repeated detection or retry after network drop),
    the server updates the existing open issue rather than creating duplicate tickets.
    """
    token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]

    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "title": "High CPU Detected",
        "description": "CPU exceeded 95% for 3 cycles",
        "severity": "high",
    }

    # Initial report
    resp1 = client.post("/api/issues/agent", json=payload, headers=headers)
    assert resp1.status_code == 201
    data1 = resp1.json()
    issue_id = data1["id"]

    # Retry / subsequent report of same issue condition
    payload["description"] = "CPU exceeded 98% for 4 cycles"
    resp2 = client.post("/api/issues/agent", json=payload, headers=headers)
    assert resp2.status_code == 201
    data2 = resp2.json()

    # Must be the same issue ID with updated description
    assert data2["id"] == issue_id
    assert data2["description"] == "CPU exceeded 98% for 4 cycles"

    # Verify only one open issue exists for this title and computer
    issues = db_session.query(Issue).filter_by(
        computer_id=computer_id,
        title="High CPU Detected",
        status=IssueStatus.open,
    ).all()
    assert len(issues) == 1


def test_usage_session_idempotent_deduplication(client, registered_agent, db_session):
    """
    Verify that resubmitting a usage session batch (e.g. retry after response drop)
    does not create duplicate rows in the database.
    """
    token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]

    headers = {"Authorization": f"Bearer {token}"}
    now_iso = "2026-09-27T10:00:00Z"
    end_iso = "2026-09-27T10:30:00Z"
    payload = {
        "sessions": [
            {
                "application_name": "chrome.exe",
                "started_at": now_iso,
                "ended_at": end_iso,
                "duration_seconds": 1800,
            },
            {
                "application_name": "code.exe",
                "started_at": now_iso,
                "ended_at": end_iso,
                "duration_seconds": 1800,
            },
        ]
    }

    # First upload
    resp1 = client.post("/api/usage", json=payload, headers=headers)
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert len(data1) == 2

    # Second upload of the same batch (retry scenario)
    resp2 = client.post("/api/usage", json=payload, headers=headers)
    assert resp2.status_code == 201
    data2 = resp2.json()
    assert len(data2) == 2

    # Total rows in db for this started_at must be 2, not 4
    start_dt = datetime.fromisoformat("2026-09-27T10:00:00+00:00")
    sessions = db_session.query(UsageSession).filter_by(
        computer_id=computer_id,
        started_at=start_dt,
    ).all()
    assert len(sessions) == 2


def test_metrics_idempotent_deduplication(client, registered_agent, db_session):
    """
    Verify that submitting metrics with an idempotency_key prevents duplicate entries.
    """
    token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]

    headers = {"Authorization": f"Bearer {token}"}
    key = "metric_test_unique_key_123"
    payload = {
        "cpu_usage": 45.5,
        "ram_usage": 60.2,
        "disk_usage": 75.0,
        "network_sent": 10240,
        "network_received": 20480,
        "idempotency_key": key,
    }

    # First submission
    resp1 = client.post("/api/metrics", json=payload, headers=headers)
    assert resp1.status_code == 201
    id1 = resp1.json()["id"]

    # Second submission with same idempotency_key
    resp2 = client.post("/api/metrics", json=payload, headers=headers)
    assert resp2.status_code == 201
    id2 = resp2.json()["id"]

    assert id1 == id2

    # Verify only 1 metric row exists with this key
    metrics = db_session.query(SystemMetric).filter_by(
        computer_id=computer_id,
        idempotency_key=key,
    ).all()
    assert len(metrics) == 1


# ==============================================================================
# CONCURRENT IDEMPOTENCY RACE-CONDITION TESTS
# ==============================================================================

def _concurrent_post(url: str, payload: dict, headers: dict, num_requests: int = 2):
    """
    Fire multiple HTTP requests concurrently against the test application,
    synchronizing them with a barrier to maximize the chance of concurrent
    race condition at the database layer.
    """
    barrier = threading.Barrier(num_requests)

    def worker():
        barrier.wait()
        with TestClient(app) as test_client:
            return test_client.post(url, json=payload, headers=headers)

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as pool:
        futures = [pool.submit(worker) for _ in range(num_requests)]
        return [f.result() for f in futures]


def test_concurrent_metric_idempotency(registered_agent, db_session):
    """
    Simulate two concurrent threads submitting the exact same metric payload
    with an identical idempotency_key simultaneously.

    Expected:
    - Both requests succeed with HTTP 201
    - Both return the exact same metric ID
    - Exactly ONE database record is created
    """
    token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]
    headers = {"Authorization": f"Bearer {token}"}
    key = f"metric_race_key_{computer_id}_concurrent"

    payload = {
        "cpu_usage": 52.3,
        "ram_usage": 44.1,
        "disk_usage": 60.0,
        "network_sent": 5000,
        "network_received": 10000,
        "idempotency_key": key,
    }

    results = _concurrent_post("/api/metrics", payload, headers, num_requests=2)

    # Both requests must receive a successful response
    assert results[0].status_code == 201, results[0].text
    assert results[1].status_code == 201, results[1].text

    id1 = results[0].json()["id"]
    id2 = results[1].json()["id"]
    assert id1 == id2

    # Exactly ONE record exists in the database
    metrics = db_session.query(SystemMetric).filter_by(
        computer_id=computer_id,
        idempotency_key=key,
    ).all()
    assert len(metrics) == 1


def test_concurrent_command_result_idempotency(registered_agent, db_session):
    """
    Simulate two concurrent threads submitting command results for the same
    command simultaneously.

    Expected:
    - Both requests succeed with HTTP 201
    - Both return the same CommandResult ID
    - Exactly ONE CommandResult record exists in the database
    """
    computer_id = registered_agent["computer_id"]
    token = registered_agent["token"]
    user = get_or_create_test_user(db_session)

    cmd = RemoteCommand(
        computer_id=computer_id,
        command_type="shutdown",
        payload=None,
        status=CommandStatus.delivered,
        issued_by=user.id,
    )
    db_session.add(cmd)
    db_session.commit()
    db_session.refresh(cmd)

    headers = {"Authorization": f"Bearer {token}"}
    payload = {"success": True, "message": "Host shutting down"}

    results = _concurrent_post(f"/api/commands/{cmd.id}/result", payload, headers, num_requests=2)

    assert results[0].status_code == 201, results[0].text
    assert results[1].status_code == 201, results[1].text

    id1 = results[0].json()["id"]
    id2 = results[1].json()["id"]
    assert id1 == id2

    results_in_db = db_session.query(CommandResult).filter_by(command_id=cmd.id).all()
    assert len(results_in_db) == 1


def test_concurrent_agent_issue_idempotency(registered_agent, db_session):
    """
    Simulate two concurrent threads reporting the exact same issue condition
    with an identical idempotency_key simultaneously.

    Expected:
    - Both requests succeed with HTTP 201
    - Both return the same issue ID
    - Exactly ONE Issue record exists in the database
    """
    token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]
    headers = {"Authorization": f"Bearer {token}"}
    key = f"issue_race_key_{computer_id}_concurrent"

    payload = {
        "title": "Low Disk Space Alert",
        "description": "Drive C has less than 2 GB remaining",
        "severity": "critical",
        "idempotency_key": key,
    }

    results = _concurrent_post("/api/issues/agent", payload, headers, num_requests=2)

    assert results[0].status_code == 201, results[0].text
    assert results[1].status_code == 201, results[1].text

    id1 = results[0].json()["id"]
    id2 = results[1].json()["id"]
    assert id1 == id2

    issues_in_db = db_session.query(Issue).filter_by(
        computer_id=computer_id,
        idempotency_key=key,
    ).all()
    assert len(issues_in_db) == 1


def test_concurrent_usage_session_idempotency(registered_agent, db_session):
    """
    Simulate two concurrent threads submitting the same usage session batch
    simultaneously.

    Expected:
    - Both requests succeed with HTTP 201
    - Exactly the batch size (2 records) exist in the database without duplicates
    """
    token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]
    headers = {"Authorization": f"Bearer {token}"}

    started_time = "2026-09-27T11:00:00Z"
    ended_time = "2026-09-27T11:45:00Z"
    payload = {
        "sessions": [
            {
                "application_name": "pycharm64.exe",
                "started_at": started_time,
                "ended_at": ended_time,
                "duration_seconds": 2700,
            },
            {
                "application_name": "firefox.exe",
                "started_at": started_time,
                "ended_at": ended_time,
                "duration_seconds": 2700,
            },
        ]
    }

    results = _concurrent_post("/api/usage", payload, headers, num_requests=2)

    assert results[0].status_code == 201, results[0].text
    assert results[1].status_code == 201, results[1].text

    start_dt = datetime.fromisoformat("2026-09-27T11:00:00+00:00")
    db_sessions = db_session.query(UsageSession).filter_by(
        computer_id=computer_id,
        started_at=start_dt,
    ).all()
    assert len(db_sessions) == 2


# ==============================================================================
# INVENTORY IDEMPOTENT RETRY TESTS
# ==============================================================================

def test_software_inventory_idempotent_retry(client, registered_agent, db_session):
    """
    Verify that software inventory replacement is safely idempotent under retry:
    1. Server receives inventory and commits snapshot
    2. Response is simulated lost
    3. Client retries the identical payload
    4. Exactly the current software snapshot exists, no duplicate rows created
    """
    token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "software": [
            {"name": "Python", "version": "3.13.5", "publisher": "Python Foundation"},
            {"name": "Git", "version": "2.44.0", "publisher": "Git Authors"},
            {"name": "VS Code", "version": "1.87.0", "publisher": "Microsoft"},
        ]
    }

    # Initial upload
    resp1 = client.post("/api/software", json=payload, headers=headers)
    assert resp1.status_code == 201, resp1.text
    assert len(resp1.json()) == 3

    # Lost response: retry
    resp2 = client.post("/api/software", json=payload, headers=headers)
    assert resp2.status_code == 201, resp2.text
    assert len(resp2.json()) == 3

    # Direct DB inspection: exactly 3 rows, no duplicate records
    software_rows = db_session.query(Software).filter_by(computer_id=computer_id).all()
    assert len(software_rows) == 3
    names = {s.name for s in software_rows}
    assert names == {"Python", "Git", "VS Code"}


def test_process_inventory_idempotent_retry(client, registered_agent, db_session):
    """
    Verify that process inventory replacement is safely idempotent under retry:
    1. Server receives process snapshot and commits
    2. Response is simulated lost
    3. Client retries the identical payload
    4. Exactly the current process snapshot exists, no duplicate rows created
    """
    token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "processes": [
            {"pid": 1001, "name": "system.exe", "user": "SYSTEM"},
            {"pid": 1002, "name": "explorer.exe", "user": "lab_user"},
            {"pid": 1003, "name": "python.exe", "user": "lab_user"},
        ]
    }

    # Initial upload
    resp1 = client.post("/api/processes", json=payload, headers=headers)
    assert resp1.status_code == 201, resp1.text
    assert len(resp1.json()) == 3

    # Lost response: retry
    resp2 = client.post("/api/processes", json=payload, headers=headers)
    assert resp2.status_code == 201, resp2.text
    assert len(resp2.json()) == 3

    # Direct DB inspection: exactly 3 rows, no duplicate records
    process_rows = db_session.query(Process).filter_by(computer_id=computer_id).all()
    assert len(process_rows) == 3
    pids = {p.pid for p in process_rows}
    assert pids == {1001, 1002, 1003}
