from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest

from modules.hardware import (
    _parse_wmi_date,
    _format_boot_time,
    get_detailed_hardware_specs,
)
from server.sender import send_hardware_specs


def test_parse_wmi_date():
    """Verify parsing of various WMI / CIM date formats."""
    # /Date(ms)/ format
    assert _parse_wmi_date("/Date(1738673068000)/", date_only=True) == "04-02-2025"
    # YYYYMMDD format
    assert _parse_wmi_date("20240210123000.000000+000", date_only=True) == "10-02-2024"
    # None or empty
    assert _parse_wmi_date(None) is None
    assert _parse_wmi_date("") is None


def test_format_boot_time():
    """Verify relative boot time formatting."""
    now = datetime.now()
    today_boot = now.replace(hour=6, minute=15)
    formatted = _format_boot_time(today_boot)
    assert formatted.startswith("Today, 06:15")


def test_get_detailed_hardware_specs_keys():
    """Verify get_detailed_hardware_specs returns all required hardware specification keys."""
    specs = get_detailed_hardware_specs()
    assert isinstance(specs, dict)

    required_keys = [
        "manufacturer",
        "model",
        "serial_number",
        "system_type",
        "bios_version",
        "bios_date",
        "processor_name",
        "processor_cores",
        "processor_threads",
        "processor_base_speed",
        "processor_max_speed",
        "ram_total_gb",
        "ram_usable_gb",
        "ram_type",
        "ram_speed",
        "ram_slots_used",
        "ram_slots_total",
        "storage_drives_count",
        "storage_total_gb",
        "storage_type",
        "storage_health",
        "gpu_name",
        "gpu_memory_mb",
        "gpu_driver_version",
        "subnet_mask",
        "default_gateway",
        "dns_servers",
        "connection_type",
        "motherboard_manufacturer",
        "motherboard_model",
        "motherboard_chipset",
        "motherboard_serial",
        "os_install_date",
        "last_boot_time",
        "power_plan",
        "agent_version",
    ]

    for key in required_keys:
        assert key in specs, f"Missing required key: {key}"


@patch("server.sender.get_api_base_url", return_value="https://test.slms.local")
@patch("server.sender.create_secure_session")
def test_send_hardware_specs(mock_create_session, mock_get_url):
    """Verify send_hardware_specs sends POST request to /api/clients/hardware."""
    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1, "computer_id": 42}
    mock_session.post.return_value = mock_response
    mock_create_session.return_value = mock_session

    sample_specs = {
        "processor_name": "Intel Core i5-10400",
        "ram_total_gb": 16.0,
    }

    result = send_hardware_specs(sample_specs, "test_token_123")

    mock_session.post.assert_called_once()
    call_args = mock_session.post.call_args
    assert "/api/clients/hardware" in call_args[0][0]
    assert call_args[1]["json"] == sample_specs
    assert call_args[1]["headers"]["Authorization"] == "Bearer test_token_123"
    assert result == {"id": 1, "computer_id": 42}


def test_hardware_fingerprint_deterministic_and_ignores_boot_time():
    """Verify compute_hardware_fingerprint is deterministic and ignores last_boot_time."""
    from modules.hardware import compute_hardware_fingerprint

    specs1 = {
        "processor_name": "Intel Core i7",
        "ram_total_gb": 16.0,
        "last_boot_time": "Today, 10:00 AM",
    }
    specs2 = {
        "ram_total_gb": 16.0,
        "processor_name": "Intel Core i7",
        "last_boot_time": "Yesterday, 08:30 PM",  # volatile field changed
    }
    specs3 = {
        "processor_name": "Intel Core i9",  # hardware changed
        "ram_total_gb": 32.0,
        "last_boot_time": "Today, 10:00 AM",
    }

    fp1 = compute_hardware_fingerprint(specs1)
    fp2 = compute_hardware_fingerprint(specs2)
    fp3 = compute_hardware_fingerprint(specs3)

    assert fp1 == fp2, "Fingerprint should ignore volatile last_boot_time"
    assert fp1 != fp3, "Fingerprint must change when physical hardware changes"
    assert compute_hardware_fingerprint({}) == compute_hardware_fingerprint({})


def test_hardware_state_persistence_and_atomic_recovery(tmp_path):
    """Verify hardware state file loading, atomic saving, and corrupted file recovery."""
    from modules.hardware import (
        load_hardware_state,
        record_hardware_delivered,
        record_hardware_enqueued,
    )

    state_file = str(tmp_path / "hardware_state.json")

    # Initial empty state
    initial = load_hardware_state(state_file)
    assert initial["last_delivered_fingerprint"] is None

    # Record enqueued
    record_hardware_enqueued("fp_abc123", state_file=state_file)
    s1 = load_hardware_state(state_file)
    assert s1["last_enqueued_fingerprint"] == "fp_abc123"
    assert s1["last_delivered_fingerprint"] is None

    # Record delivered
    record_hardware_delivered("fp_abc123", state_file=state_file)
    s2 = load_hardware_state(state_file)
    assert s2["last_delivered_fingerprint"] == "fp_abc123"
    assert s2["last_delivery_time"] is not None

    # Corrupted file recovery
    with open(state_file, "w") as f:
        f.write("corrupted json {{{{")
    recovered = load_hardware_state(state_file)
    assert recovered["last_delivered_fingerprint"] is None


def test_collector_manager_collect_hardware_specs():
    """Verify CollectorManager collects hardware specs with all required keys."""
    from core.managers import CollectorManager

    mgr = CollectorManager(max_workers=1)
    try:
        specs = mgr.collect_hardware_specs()
        assert isinstance(specs, dict)
        assert "processor_name" in specs
        assert "ram_total_gb" in specs
        assert "agent_version" in specs
    finally:
        mgr.stop()


def test_upload_manager_enqueues_and_deduplicates_hardware(tmp_path):
    """Verify UploadManager enqueues hardware to outbox and skips unchanged delivery."""
    from core.managers import OutboxManager, TokenHolder, TokenManager, UploadManager
    from core.outbox.storage import DurableOutbox

    db_path = str(tmp_path / "test_outbox.db")
    state_file = str(tmp_path / "hw_state.json")
    outbox = DurableOutbox(db_path=db_path)
    outbox_mgr = OutboxManager(outbox=outbox, enable_outbox=True, hardware_state_file=state_file)
    token_mgr = TokenManager(token_holder=TokenHolder("test_token"))
    upload_mgr = UploadManager()

    sample_specs = {
        "processor_name": "Intel Core i7-12700K",
        "ram_total_gb": 32.0,
        "manufacturer": "Custom Rig",
        "agent_version": "1.0.0",
    }

    with patch("core.managers._resolve_computer_id", return_value=77):
        # 1. First upload enqueues to outbox
        enqueued = upload_mgr.upload_hardware_specs(
            sample_specs,
            token_mgr,
            outbox_mgr,
            state_file=state_file,
        )
        assert enqueued is True

        pending = outbox.get_pending_batch(limit=10)
        assert len(pending) == 1
        assert pending[0].event_type == "hardware"
        assert pending[0].payload["processor_name"] == "Intel Core i7-12700K"

        # 2. Mark delivered in state
        from modules.hardware import compute_hardware_fingerprint, record_hardware_delivered
        fp = compute_hardware_fingerprint(sample_specs)
        record_hardware_delivered(fp, state_file=state_file)

        # 3. Second upload should skip because unchanged
        skipped = upload_mgr.upload_hardware_specs(
            sample_specs,
            token_mgr,
            outbox_mgr,
            state_file=state_file,
            force=False,
        )
        assert skipped is False

        # 4. Forced upload re-enqueues
        forced = upload_mgr.upload_hardware_specs(
            sample_specs,
            token_mgr,
            outbox_mgr,
            state_file=state_file,
            force=True,
        )
        assert forced is True


def test_upload_manager_direct_http_fallback_and_401_retry(tmp_path):
    """Verify direct HTTP upload works and transparently retries on HTTP 401."""
    import requests
    from core.managers import OutboxManager, TokenHolder, TokenManager, UploadManager

    state_file = str(tmp_path / "hw_state.json")
    outbox_mgr = OutboxManager(outbox=None, enable_outbox=False)
    token_holder = TokenHolder("old_token")
    token_mgr = TokenManager(token_holder=token_holder)
    upload_mgr = UploadManager()

    sample_specs = {"processor_name": "AMD Ryzen 9", "ram_total_gb": 64.0}

    # Simulate 401 on first attempt, then success on second attempt after refresh
    resp_401 = requests.Response()
    resp_401.status_code = 401
    err_401 = requests.HTTPError(response=resp_401)

    mock_send = MagicMock(side_effect=[err_401, {"id": 1, "computer_id": 99}])

    with patch("core.managers._resolve_send_hardware_specs", mock_send), \
         patch.object(token_mgr, "refresh", return_value="new_token") as mock_refresh:
        success = upload_mgr.upload_hardware_specs(
            sample_specs,
            token_mgr,
            outbox_mgr,
            state_file=state_file,
        )
        assert success is True
        mock_refresh.assert_called_once()
        assert mock_send.call_count == 2


def test_outbox_worker_dispatches_hardware():
    """Verify OutboxDeliveryWorker dispatches hardware events to send_hardware_specs."""
    from core.outbox.models import OutboxRecord, OutboxStatus
    from core.outbox.worker import OutboxDeliveryWorker

    mock_outbox = MagicMock()
    mock_send_hw = MagicMock(return_value={"id": 1})

    item = OutboxRecord(
        id=1,
        event_type="hardware",
        payload={"processor_name": "Intel Core i5", "ram_total_gb": 16.0},
        idempotency_key="hw_key_1",
        priority=10,
        status=OutboxStatus.PENDING,
        attempt_count=0,
        max_attempts=5,
        next_attempt_at=0.0,
        created_at=0.0,
        updated_at=0.0,
        last_error=None,
        payload_size=100,
    )

    worker = OutboxDeliveryWorker(
        outbox=mock_outbox,
        get_token=lambda: "token_123",
    )

    with patch("core.outbox.worker.send_hardware_specs", mock_send_hw):
        worker._dispatch_event(item, "token_123")
        mock_send_hw.assert_called_once_with(item.payload, "token_123")


def test_runtime_manager_registers_hardware_scheduled_job():
    """Verify RuntimeManager registers hardware job on the scheduler."""
    import threading
    from core.runtime import RuntimeManager

    stop_event = threading.Event()
    rt = RuntimeManager(stop_event=stop_event, enable_single_instance=False, enable_outbox=False)

    rt._register_scheduled_jobs()

    job_names = [j.name for j in rt.scheduler._jobs.values()]
    assert "hardware" in job_names, f"Expected 'hardware' in scheduled jobs: {job_names}"
    assert rt.due_for_hardware_scan() is True


def test_enroll_includes_hardware_specs():
    """Verify enroll() includes collected hardware specs in registration payload."""
    from server.enroll import enroll

    mock_session = MagicMock()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "agent_id": "AGT_TEST",
        "client_secret": "SECRET_TEST",
        "computer_id": 101,
    }
    mock_session.post.return_value = mock_resp

    mock_store = MagicMock()
    mock_store.get_enrolled_credentials.return_value = {
        "agent_id": "AGT_TEST",
        "client_secret": "SECRET_TEST",
        "computer_id": 101,
    }
    mock_store.is_enrolled.return_value = True
    mock_store.get_server_url.return_value = "https://slms.test.local"

    mock_specs = {"processor_name": "Intel Core i7", "ram_total_gb": 16.0}

    with patch("server.enroll.create_secure_session", return_value=mock_session), \
         patch("server.enroll.get_system_info", return_value={
             "computer_name": "PC-101",
             "ip_address": "10.0.0.5",
             "mac_address": "AA:BB:CC:DD:EE:FF",
             "operating_system": "Windows 11",
             "os_version": "23H2",
         }), \
         patch("modules.hardware.get_detailed_hardware_specs", return_value=mock_specs):

        result = enroll(
            enrollment_key="KEY-VALID-123",
            server_url="https://slms.test.local",
            store=mock_store,
        )

        assert result["computer_id"] == 101
        call_args = mock_session.post.call_args
        sent_json = call_args[1]["json"]
        assert "hardware" in sent_json
        assert sent_json["hardware"] == mock_specs
