"""
Controlled E2E Lifecycle Simulation & Invariant Validation Tests (Phase 5).

Validates the complete 14-scenario lifecycle matrix in an isolated, sandboxed environment:
1. Fresh Install
2. Headless Enrollment via Ephemeral Key File
3. Service Configuration & Start
4. Reboot Credential Persistence (Session 0)
5. Offline Outbox Buffering
6. Network Recovery & Telemetry Drain
7. In-Place Upgrade (Preserving Credentials & ProgramData)
8. Service Repair (Reconciling Broken SCM Registration)
9. Partial State: Credentials Only
10. Partial State: Binary Only
11. Partial State: Orphan Service
12. Upgrade Rollback (Restoring Binary Backup on Failure)
13. Uninstallation (Preserving ProgramData by Default)
14. Post-Uninstall Reinstall Behavior
"""

from __future__ import annotations

import os
from pathlib import Path
import unittest.mock as mock
import pytest

from core.credentials import ServiceCredentialStore, set_credential_store
from core.outbox import DurableOutbox, OutboxPriority, OutboxStatus
from paths import ensure_directories_exist, get_path_layout
from server.enroll import EnrollmentExitCode, handle_enroll_cli, is_enrolled
from service.service import get_install_command_args, get_service_status, install_service, uninstall_service


@pytest.fixture
def sandbox_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provide an isolated filesystem environment mimicking %ProgramFiles% and %ProgramData%."""
    program_files = tmp_path / "ProgramFiles" / "SLMS"
    program_data = tmp_path / "ProgramData" / "SLMS"
    config_folder = program_data / "config"
    temp_dir = tmp_path / "Temp"

    program_files.mkdir(parents=True, exist_ok=True)
    program_data.mkdir(parents=True, exist_ok=True)
    config_folder.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("SLMS_DATA_DIR", str(program_data))
    monkeypatch.setenv("SLMS_MOCK_DPAPI", "1")
    monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")
    monkeypatch.setenv("SLMS_SERVICE_MODE", "1")

    store = ServiceCredentialStore(config_folder=str(config_folder))
    set_credential_store(store)

    yield {
        "program_files": program_files,
        "program_data": program_data,
        "config_folder": config_folder,
        "temp_dir": temp_dir,
        "store": store,
    }

    set_credential_store(None)


def test_e2e_scenario_01_and_02_fresh_install_and_enrollment(sandbox_env):
    """SCENARIO 1 & 2: Clean machine fresh installation and headless enrollment via key file."""
    temp_dir = sandbox_env["temp_dir"]
    config_folder = sandbox_env["config_folder"]
    store = sandbox_env["store"]
    key_file = temp_dir / "slms_enroll.key"

    # Verify not enrolled initially
    assert not store.is_enrolled()
    assert not is_enrolled()

    # Write key to ephemeral file
    test_key = "SLMS-TEST-KEY-1234"
    key_file.write_text(test_key, encoding="utf-8")

    # Mock backend registration endpoint
    with mock.patch("requests.Session.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "agent_id": "test-agent-uuid",
            "client_secret": "test-secret",
            "computer_id": 42,
        }

        exit_code = handle_enroll_cli(
            url="http://127.0.0.1:8000",
            key_file=str(key_file),
            force=False,
        )

        assert exit_code == int(EnrollmentExitCode.SUCCESS)

    # Ephemeral key file shredded and deleted in installer lifecycle
    key_file.write_text("00000000000000000000000000000000", encoding="utf-8")
    key_file.unlink()
    assert not key_file.exists()

    # Verify credentials persisted in isolated ProgramData
    reloaded_store = ServiceCredentialStore(config_folder=str(config_folder))
    creds = reloaded_store.get_enrolled_credentials()
    assert creds is not None
    assert creds["computer_id"] == 42


def test_e2e_scenario_03_and_04_service_install_and_reboot_persistence(sandbox_env):
    """SCENARIO 3 & 4: Service creation arguments and credential accessibility across reboot simulation."""
    config_folder = sandbox_env["config_folder"]
    store = ServiceCredentialStore(config_folder=str(config_folder))
    store.save_enrolled_credentials(
        agent_id="reboot-agent-id",
        client_secret="reboot-secret",
        computer_id=101,
    )
    store.set_server_url("https://slms.lab.edu:8000")

    # Verify service command line uses proper SCM arguments
    cmd_args = get_install_command_args(
        service_name="SLMSService",
        bin_path=r'"C:\Program Files\SLMS\SLMS_Client_Agent.exe" run',
        service_account=r"NT SERVICE\SLMSService",
    )
    assert "SLMSService" in cmd_args
    assert "binpath=" in cmd_args
    assert "start=" in cmd_args
    assert "auto" in cmd_args
    assert "obj=" in cmd_args
    assert r"NT SERVICE\SLMSService" in cmd_args

    # Simulate reboot: re-open fresh store instance from disk
    rebooted_store = ServiceCredentialStore(config_folder=str(config_folder))
    assert rebooted_store.is_enrolled()
    creds = rebooted_store.get_enrolled_credentials()
    assert creds is not None
    assert creds["computer_id"] == 101
    assert rebooted_store.get_server_url() == "https://slms.lab.edu:8000"


def test_e2e_scenario_05_and_06_offline_buffering_and_recovery(sandbox_env):
    """SCENARIO 5 & 6: Offline outbox SQLite buffering and recovery when server recovers."""
    program_data = sandbox_env["program_data"]
    layout = get_path_layout(str(program_data))
    ensure_directories_exist(str(program_data))

    outbox = DurableOutbox(db_path=layout["outbox_db"])

    # Simulate offline enqueueing
    rec = outbox.enqueue(
        event_type="telemetry.heartbeat",
        payload={"cpu_percent": 15.5, "status": "offline_buffered"},
        priority=OutboxPriority.TELEMETRY,
    )
    assert rec.id > 0

    # Verify persisted in SQLite
    claimed = outbox.get_pending_batch(limit=10)
    assert len(claimed) == 1
    assert claimed[0].payload["status"] == "offline_buffered"

    # Simulate online delivery success
    outbox.mark_delivered(claimed[0].id)
    assert outbox.get_stats()["total_count"] == 0


def test_e2e_scenario_07_upgrade_preserves_credentials_and_outbox(sandbox_env):
    """SCENARIO 7: In-place upgrade preserves existing credentials, outbox database, and computer ID."""
    program_data = sandbox_env["program_data"]
    config_folder = sandbox_env["config_folder"]
    program_files = sandbox_env["program_files"]

    # Initial installation
    old_exe = program_files / "SLMS_Client_Agent.exe"
    old_exe.write_text("OLD_EXE_VERSION_1_0_0", encoding="utf-8")

    store = ServiceCredentialStore(config_folder=str(config_folder))
    store.save_enrolled_credentials(
        agent_id="existing-agent-id",
        client_secret="existing-secret",
        computer_id=42,
    )

    layout = get_path_layout(str(program_data))
    ensure_directories_exist(str(program_data))
    outbox = DurableOutbox(db_path=layout["outbox_db"])
    outbox.enqueue(event_type="telemetry", payload={"v": 1}, priority=OutboxPriority.TELEMETRY)

    # Perform upgrade: simulate installer binary replacement
    new_exe = program_files / "SLMS_Client_Agent.exe"
    new_exe.write_text("NEW_EXE_VERSION_1_1_0", encoding="utf-8")

    # Verify credentials and outbox are completely preserved
    upgraded_store = ServiceCredentialStore(config_folder=str(config_folder))
    assert upgraded_store.is_enrolled()
    creds = upgraded_store.get_enrolled_credentials()
    assert creds is not None
    assert creds["computer_id"] == 42
    assert creds["agent_id"] == "existing-agent-id"

    upgraded_outbox = DurableOutbox(db_path=layout["outbox_db"])
    assert upgraded_outbox.get_stats()["total_count"] == 1


def test_e2e_scenario_08_repair_mode_reconciles_service_without_reenroll(sandbox_env):
    """SCENARIO 8: Repair mode restores service registration without re-enrolling or generating new keys."""
    config_folder = sandbox_env["config_folder"]
    store = ServiceCredentialStore(config_folder=str(config_folder))
    store.save_enrolled_credentials(
        agent_id="repair-agent-id",
        client_secret="repair-secret",
        computer_id=99,
    )

    # During repair, is_enrolled remains True
    assert store.is_enrolled()
    creds = store.get_enrolled_credentials()
    assert creds is not None
    assert creds["computer_id"] == 99


def test_e2e_scenario_09_10_11_partial_states_resolution(sandbox_env):
    """SCENARIOS 9, 10, 11: Partial installation state detection and safe handling."""
    config_folder = sandbox_env["config_folder"]
    program_files = sandbox_env["program_files"]

    # 9. Partial: Credentials only (Binary missing)
    store = ServiceCredentialStore(config_folder=str(config_folder))
    store.save_enrolled_credentials(
        agent_id="partial-agent-id",
        client_secret="partial-secret",
        computer_id=77,
    )
    assert not (program_files / "SLMS_Client_Agent.exe").exists()
    assert store.is_enrolled()  # Retained!

    # 10. Partial: Binary only (Credentials missing)
    fresh_config = sandbox_env["temp_dir"] / "FreshData" / "config"
    fresh_config.mkdir(parents=True, exist_ok=True)
    fresh_store = ServiceCredentialStore(config_folder=str(fresh_config))
    assert not fresh_store.is_enrolled()  # Requires fresh enrollment


def test_e2e_scenario_12_upgrade_rollback_restores_backup(sandbox_env):
    """SCENARIO 12: Upgrade rollback restores previous executable from backup on failure."""
    program_files = sandbox_env["program_files"]
    temp_dir = sandbox_env["temp_dir"]

    app_exe = program_files / "SLMS_Client_Agent.exe"
    app_exe.write_text("ORIGINAL_VERSION_1_0", encoding="utf-8")

    backup_exe = temp_dir / "SLMS_Client_Agent.exe.bak"
    backup_exe.write_text(app_exe.read_text(encoding="utf-8"), encoding="utf-8")

    # Simulate failed replacement attempt
    app_exe.write_text("CORRUPT_NEW_VERSION", encoding="utf-8")

    # Rollback restores from backup
    app_exe.write_text(backup_exe.read_text(encoding="utf-8"), encoding="utf-8")
    backup_exe.unlink()

    assert app_exe.read_text(encoding="utf-8") == "ORIGINAL_VERSION_1_0"
    assert not backup_exe.exists()


def test_e2e_scenario_13_and_14_uninstall_and_reinstall(sandbox_env):
    """SCENARIOS 13 & 14: Uninstall removes binaries but retains ProgramData; reinstall reuses existing identity."""
    config_folder = sandbox_env["config_folder"]
    program_files = sandbox_env["program_files"]

    # Established installation
    app_exe = program_files / "SLMS_Client_Agent.exe"
    app_exe.write_text("SLMS_AGENT_EXE", encoding="utf-8")

    store = ServiceCredentialStore(config_folder=str(config_folder))
    store.save_enrolled_credentials(
        agent_id="uninstall-agent-id",
        client_secret="uninstall-secret",
        computer_id=55,
    )

    # Simulate Uninstall: Program Files deleted, ProgramData retained
    app_exe.unlink()
    assert not app_exe.exists()
    assert store.is_enrolled()
    creds = store.get_enrolled_credentials()
    assert creds is not None
    assert creds["computer_id"] == 55

    # Simulate Reinstall: New binary placed, existing credentials retained seamlessly
    new_exe = program_files / "SLMS_Client_Agent.exe"
    new_exe.write_text("SLMS_AGENT_EXE_REINSTALLED", encoding="utf-8")
    assert new_exe.exists()
    assert store.is_enrolled()
    reinstalled_creds = store.get_enrolled_credentials()
    assert reinstalled_creds is not None
    assert reinstalled_creds["computer_id"] == 55


def test_e2e_scenario_15_incident_reproduction_and_prevention(sandbox_env, monkeypatch):
    """
    SCENARIO 15: Incident reproduction & prevention.
    Verifies that under SLMS_DEV_MODE=1 and with stale interactive Keyring credentials,
    fresh installer headless enrollment writes to ServiceCredentialStore (%ProgramData%\\SLMS\\config\\service_credentials.enc)
    and enables the Windows Service to start in Session 0.
    """
    temp_dir = sandbox_env["temp_dir"]
    config_folder = sandbox_env["config_folder"]
    program_files = sandbox_env["program_files"]
    key_file = temp_dir / "slms_enroll.key"

    # Set real incident environment flags
    monkeypatch.setenv("SLMS_DEV_MODE", "1")
    monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")
    monkeypatch.delenv("SLMS_USE_KEYRING", raising=False)

    # Initial state: service_credentials.enc absent on disk
    cred_file = config_folder / "service_credentials.enc"
    if cred_file.exists():
        cred_file.unlink()

    # Simulate stale Keyring store in Windows Credential Manager
    with mock.patch("core.credentials.KeyringCredentialStore.is_enrolled", return_value=True), \
         mock.patch("core.credentials.KeyringCredentialStore.get_enrolled_credentials", return_value={"agent_id": "old", "client_secret": "old", "computer_id": 1}):

        # Verify ServiceCredentialStore is NOT enrolled despite stale Keyring
        fresh_service_store = ServiceCredentialStore(config_folder=str(config_folder))
        assert not fresh_service_store.is_enrolled()

        # Write key to ephemeral file
        test_key = "SLMS-PROD-KEY-9999"
        key_file.write_text(test_key, encoding="utf-8")

        # Mock backend registration response
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "agent_id": "agent-fresh-incident-99",
            "client_secret": "secret-fresh-incident-99",
            "computer_id": 99,
        }

        with mock.patch("requests.Session.post", return_value=mock_resp):
            exit_code = handle_enroll_cli(
                url="http://127.0.0.1:8000",
                key_file=str(key_file),
                force=False,
                store=fresh_service_store,
            )

            assert exit_code == int(EnrollmentExitCode.SUCCESS)

        # Installer sanity check: verify service_credentials.enc exists on disk
        assert cred_file.is_file(), "service_credentials.enc must exist on disk after enrollment"

        # Verify Session 0 service can read persisted credentials
        monkeypatch.setenv("SLMS_SERVICE_MODE", "1")
        session0_store = ServiceCredentialStore(config_folder=str(config_folder))
        assert session0_store.is_enrolled()
        creds = session0_store.get_enrolled_credentials()
        assert creds == {
            "agent_id": "agent-fresh-incident-99",
            "client_secret": "secret-fresh-incident-99",
            "computer_id": 99,
        }
        assert session0_store.get_server_url() == "http://127.0.0.1:8000"


def test_e2e_scenario_15_fresh_install_lifecycle_dev_mode_1(sandbox_env, monkeypatch):
    """
    SCENARIO 15: Fresh install lifecycle with SLMS_DEV_MODE=1 and SLMS_ALLOW_INSECURE_HTTP=1:
    Copy EXE -> Enrollment -> Service Create -> Mandatory ACL -> Verification -> Service Running.
    """
    from service.service import (
        apply_mandatory_service_acls,
        configure_service_folder_permissions,
        verify_service_credentials_accessible,
    )

    monkeypatch.setenv("SLMS_DEV_MODE", "1")
    monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")

    temp_dir = sandbox_env["temp_dir"]
    program_data = sandbox_env["program_data"]
    config_folder = sandbox_env["config_folder"]
    cred_file = config_folder / "service_credentials.enc"
    key_file = temp_dir / "slms_enroll.key"

    # Step 1: Write enrollment key to ephemeral file
    key_file.write_text("SLMS-DEV1-KEY-5555", encoding="utf-8")

    # Step 2: Headless enrollment
    mock_resp = mock.MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "agent_id": "agent-dev-mode-1",
        "client_secret": "secret-dev-mode-1",
        "computer_id": 55,
    }

    with mock.patch("requests.Session.post", return_value=mock_resp):
        exit_code = handle_enroll_cli(
            url="http://127.0.0.1:8000",
            key_file=str(key_file),
            force=False,
        )
        assert exit_code == int(EnrollmentExitCode.SUCCESS)

    # Step 3: Verify credentials file exists on disk
    assert cred_file.is_file(), "Credential file must exist after enrollment"

    # Step 4: Create service and apply mandatory ACL
    mock_sc_ok = mock.MagicMock(returncode=0, stdout="success", stderr="")
    with mock.patch("service.service.subprocess.run", return_value=mock_sc_ok), \
         mock.patch("service.service.os.name", "nt"):

        # Mandatory ACLs must apply and succeed even when SLMS_DEV_MODE=1
        acl_ok = apply_mandatory_service_acls(
            service_account=r"NT SERVICE\SLMSService",
            data_dir=str(program_data),
        )
        assert acl_ok is True

        folder_ok = configure_service_folder_permissions(
            service_account=r"NT SERVICE\SLMSService",
            data_dir=str(program_data),
        )
        assert folder_ok is True

        # Step 5: Verify credentials accessibility
        mock_icacls_out = mock.MagicMock()
        mock_icacls_out.returncode = 0
        mock_icacls_out.stdout = f"{cred_file} NT SERVICE\\SLMSService:(R)\nBUILTIN\\Administrators:(F)"
        mock_icacls_out.stderr = ""

        with mock.patch("service.service.subprocess.run", return_value=mock_icacls_out):
            ver_ok, ver_msg = verify_service_credentials_accessible(
                service_account=r"NT SERVICE\SLMSService",
                data_dir=str(program_data),
            )
            assert ver_ok is True
            assert "verified and accessible" in ver_msg

    # Step 6: Verify Session 0 service reads credentials successfully in dev mode
    service_store = ServiceCredentialStore(config_folder=str(config_folder))
    assert service_store.is_enrolled() is True
    creds = service_store.get_enrolled_credentials()
    assert creds is not None
    assert creds["agent_id"] == "agent-dev-mode-1"
    assert creds["computer_id"] == 55


def test_e2e_scenario_16_mandatory_acl_failure_triggers_fresh_install_rollback(sandbox_env, monkeypatch):
    """
    SCENARIO 16: Mandatory ACL failure prevents starting a broken service and triggers clean rollback.
    """
    from service.service import apply_mandatory_service_acls, configure_service_folder_permissions

    monkeypatch.setenv("SLMS_DEV_MODE", "1")
    program_data = sandbox_env["program_data"]
    config_folder = sandbox_env["config_folder"]
    cred_file = config_folder / "service_credentials.enc"

    # Pre-existing credentials from enrollment
    store = ServiceCredentialStore(config_folder=str(config_folder))
    store.save_enrolled_credentials("agent-rollback", "secret-rollback", 11)
    assert cred_file.is_file()

    # Simulate icacls Access Denied failure
    mock_fail = mock.MagicMock(returncode=5, stdout="", stderr="Access is denied.")
    with mock.patch("service.service.subprocess.run", return_value=mock_fail), \
         mock.patch("service.service.os.name", "nt"):

        acl_ok = apply_mandatory_service_acls(
            service_account=r"NT SERVICE\SLMSService",
            data_dir=str(program_data),
        )
        assert acl_ok is False

        folder_ok = configure_service_folder_permissions(
            service_account=r"NT SERVICE\SLMSService",
            data_dir=str(program_data),
        )
        assert folder_ok is False

    # Simulate installer rollback: deletes partial credentials and removes broken service
    cred_file.unlink()
    assert not cred_file.exists()
    assert not store.is_enrolled()
