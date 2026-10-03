"""
Tests for Telemetry contract compatibility (Phase 1 verification).
Verifies that:
1. Process upload accepts payloads where `user` is None (or null), complying with
   student privacy requirements.
2. Metric upload accepts cumulative network counters without semantic disruption.
3. System info computer registration/update schemas do not require or collect username.
"""

import pytest
from app.schemas.process_schema import ProcessItem, ProcessUpload
from app.schemas.metric_schema import MetricUpload
from app.schemas.computer_schema import ComputerCreate


def test_process_schema_accepts_null_user():
    """Verify ProcessItem accepts user=None and defaults to None."""
    item_with_none = ProcessItem(
        pid=1001,
        name="code.exe",
        user=None,
        cpu_percent=12.5,
        memory_percent=5.0,
    )
    assert item_with_none.user is None

    # Serialization check
    payload = item_with_none.model_dump()
    assert payload["user"] is None

    # ProcessUpload container check
    upload = ProcessUpload(processes=[item_with_none])
    assert len(upload.processes) == 1
    assert upload.processes[0].user is None


def test_process_upload_endpoint_accepts_null_user(client, registered_agent):
    """
    Test POST /processes with user=None (privacy requirement).
    Payload matches exact output of client_agent/modules/processes.py.
    """
    token = registered_agent["token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "processes": [
            {
                "pid": 1234,
                "name": "python.exe",
                "user": None,
                "cpu_percent": 2.5,
                "memory_percent": 1.2,
                "status": "running",
                "start_time": "2026-09-26T12:00:00+00:00",
            },
            {
                "pid": 5678,
                "name": "explorer.exe",
                "user": None,
                "cpu_percent": 0.5,
                "memory_percent": 3.4,
                "status": "running",
                "start_time": None,
            },
        ]
    }

    response = client.post("/api/processes", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 2
    assert data[0]["user"] is None
    assert data[1]["user"] is None


def test_metric_schema_preserves_network_counters():
    """Verify MetricUpload preserves cumulative network counter fields."""
    metric = MetricUpload(
        cpu_usage=45.0,
        ram_usage=60.0,
        disk_usage=75.0,
        network_sent=1048576.0,
        network_received=2097152.0,
    )
    assert metric.network_sent == 1048576.0
    assert metric.network_received == 2097152.0


def test_computer_create_schema_has_no_username():
    """Verify ComputerCreate schema has no personal username field."""
    schema_fields = ComputerCreate.model_fields.keys()
    assert "username" not in schema_fields
    assert "user" not in schema_fields


def test_process_schema_validates_start_time_length():
    """Verify ProcessItem accepts start_time up to 64 chars and rejects longer strings."""
    from pydantic import ValidationError

    # Valid 32-char microsecond ISO UTC timestamp
    valid_ts = "2026-10-02T01:35:51.901672+00:00"
    item = ProcessItem(
        pid=1001,
        name="test.exe",
        start_time=valid_ts,
    )
    assert item.start_time == valid_ts

    # Valid 64-char string
    item_64 = ProcessItem(
        pid=1002,
        name="test.exe",
        start_time="X" * 64,
    )
    assert item_64.start_time == "X" * 64

    # Invalid >64 chars
    with pytest.raises(ValidationError):
        ProcessItem(
            pid=1003,
            name="test.exe",
            start_time="X" * 65,
        )


def test_process_upload_endpoint_accepts_microsecond_iso_timestamp_and_persists_to_db(client, registered_agent, db_session):
    """
    Verify POST /api/processes accepts timezone-aware ISO 8601 timestamps
    with microsecond resolution (e.g., '2026-10-02T01:35:51.901672+00:00')
    and persists the record accurately to the database.
    """
    from app.models.process import Process

    token = registered_agent["token"]
    computer_id = registered_agent["computer_id"]
    headers = {"Authorization": f"Bearer {token}"}

    microsecond_ts = "2026-10-02T01:35:51.901672+00:00"
    assert len(microsecond_ts) == 32

    payload = {
        "processes": [
            {
                "pid": 4321,
                "name": "worker.exe",
                "user": None,
                "cpu_percent": 15.5,
                "memory_percent": 8.2,
                "status": "running",
                "start_time": microsecond_ts,
            }
        ]
    }

    response = client.post("/api/processes", json=payload, headers=headers)
    assert response.status_code == 201, f"Response: {response.text}"

    data = response.json()
    assert len(data) == 1
    assert data[0]["start_time"] == microsecond_ts
    assert data[0]["pid"] == 4321

    # Verify actual database persistence
    db_session.expire_all()
    saved_proc = db_session.query(Process).filter_by(
        computer_id=computer_id,
        pid=4321,
    ).first()

    assert saved_proc is not None
    assert saved_proc.name == "worker.exe"
    assert saved_proc.start_time == microsecond_ts
    assert saved_proc.cpu_percent == 15.5
    assert saved_proc.memory_percent == 8.2


def test_process_upload_endpoint_rejects_oversized_start_time(client, registered_agent):
    """Verify POST /api/processes returns HTTP 422 if start_time exceeds 64 chars."""
    token = registered_agent["token"]
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "processes": [
            {
                "pid": 9999,
                "name": "overflow.exe",
                "user": None,
                "cpu_percent": 1.0,
                "memory_percent": 1.0,
                "status": "running",
                "start_time": "T" * 65,
            }
        ]
    }

    response = client.post("/api/processes", json=payload, headers=headers)
    assert response.status_code == 422
