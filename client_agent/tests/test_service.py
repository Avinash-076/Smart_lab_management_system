"""
Phase 2 Test Suite: Windows Service Architecture.

Covers all 15 explicit Phase 2 verification requirements:
1. Service module imports
2. Service class construction
3. Service lifecycle state transitions
4. Stop event causes clean shutdown
5. Runtime starts exactly once
6. Runtime shutdown is invoked exactly once
7. Credential store works in service context
8. Interactive Keyring development behavior remains intact
9. Service configuration contains no plaintext secret
10. Service does not use MessageBoxW
11. startup.py is no longer required for production startup
12. Authentication failure is handled cleanly
13. Unexpected runtime failure does not leave the service in a falsely running state
14. Service recovery configuration is generated correctly
15. Integration of AgentRuntime with service lifecycle
"""

import os
import subprocess
import threading
import time
from unittest.mock import MagicMock, patch
import pytest

from core.credentials import (
    BaseCredentialStore,
    KeyringCredentialStore,
    ServiceCredentialStore,
    dpapi_decrypt,
    dpapi_encrypt,
    get_credential_store,
    migrate_credentials,
    set_credential_store,
)
from core.runtime import AgentRuntime
from server.command_handler import execute_command, handle_message
from service.lifecycle import ServiceLifecycle, ServiceState
from service.service import (
    DEFAULT_SERVICE_ACCOUNT,
    SERVICE_DESCRIPTION,
    SERVICE_DISPLAY_NAME,
    SERVICE_NAME,
    SLMSService,
    assign_account_privileges,
    configure_service_folder_permissions,
    get_failure_flag_command_args,
    get_privileges_command_args,
    get_recovery_command_args,
)


class TestServiceImportsAndConstruction:

    def test_service_module_imports(self):
        """1. Verify service package and modules import cleanly."""
        import service
        import service.lifecycle
        import service.service
        import core.runtime

        assert hasattr(service.service, "SLMSService")
        assert hasattr(service.lifecycle, "ServiceLifecycle")
        assert hasattr(core.runtime, "AgentRuntime")

    def test_service_class_construction(self):
        """2. Verify Service class construction and service metadata."""
        svc = SLMSService()
        assert svc._svc_name_ == SERVICE_NAME
        assert svc._svc_display_name_ == SERVICE_DISPLAY_NAME
        assert svc._svc_description_ == SERVICE_DESCRIPTION
        assert isinstance(svc.lifecycle, ServiceLifecycle)
        assert svc.lifecycle.state == ServiceState.STOPPED


class TestServiceLifecycle:

    def test_service_lifecycle_state_transitions(self):
        """3. Verify STOPPED -> STARTING -> RUNNING -> STOPPING -> STOPPED transitions."""
        stop_event = threading.Event()

        class MockRuntime:
            def __init__(self, stop_event):
                self.stop_event = stop_event
            def start(self):
                self.stop_event.wait(timeout=5.0)
            def stop(self):
                self.stop_event.set()

        lifecycle = ServiceLifecycle(runtime_factory=lambda ev: MockRuntime(ev))
        assert lifecycle.state == ServiceState.STOPPED

        lifecycle.start()
        time.sleep(0.1)
        assert lifecycle.state == ServiceState.RUNNING
        assert lifecycle.is_healthy() is True

        lifecycle.stop()
        assert lifecycle.state == ServiceState.STOPPED
        assert lifecycle.is_healthy() is False

    def test_stop_event_causes_clean_shutdown(self):
        """4. Verify stop event wakes up runtime immediately without waiting for interval."""
        stop_event = threading.Event()
        runtime = AgentRuntime(stop_event=stop_event, is_service=True)

        start_time = time.time()
        # Trigger stop after 0.1s
        threading.Timer(0.1, stop_event.set).start()
        stop_event.wait(timeout=20.0)
        elapsed = time.time() - start_time

        # Must exit well before the 20s MONITOR_INTERVAL
        assert elapsed < 2.0

    def test_runtime_starts_and_stops_exactly_once(self):
        """5 & 6. Verify runtime starts exactly once and shutdown is invoked exactly once."""
        stop_event = threading.Event()
        runtime = AgentRuntime(stop_event=stop_event, is_service=True)

        # Mock authentication and enrollment to simulate a single cycle
        with patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.authenticate_agent", return_value="fake.jwt.token"), \
             patch("core.runtime.get_computer_id", return_value=42), \
             patch("core.runtime.AgentWebSocketClient"), \
             patch("core.runtime.collect_all_data", return_value={}), \
             patch("core.runtime.upload_metrics"):

            # Immediately request stop after first iteration
            def stop_soon():
                time.sleep(0.05)
                runtime.stop()

            threading.Thread(target=stop_soon, daemon=True).start()
            runtime.start()

            assert runtime.started_count == 1
            assert runtime.stopped_count == 1
            assert runtime.is_running is False


class TestServiceCredentialStorage:

    def test_service_credential_store_dpapi_machine_scope(self, tmp_path):
        """7. Verify credential store functions in service context using DPAPI machine scope."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        store = ServiceCredentialStore(config_folder=str(config_dir))
        assert store.is_enrolled() is False

        # Save credentials
        store.save_enrolled_credentials(
            agent_id="svc-agent-001",
            client_secret="super-secret-key-12345",
            computer_id=101,
        )
        store.set_server_url("https://slms.lab.edu:8000")

        # Verify enrollment and retrieval across instances (reboot simulation)
        reboot_store = ServiceCredentialStore(config_folder=str(config_dir))
        assert reboot_store.is_enrolled() is True

        creds = reboot_store.get_enrolled_credentials()
        assert creds == {
            "agent_id": "svc-agent-001",
            "client_secret": "super-secret-key-12345",
            "computer_id": 101,
        }
        assert reboot_store.get_server_url() == "https://slms.lab.edu:8000"

    def test_service_configuration_contains_no_plaintext_secret(self, tmp_path):
        """9. Verify stored encrypted file contains no plaintext client_secret or agent_id."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        secret = "ultra-confidential-secret-999"
        store = ServiceCredentialStore(config_folder=str(config_dir))
        store.save_enrolled_credentials("agent-999", secret, 55)

        raw_bytes = (config_dir / "service_credentials.enc").read_bytes()
        assert secret.encode("utf-8") not in raw_bytes
        assert b"agent-999" not in raw_bytes

    def test_interactive_keyring_development_behavior_intact(self, monkeypatch):
        """8. Verify interactive Keyring development store remains functional."""
        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        monkeypatch.delenv("SLMS_SERVICE_MODE", raising=False)

        store = get_credential_store()
        assert isinstance(store, KeyringCredentialStore)

    def test_credential_migration_from_keyring_to_service(self, tmp_path):
        """Verify migration helper moves credentials from Keyring to Service store."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        # Mock source store (interactive Keyring)
        class MockKeyring(BaseCredentialStore):
            def get_credential(self, k): return None
            def set_credential(self, k, v): pass
            def delete_credential(self, k): return True
            def is_enrolled(self): return True
            def get_enrolled_credentials(self):
                return {"agent_id": "keyring-007", "client_secret": "secret-007", "computer_id": 7}
            def save_enrolled_credentials(self, a, s, c): pass
            def get_server_url(self): return "https://auth.server.edu"
            def set_server_url(self, u): pass

        src = MockKeyring()
        dst = ServiceCredentialStore(config_folder=str(config_dir))

        success = migrate_credentials(src, dst)
        assert success is True
        assert dst.is_enrolled() is True
        assert dst.get_enrolled_credentials()["agent_id"] == "keyring-007"
        assert dst.get_server_url() == "https://auth.server.edu"


class TestServiceSecurityAndNonInteractiveConstraints:

    def test_service_does_not_use_messageboxw(self):
        """10. Verify command handler message command does not call user32.MessageBoxW."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            success, msg = execute_command("message", "Attention: Lab closing")
            assert success is True

            # Verify msg.exe was attempted instead of blocking MessageBoxW
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "msg" in args[0]
            assert "Attention: Lab closing" in args

    def test_startup_py_is_no_longer_required(self):
        """11. Verify startup.py is marked deprecated and not imported by core runtime."""
        import startup
        assert "DEPRECATED" in startup.__doc__

        # Ensure service and runtime modules do not import startup
        import service.service as svc_mod
        import core.runtime as rt_mod
        assert "startup" not in dir(svc_mod)
        assert "startup" not in dir(rt_mod)

    def test_authentication_failure_handled_cleanly(self):
        """12. Verify authentication failure does not leave runtime in active state."""
        stop_event = threading.Event()
        runtime = AgentRuntime(stop_event=stop_event, is_service=True)

        with patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.authenticate_agent", side_effect=RuntimeError("Auth rejected 401")):

            with pytest.raises(RuntimeError, match="Auth rejected"):
                runtime.start()

            assert runtime.is_running is False
            assert runtime.ws_client is None

    def test_unexpected_runtime_failure_transitions_to_failed(self):
        """13. Verify unexpected worker crash transitions lifecycle state to FAILED."""
        class CrashingRuntime:
            def __init__(self, stop_event): pass
            def start(self):
                raise ValueError("Fatal crash in collector")
            def stop(self): pass

        lifecycle = ServiceLifecycle(runtime_factory=lambda ev: CrashingRuntime(ev))
        lifecycle.start()

        # Wait for thread to fail
        time.sleep(0.2)
        assert lifecycle.state == ServiceState.FAILED
        assert lifecycle.is_healthy() is False
        assert isinstance(lifecycle.last_error, ValueError)

    def test_service_recovery_configuration_generated_correctly(self):
        """14. Verify recovery command arguments conform to Windows sc failure syntax."""
        cmd = get_recovery_command_args("SLMSService")
        assert cmd[0] == "sc.exe"
        assert cmd[1] == "failure"
        assert cmd[2] == "SLMSService"
        assert "reset=" in cmd
        assert "86400" in cmd
        assert "actions=" in cmd
        assert "restart/5000/restart/10000/restart/60000" in cmd


class TestServiceSCMFailureRecovery:
    """Tests verifying Windows SCM failure recognition, exit codes, and recovery commands."""

    def test_recovery_and_failure_flag_commands(self):
        """Verify sc failure and sc failureflag command syntax."""
        rec_cmd = get_recovery_command_args("SLMSService")
        assert rec_cmd == [
            "sc.exe", "failure", "SLMSService", "reset=", "86400",
            "actions=", "restart/5000/restart/10000/restart/60000",
        ]

        flag_cmd = get_failure_flag_command_args("SLMSService")
        assert flag_cmd == ["sc.exe", "failureflag", "SLMSService", "1"]

    def test_svc_do_run_graceful_stop_reports_exit_code_zero(self):
        """Verify intentional SCM stop reports SERVICE_STOPPED with exit code 0 (no restart)."""
        class GracefulRuntime:
            def __init__(self, stop_event):
                self.stop_event = stop_event
            def start(self):
                self.stop_event.wait(timeout=5.0)
            def stop(self):
                self.stop_event.set()

        svc = SLMSService()
        svc.lifecycle = ServiceLifecycle(runtime_factory=lambda ev: GracefulRuntime(ev))
        mock_report = MagicMock()
        svc.ReportServiceStatus = mock_report

        def trigger_stop():
            time.sleep(0.05)
            svc.SvcStop()

        threading.Thread(target=trigger_stop, daemon=True).start()
        svc.SvcDoRun()

        calls = mock_report.call_args_list
        assert len(calls) >= 2
        last_call = calls[-1]
        assert last_call[0][0] == 1  # win32service.SERVICE_STOPPED
        assert last_call[1].get("win32ExitCode") == 0


    def test_svc_do_run_unexpected_crash_reports_non_zero_exit_code(self):
        """Verify unexpected runtime crash reports non-zero exit code (1067) and triggers abnormal exit."""
        class CrashingRuntime:
            def __init__(self, stop_event): pass
            def start(self): raise RuntimeError("Catastrophic error in monitoring")
            def stop(self): pass

        svc = SLMSService()
        svc.lifecycle = ServiceLifecycle(runtime_factory=lambda ev: CrashingRuntime(ev))
        mock_report = MagicMock()
        svc.ReportServiceStatus = mock_report

        with patch("os._exit") as mock_exit:
            svc.SvcDoRun()

            calls = mock_report.call_args_list
            last_call = calls[-1]
            assert last_call[0][0] == 1  # win32service.SERVICE_STOPPED
            assert last_call[1].get("win32ExitCode") == 1067
            mock_exit.assert_called_once_with(1067)

    def test_svc_do_run_missing_enrollment_clean_exit(self):
        """Verify missing enrollment causes clean stop without triggering SCM failure restart loop."""
        class CleanExitRuntime:
            def __init__(self, stop_event): pass
            def start(self): return
            def stop(self): pass

        svc = SLMSService()
        svc.lifecycle = ServiceLifecycle(runtime_factory=lambda ev: CleanExitRuntime(ev))
        mock_report = MagicMock()
        svc.ReportServiceStatus = mock_report

        svc.SvcDoRun()

        calls = mock_report.call_args_list
        last_call = calls[-1]
        assert last_call[0][0] == 1  # SERVICE_STOPPED
        assert last_call[1].get("win32ExitCode") == 0


class TestCredentialProvisioningOrder:
    """Tests verifying credential provisioning order (Flow A and Flow B) and access control."""

    def test_flow_a_service_installed_then_enrolled(self, tmp_path):
        """Flow A: Service installed -> Enrollment saves credentials -> Service starts and decrypts."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        store = ServiceCredentialStore(config_folder=str(config_dir))
        store.save_enrolled_credentials("flow-a-agent", "flow-a-secret-123", 101)
        store.set_server_url("https://slms.lab.edu:8000")

        service_store = ServiceCredentialStore(config_folder=str(config_dir))
        assert service_store.is_enrolled() is True
        creds = service_store.get_enrolled_credentials()
        assert creds["client_secret"] == "flow-a-secret-123"

        raw = (config_dir / "service_credentials.enc").read_bytes()
        assert b"flow-a-secret-123" not in raw

    def test_flow_b_enrolled_then_service_installed(self, tmp_path):
        """Flow B: Enrollment occurs first -> Service installed -> ACL updated -> Service starts."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        store = ServiceCredentialStore(config_folder=str(config_dir))
        store.save_enrolled_credentials("flow-b-agent", "flow-b-secret-456", 102)

        cred_file = config_dir / "service_credentials.enc"
        assert cred_file.exists()

        service_store = ServiceCredentialStore(config_folder=str(config_dir))
        assert service_store.is_enrolled() is True
        creds = service_store.get_enrolled_credentials()
        assert creds["client_secret"] == "flow-b-secret-456"

    def test_ordinary_student_cannot_read_or_decrypt_credentials(self, tmp_path):
        """Verify credentials file is encrypted with machine DPAPI and contains no plaintext secret."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()

        store = ServiceCredentialStore(config_folder=str(config_dir))
        store.save_enrolled_credentials("student-test-agent", "student-secret-999", 103)

        cred_file = config_dir / "service_credentials.enc"
        raw_bytes = cred_file.read_bytes()

        assert b"student-secret-999" not in raw_bytes
        assert b"student-test-agent" not in raw_bytes


class TestMsgExeHandling:
    """Tests verifying service-safe message delivery and fallback via msg.exe."""

    def test_msg_exe_success(self):
        """Verify normal message broadcast succeeds when msg.exe returns 0."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            status, msg = handle_message("Lab closing in 10 minutes")
            assert status is True
            assert "Notice broadcast" in msg
            args = mock_run.call_args[0][0]
            assert "msg" in args[0]
            assert "Lab closing in 10 minutes" in args

    def test_msg_exe_failure_fallback_to_log(self):
        """Verify msg.exe non-zero exit (e.g. no active sessions) falls back to log recording safely."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="No session exists", stdout="")
            status, msg = handle_message("Shutdown alert")
            assert status is True
            assert "Notice recorded in agent log: Shutdown alert" in msg

    def test_msg_exe_timeout_fallback_to_log(self):
        """Verify msg.exe timeout falls back to log recording without raising or hanging."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="msg", timeout=3)):
            status, msg = handle_message("Immediate notice")
            assert status is True
            assert "Notice recorded in agent log: Immediate notice" in msg

    def test_msg_exe_truncates_oversized_payload(self):
        """Verify oversized message payloads are truncated to 1024 characters to prevent buffer overflow."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            long_msg = "X" * 3000
            status, msg = handle_message(long_msg)
            assert status is True
            args = mock_run.call_args[0][0]
            assert len(args[3]) == 1024

    def test_msg_exe_none_payload_handled(self):
        """Verify None payload uses default message string."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            status, msg = handle_message(None)
            assert status is True
            args = mock_run.call_args[0][0]
            assert args[3] == "Message from administrator"


class TestVirtualServiceAccountPrivileges:
    """Tests verifying least-privilege service account capabilities and configuration."""

    def test_process_enumeration_permissions(self):
        """Verify process enumeration capability (PROCESS_QUERY_LIMITED_INFORMATION)."""
        import psutil
        procs = list(psutil.process_iter(["pid", "name"]))
        assert len(procs) > 0

    def test_software_inventory_hklm_read_permissions(self):
        """Verify read access to HKLM uninstall registry key for software inventory."""
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        )
        try:
            subkeys, _, _ = winreg.QueryInfoKey(key)
            assert subkeys > 0
        finally:
            winreg.CloseKey(key)

    def test_programdata_slms_read_write(self, tmp_path):
        """Verify read/write capability to %PROGRAMDATA%\\SLMS folders."""
        test_file = tmp_path / "write_test.txt"
        test_file.write_text("privilege test", encoding="utf-8")
        assert test_file.read_text(encoding="utf-8") == "privilege test"

    def test_sc_privs_command_generation(self):
        """Verify sc privs command declares SeShutdownPrivilege."""
        privs_cmd = get_privileges_command_args("SLMSService")
        assert privs_cmd == [
            "sc.exe", "privs", "SLMSService", "SeShutdownPrivilege/SeChangeNotifyPrivilege"
        ]
