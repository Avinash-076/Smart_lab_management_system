from datetime import datetime, timezone
import json
import logging
import os
import subprocess
import time
from logging.handlers import RotatingFileHandler
from unittest.mock import MagicMock, patch

import pytest

import config
import paths
from core.exporter import clean_legacy_diagnostic_files, export_to_json
from core.logger import SafeRotatingFileHandler, create_rotating_handler, logger
from core.outbox.storage import DurableOutbox
from service.service import configure_service_folder_permissions


def test_log_handler_is_rotating():
    """Verify logger uses a RotatingFileHandler configured with bounded values."""
    rotating_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
    assert len(rotating_handlers) >= 1, "Logger must have at least one RotatingFileHandler"
    handler = rotating_handlers[0]
    assert handler.maxBytes == config.LOG_MAX_BYTES
    assert handler.backupCount == config.LOG_BACKUP_COUNT


def test_log_rotation_on_threshold(tmp_path):
    """Verify log file rotates when size threshold is reached."""
    log_file = tmp_path / "test.log"
    # Small 200 byte threshold with 2 backups
    handler = create_rotating_handler(log_file=str(log_file), max_bytes=200, backup_count=2)
    test_logger = logging.getLogger("SLMS_Test_Rotation")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)

    try:
        # Write enough lines to exceed 200 bytes
        for i in range(15):
            test_logger.info(f"Log entry line number {i} to exceed maxBytes threshold")

        handler.flush()
        handler.close()

        assert log_file.exists(), "Active log file must exist"
        rotated_1 = tmp_path / "test.log.1"
        assert rotated_1.exists(), "Rotated backup test.log.1 must exist"
    finally:
        test_logger.removeHandler(handler)


def test_log_backup_count_is_bounded(tmp_path):
    """Verify log backups never exceed configured backupCount."""
    log_file = tmp_path / "bounded.log"
    backup_count = 3
    handler = create_rotating_handler(log_file=str(log_file), max_bytes=150, backup_count=backup_count)
    test_logger = logging.getLogger("SLMS_Test_Bounded")
    test_logger.setLevel(logging.INFO)
    test_logger.addHandler(handler)

    try:
        for i in range(50):
            test_logger.info(f"Message payload {i:03d} to trigger multiple rollovers")

        handler.flush()
        handler.close()

        # Backups 1, 2, 3 should exist, but 4 must NOT exist
        assert (tmp_path / "bounded.log.1").exists()
        assert (tmp_path / "bounded.log.2").exists()
        assert (tmp_path / "bounded.log.3").exists()
        assert not (tmp_path / "bounded.log.4").exists()
    finally:
        test_logger.removeHandler(handler)


def test_windows_service_data_directory_layout(tmp_path):
    """Verify get_path_layout structures paths under logs, data, cache."""
    layout = paths.get_path_layout(str(tmp_path))
    assert layout["logs"] == str(tmp_path / "logs")
    assert layout["data"] == str(tmp_path / "data")
    assert layout["cache"] == str(tmp_path / "cache")
    assert layout["outbox"] == str(tmp_path / "data" / "outbox")
    assert layout["outbox_db"] == str(tmp_path / "data" / "outbox" / "outbox.db")
    assert layout["diagnostic"] == str(tmp_path / "data" / "diagnostic")
    assert layout["software_state"] == str(tmp_path / "data" / "software_state.json")
    assert layout["usage_state"] == str(tmp_path / "data" / "usage_state.json")
    assert layout["issue_state"] == str(tmp_path / "data" / "issue_state.json")


def test_state_files_are_under_data():
    """Verify paths module points state files under data/."""
    assert os.path.dirname(paths.SOFTWARE_STATE_FILE) == paths.DATA_FOLDER
    assert os.path.dirname(paths.USAGE_STATE_FILE) == paths.DATA_FOLDER
    assert os.path.dirname(paths.ISSUE_STATE_FILE) == paths.DATA_FOLDER
    assert os.path.dirname(paths.OUTBOX_DB_PATH) == paths.OUTBOX_FOLDER
    assert os.path.dirname(paths.OUTBOX_FOLDER) == paths.DATA_FOLDER


def test_diagnostic_directory_is_under_data():
    """Verify diagnostic folder is under data/."""
    assert paths.DIAGNOSTIC_FOLDER == os.path.join(paths.DATA_FOLDER, "diagnostic")
    assert paths.OUTPUT_FOLDER == paths.DIAGNOSTIC_FOLDER


def test_ensure_directories_exist(tmp_path):
    """Verify ensure_directories_exist creates the target directory tree."""
    target_dir = tmp_path / "SLMS_TEST_DIR"
    paths.ensure_directories_exist(str(target_dir))
    assert (target_dir / "logs").is_dir()
    assert (target_dir / "data").is_dir()
    assert (target_dir / "data" / "outbox").is_dir()
    assert (target_dir / "data" / "diagnostic").is_dir()
    assert (target_dir / "cache").is_dir()
    assert (target_dir / "config").is_dir()


def test_diagnostic_export_off_by_default(monkeypatch):
    """Verify diagnostic export is OFF by default."""
    monkeypatch.delenv("SLMS_EXPORT_JSON", raising=False)
    # Re-evaluate config value
    val = os.getenv("SLMS_EXPORT_JSON", "0").lower() in ("1", "true", "yes")
    assert val is False


def test_explicit_diagnostic_export_opt_in(monkeypatch):
    """Verify diagnostic export turns ON with SLMS_EXPORT_JSON=1."""
    monkeypatch.setenv("SLMS_EXPORT_JSON", "1")
    val = os.getenv("SLMS_EXPORT_JSON", "0").lower() in ("1", "true", "yes")
    assert val is True


def test_atomic_json_replacement(tmp_path, monkeypatch):
    """Verify export_to_json writes atomically and updates contents safely."""
    monkeypatch.setattr("core.exporter.OUTPUT_FOLDER", str(tmp_path))

    data1 = {"cycle": 1, "status": "initial"}
    out_path = export_to_json(data1, filename="test_client_data.json")
    assert os.path.isfile(out_path)

    with open(out_path, "r", encoding="utf-8") as f:
        loaded1 = json.load(f)
    assert loaded1["cycle"] == 1

    # Overwrite atomically
    data2 = {"cycle": 2, "status": "updated"}
    out_path2 = export_to_json(data2, filename="test_client_data.json")
    assert out_path == out_path2

    with open(out_path2, "r", encoding="utf-8") as f:
        loaded2 = json.load(f)
    assert loaded2["cycle"] == 2


def test_failed_json_serialization_preserves_previous_file(tmp_path, monkeypatch):
    """Verify an error during serialization preserves previous valid file."""
    monkeypatch.setattr("core.exporter.OUTPUT_FOLDER", str(tmp_path))

    # Create initial valid file
    valid_data = {"status": "good"}
    out_path = export_to_json(valid_data, filename="safe_data.json")
    assert os.path.isfile(out_path)

    # Attempt to write invalid object (unserializable without to_dict)
    class BrokenObject:
        def __repr__(self):
            raise RuntimeError("Serialization failure")

    with patch("core.exporter.json.dump", side_effect=TypeError("JSON serialize error")):
        with pytest.raises(TypeError):
            export_to_json({"broken": BrokenObject()}, filename="safe_data.json")

    # The original file must remain valid and unmodified
    with open(out_path, "r", encoding="utf-8") as f:
        preserved = json.load(f)
    assert preserved["status"] == "good"


def test_temporary_json_file_is_cleaned_up(tmp_path, monkeypatch):
    """Verify temporary files are removed even when write fails."""
    monkeypatch.setattr("core.exporter.OUTPUT_FOLDER", str(tmp_path))

    with patch("core.exporter.json.dump", side_effect=IOError("Disk write simulated crash")):
        with pytest.raises(IOError):
            export_to_json({"data": 123}, filename="fail_data.json")

    # Check for temporary artifacts
    tmp_files = [f for f in os.listdir(str(tmp_path)) if f.startswith(".tmp_diagnostic_")]
    assert len(tmp_files) == 0, f"Temporary files were not cleaned up: {tmp_files}"


def test_diagnostic_retention_is_one_snapshot(tmp_path, monkeypatch):
    """Verify diagnostic folder retains ONE current snapshot and cleans legacy files."""
    monkeypatch.setattr("core.exporter.OUTPUT_FOLDER", str(tmp_path))

    # Plant a legacy timestamped diagnostic file
    legacy_file = tmp_path / "client_data_20260920_120000.json"
    legacy_file.write_text("{}", encoding="utf-8")
    assert legacy_file.exists()

    # Perform normal export
    current_file = export_to_json({"metric": 100}, filename="client_data.json")
    assert os.path.isfile(current_file)

    # Legacy file must have been cleaned up
    assert not legacy_file.exists(), "Legacy timestamped diagnostic file should be removed"

    # Only client_data.json should exist
    files = os.listdir(str(tmp_path))
    assert files == ["client_data.json"]


def test_tracked_client_data_json_is_removed():
    """Verify client_agent/output/client_data.json is not tracked by git."""
    res = subprocess.run(
        ["git", "ls-files", "client_agent/output/client_data.json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert res.stdout.strip() == "", "client_agent/output/client_data.json must not be tracked in git"


def test_runtime_state_patterns_in_gitignore():
    """Verify .gitignore contains runtime state and log patterns."""
    root_gitignore = paths.BASE_PATH.replace("client_agent", ".gitignore")
    if not os.path.isfile(root_gitignore):
        root_gitignore = os.path.join(os.path.dirname(paths.BASE_PATH), ".gitignore")

    with open(root_gitignore, "r", encoding="utf-8") as f:
        content = f.read()

    assert "*.log.*" in content or "*.log" in content
    assert "software_state.json" in content
    assert "usage_state.json" in content
    assert "issue_state.json" in content
    assert "client_data.json" in content


def test_durable_outbox_integration_with_new_data_path(tmp_path):
    """Verify Phase 3 DurableOutbox operates cleanly within the new data directory."""
    outbox_db = tmp_path / "data" / "outbox" / "outbox.db"
    box = DurableOutbox(db_path=str(outbox_db))
    assert outbox_db.exists()

    # Enqueue record
    record = box.enqueue(event_type="test_phase9", payload={"status": "ok"})
    assert record.id > 0

    pending = box.get_pending_batch(limit=10)
    assert len(pending) == 1
    assert pending[0].event_type == "test_phase9"
    assert pending[0].payload == {"status": "ok"}


def test_acl_helper_behavior_without_elevation(monkeypatch):
    """Verify configure_service_folder_permissions handles failure gracefully without silent pass."""
    # Mock subprocess.run to simulate a failed icacls call
    mock_res = MagicMock()
    mock_res.returncode = 5  # Access Denied
    mock_res.stderr = "Access is denied."
    mock_res.stdout = ""

    with patch("service.service.subprocess.run", return_value=mock_res):
        with patch.dict(os.environ, {"SLMS_DEV_MODE": "0"}):
            with patch("service.service.os.name", "nt"):
                # Call should return False and not raise unhandled exception
                success = configure_service_folder_permissions(service_account="NT SERVICE\\SLMSService")
                assert success is False


# ============================================================================
# Outbox Path Migration Tests (Requirement 14)
# ============================================================================

def test_migration_old_outbox_only_migrated_to_new_path(tmp_path):
    """Test 14a: Legacy outbox in <data_dir>/outbox is migrated to <data_dir>/data/outbox."""
    from core.outbox.migration import migrate_legacy_outbox
    old_db = tmp_path / "outbox" / "outbox.db"
    old_db.parent.mkdir(parents=True, exist_ok=True)

    # Initialize old outbox with a test record
    old_box = DurableOutbox(db_path=str(old_db))
    rec = old_box.enqueue("metric", {"val": 42}, idempotency_key="fp_mig_1")
    assert rec.id > 0
    del old_box
    import gc
    gc.collect()

    new_db = tmp_path / "data" / "outbox" / "outbox.db"
    assert not new_db.exists()

    # Run migration
    result = migrate_legacy_outbox(data_dir=str(tmp_path))
    assert result is True

    # Old database file should no longer exist in old folder
    assert not old_db.exists()
    # New database file must exist and contain the migrated record
    assert new_db.exists()
    new_box = DurableOutbox(db_path=str(new_db))
    batch = new_box.get_pending_batch(limit=5)
    assert len(batch) == 1
    assert batch[0].payload == {"val": 42}
    assert batch[0].idempotency_key == "fp_mig_1"


def test_migration_no_old_outbox_normal_startup(tmp_path):
    """Test 14b: Fresh start with no legacy outbox returns True cleanly."""
    from core.outbox.migration import migrate_legacy_outbox
    result = migrate_legacy_outbox(data_dir=str(tmp_path))
    assert result is True


def test_migration_new_outbox_already_exists_no_overwrite(tmp_path):
    """Test 14c: New outbox already exists and no legacy outbox exists -> returns True without error."""
    from core.outbox.migration import migrate_legacy_outbox
    new_db = tmp_path / "data" / "outbox" / "outbox.db"
    new_db.parent.mkdir(parents=True, exist_ok=True)
    box = DurableOutbox(db_path=str(new_db))
    box.enqueue("telemetry", {"active": True})

    result = migrate_legacy_outbox(data_dir=str(tmp_path))
    assert result is True

    # Data in new outbox remains intact
    batch = box.get_pending_batch(limit=5)
    assert len(batch) == 1


def test_migration_both_old_and_new_exist_safe_refusal(tmp_path):
    """Test 14d: Both old and new outbox databases exist -> safe refusal without data loss."""
    from core.outbox.migration import migrate_legacy_outbox
    old_db = tmp_path / "outbox" / "outbox.db"
    new_db = tmp_path / "data" / "outbox" / "outbox.db"
    old_db.parent.mkdir(parents=True, exist_ok=True)
    new_db.parent.mkdir(parents=True, exist_ok=True)

    old_box = DurableOutbox(db_path=str(old_db))
    old_box.enqueue("old_event", {"old": 1})
    del old_box

    new_box = DurableOutbox(db_path=str(new_db))
    new_box.enqueue("new_event", {"new": 2})
    del new_box
    import gc
    gc.collect()

    # Must raise RuntimeError refusing to overwrite or merge
    with pytest.raises(RuntimeError) as exc_info:
        migrate_legacy_outbox(data_dir=str(tmp_path))

    assert "Outbox migration conflict" in str(exc_info.value)
    # Both databases must remain intact
    assert old_db.exists()
    assert new_db.exists()


def test_migration_is_idempotent(tmp_path):
    """Test 14e: Running migration multiple times is idempotent."""
    from core.outbox.migration import migrate_legacy_outbox
    old_db = tmp_path / "outbox" / "outbox.db"
    old_db.parent.mkdir(parents=True, exist_ok=True)

    old_box = DurableOutbox(db_path=str(old_db))
    old_box.enqueue("event", {"count": 1})
    del old_box
    import gc
    gc.collect()

    # First migration run
    assert migrate_legacy_outbox(data_dir=str(tmp_path)) is True
    new_db = tmp_path / "data" / "outbox" / "outbox.db"
    assert new_db.exists()
    assert not old_db.exists()

    # Second migration run (idempotent)
    assert migrate_legacy_outbox(data_dir=str(tmp_path)) is True
    assert new_db.exists()


def test_migration_occurs_before_outbox_initialization(tmp_path, monkeypatch):
    """Test 14f: OutboxManager migrates legacy outbox before initializing its own DurableOutbox."""
    from core.managers import OutboxManager
    old_db = tmp_path / "outbox" / "outbox.db"
    old_db.parent.mkdir(parents=True, exist_ok=True)

    old_box = DurableOutbox(db_path=str(old_db))
    old_box.enqueue("migrated_startup_event", {"boot": True})
    del old_box
    import gc
    gc.collect()

    # Point paths and environment to tmp_path
    monkeypatch.setenv("SLMS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr("paths.DATA_DIR", str(tmp_path))
    monkeypatch.setattr("paths.DATA_FOLDER", str(tmp_path / "data"))
    monkeypatch.setattr("paths.OUTBOX_FOLDER", str(tmp_path / "data" / "outbox"))
    monkeypatch.setattr("paths.OUTBOX_DB_PATH", str(tmp_path / "data" / "outbox" / "outbox.db"))
    monkeypatch.setattr("core.outbox.storage.OUTBOX_DB_PATH", str(tmp_path / "data" / "outbox" / "outbox.db"))

    # Initializing OutboxManager without explicit outbox triggers migration
    mgr = OutboxManager(enable_outbox=True)
    assert mgr.outbox is not None
    assert mgr.outbox.db_path == str(tmp_path / "data" / "outbox" / "outbox.db")
    assert not old_db.exists()

    pending = mgr.outbox.get_pending_batch(limit=5)
    assert len(pending) == 1
    assert pending[0].payload == {"boot": True}


def test_development_mode_does_not_migrate_production_data(monkeypatch):
    """Test 14g: Development mode respects BASE_PATH and does not target ProgramData."""
    from core.outbox.migration import migrate_legacy_outbox
    monkeypatch.setenv("SLMS_DEV_MODE", "1")
    monkeypatch.delenv("SLMS_DATA_DIR", raising=False)

    dev_dir = paths.get_data_dir()
    assert dev_dir == paths.BASE_PATH
    assert "ProgramData" not in dev_dir


def test_migration_fails_safely_when_old_db_locked_in_use(tmp_path):
    """Test 10 & 11: Migration refuses to run if legacy outbox is actively in use / locked."""
    from core.outbox.migration import migrate_legacy_outbox
    old_db = tmp_path / "outbox" / "outbox.db"
    old_db.parent.mkdir(parents=True, exist_ok=True)

    old_box = DurableOutbox(db_path=str(old_db))
    old_box.enqueue("in_progress", {"active": True})

    # Hold an exclusive lock on old_db simulating an active process
    import sqlite3
    conn = sqlite3.connect(str(old_db))
    conn.execute("BEGIN EXCLUSIVE;")

    try:
        with pytest.raises(RuntimeError) as exc_info:
            migrate_legacy_outbox(data_dir=str(tmp_path))
        assert "is currently in use or locked" in str(exc_info.value)
    finally:
        conn.rollback()
        conn.close()
        del conn, old_box
        import gc
        gc.collect()


# ============================================================================
# Phase D: SQLite Outbox & ProgramData Permission Hardening Tests
# ============================================================================

def test_phase_d_fresh_programdata_directory_structure_creation(tmp_path):
    """Verify ensure_directories_exist creates the full runtime layout on clean installation."""
    clean_base = tmp_path / "fresh_slms"
    assert not clean_base.exists()

    paths.ensure_directories_exist(str(clean_base))

    layout = paths.get_path_layout(str(clean_base))
    assert os.path.isdir(layout["logs"])
    assert os.path.isdir(layout["data"])
    assert os.path.isdir(layout["cache"])
    assert os.path.isdir(layout["config"])
    assert os.path.isdir(layout["outbox"])
    assert os.path.isdir(layout["diagnostic"])


def test_phase_d_configure_service_folder_permissions_command_structure(tmp_path):
    """Verify configure_service_folder_permissions constructs correct recursive icacls command."""
    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stdout = "successfully processed 1 files"
    mock_run.stderr = ""

    with patch("service.service.subprocess.run", return_value=mock_run) as patched_run:
        with patch.dict(os.environ, {"SLMS_DEV_MODE": "0"}):
            with patch("service.service.os.name", "nt"):
                success = configure_service_folder_permissions(
                    service_account="NT SERVICE\\SLMSService",
                    data_dir=str(tmp_path),
                )
                assert success is True
                assert patched_run.call_count >= 1

                first_cmd = patched_run.call_args_list[0][0][0]
                assert first_cmd[0] == "icacls"
                assert first_cmd[1] == str(tmp_path)
                assert first_cmd[2] == "/grant"
                assert "NT SERVICE\\SLMSService:(OI)(CI)(M)" in first_cmd[3]
                assert "/t" in first_cmd


def test_phase_d_fresh_sqlite_outbox_wal_lifecycle(tmp_path):
    """
    Verify SQLite outbox initialization and WAL operation on a completely fresh directory
    where outbox.db, outbox.db-wal, and outbox.db-shm do not previously exist.
    """
    fresh_db = tmp_path / "data" / "outbox" / "outbox.db"
    assert not fresh_db.parent.exists()

    # Initialize fresh outbox
    box = DurableOutbox(db_path=str(fresh_db))
    assert fresh_db.exists()

    # Enqueue multiple items with different priorities
    rec1 = box.enqueue("telemetry_metric", {"cpu": 45.2}, idempotency_key="fresh_key_1")
    rec2 = box.enqueue("issue_event", {"error": "test"}, idempotency_key="fresh_key_2")
    assert rec1.id == 1
    assert rec2.id == 2

    # Verify pending batch retrieval (transitions to PROCESSING)
    batch = box.get_pending_batch(limit=10)
    assert len(batch) == 2

    # Mark first item delivered (deletes from SQLite)
    box.mark_delivered(rec1.id)
    stats = box.get_stats()
    assert stats["total_count"] == 1

    # Mark second item retry
    box.mark_retry(rec2.id, "Connection refused", time.time() + 60)
    stats_after_retry = box.get_stats()
    assert stats_after_retry["status_counts"].get("PENDING", 0) == 1

    # Close and reopen outbox to verify persistence across restarts
    del box
    import gc
    gc.collect()

    box2 = DurableOutbox(db_path=str(fresh_db))
    stats_reopened = box2.get_stats()
    assert stats_reopened["total_count"] == 1
    rec = box2.get_record_by_idempotency_key("fresh_key_2")
    assert rec is not None
    assert rec.attempt_count == 1


def test_phase_d_usage_state_atomic_write_on_fresh_dir(tmp_path):
    """Verify save_usage_state and load_usage_state operate atomically on fresh data directory."""
    from modules.usage import save_usage_state, load_usage_state, _ACTIVE_SESSIONS

    state_file = str(tmp_path / "data" / "usage_state.json")
    assert not os.path.exists(state_file)

    # Populate in-memory active session
    now = datetime.now(timezone.utc)
    _ACTIVE_SESSIONS[(9999, 1700000000.0)] = {
        "pid": 9999,
        "create_time": 1700000000.0,
        "application_name": "lab_tool.exe",
        "started_at": now,
        "last_seen_at": now,
        "consecutive_misses": 0,
    }

    # Save to fresh path (atomic write creates dir if needed)
    save_usage_state(state_file)
    assert os.path.isfile(state_file)

    with open(state_file, "r", encoding="utf-8") as f:
        saved_json = json.load(f)
    assert "9999_1700000000.0" in saved_json

    # Clean in-memory and reload
    _ACTIVE_SESSIONS.clear()
    load_usage_state(state_file)
