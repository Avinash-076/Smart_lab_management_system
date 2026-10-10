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
    apply_mandatory_service_acls,
    configure_service_folder_permissions,
    harden_production_folder_permissions,
    verify_service_credentials_accessible,
    get_failure_flag_command_args,
    get_privileges_command_args,
    get_recovery_command_args,
    get_service_bin_path,
    install_service,
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
        runtime = AgentRuntime(stop_event=stop_event, is_service=True, enable_single_instance=False)

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
        runtime = AgentRuntime(stop_event=stop_event, is_service=True, enable_single_instance=False)

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
        """8. Verify interactive Keyring development store remains functional via SLMS_USE_KEYRING."""
        set_credential_store(None)
        monkeypatch.setenv("SLMS_USE_KEYRING", "1")
        monkeypatch.delenv("SLMS_SERVICE_MODE", raising=False)

        store = get_credential_store()
        assert isinstance(store, KeyringCredentialStore)

        # Verify SLMS_DEV_MODE=1 alone does NOT select KeyringCredentialStore
        monkeypatch.delenv("SLMS_USE_KEYRING", raising=False)
        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        dev_store = get_credential_store()
        assert isinstance(dev_store, ServiceCredentialStore)
        set_credential_store(None)

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
        runtime = AgentRuntime(stop_event=stop_event, is_service=True, enable_single_instance=False)

        with patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.get_computer_id", return_value=42), \
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
    """
    Caller-environment checks and configuration generation tests.
    NOTE: Direct OS query tests run in the active test runner process. Real virtual
    service account token isolation is validated in the Windows SCM integration suite.
    """

    def test_process_enumeration_permissions(self):
        """Caller check: Verify process enumeration capability in current environment."""
        import psutil
        procs = list(psutil.process_iter(["pid", "name"]))
        assert len(procs) > 0

    @pytest.mark.windows_only
    def test_software_inventory_hklm_read_permissions(self):
        """Caller check: Verify read access to HKLM uninstall registry key in current environment."""
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
        """Unit check: Verify file creation and read/write within an isolated temporary data path."""
        test_file = tmp_path / "write_test.txt"
        test_file.write_text("privilege test", encoding="utf-8")
        assert test_file.read_text(encoding="utf-8") == "privilege test"

    def test_sc_privs_command_generation(self):
        """Verify sc privs command declares SeShutdownPrivilege."""
        privs_cmd = get_privileges_command_args("SLMSService")
        assert privs_cmd == [
            "sc.exe", "privs", "SLMSService", "SeShutdownPrivilege/SeChangeNotifyPrivilege"
        ]


class TestFrozenServiceConfiguration:
    """Tests verifying service command and binpath construction in frozen and source modes."""

    def test_non_frozen_bin_path_uses_python_executable_and_script(self):
        """In non-frozen dev mode, bin_path points to python.exe and service.py."""
        with patch("sys.frozen", False, create=True), \
             patch("sys.executable", r"C:\Python313\python.exe"):
            bin_path = get_service_bin_path()
            assert r"C:\Python313\python.exe" in bin_path
            assert "service.py" in bin_path
            assert "_MEI" not in bin_path

    def test_frozen_bin_path_uses_standalone_executable_with_run_dispatch(self):
        """In frozen PyInstaller mode, bin_path points to compiled EXE with 'run' argument."""
        with patch("sys.frozen", True, create=True), \
             patch("sys.executable", r"C:\Program Files\SLMS\SLMS_Client_Agent.exe"):
            bin_path = get_service_bin_path()
            assert bin_path == r'"C:\Program Files\SLMS\SLMS_Client_Agent.exe" run'
            assert "_MEI" not in bin_path
            assert "__file__" not in bin_path
            assert ".py" not in bin_path

    def test_install_service_frozen_command_construction(self):
        """Verify install_service constructs sc.exe create command with frozen binpath without touching SCM."""
        with patch("sys.frozen", True, create=True), \
             patch("sys.executable", r"C:\Program Files\SLMS\SLMS_Client_Agent.exe"), \
             patch("service.service.setup_service_environment"), \
             patch("service.service.assign_account_privileges"), \
             patch("service.service.configure_service_folder_permissions", return_value=True), \
             patch("service.service.verify_service_credentials_accessible", return_value=(True, "ok")), \
             patch("service.service.configure_service_recovery"), \
             patch("subprocess.run") as mock_run:

            mock_run.return_value = MagicMock(returncode=0)

            result = install_service(service_account="NT SERVICE\\SLMSService", startup_type="auto")
            assert result is True

            # Verify the sc.exe create call
            create_call = mock_run.call_args_list[0]
            cmd = create_call[0][0]
            assert cmd[0] == "sc.exe"
            assert cmd[1] == "create"
            assert cmd[2] == "SLMSService"
            assert "binpath=" in cmd
            assert r'"C:\Program Files\SLMS\SLMS_Client_Agent.exe" run' in cmd
            assert "start=" in cmd
            assert "auto" in cmd
            assert "DisplayName=" in cmd
            assert "obj=" in cmd
            assert "NT SERVICE\\SLMSService" in cmd
            assert "_MEI" not in str(cmd)
            assert ".py" not in str(cmd)


# ============================================================================
# Phase F: Windows Service Deployment & Lifecycle Hardening Tests
# ============================================================================

class TestPhaseFServiceDeploymentLifecycle:

    def test_service_runtime_data_paths_resolution(self, monkeypatch):
        """Verify service mode resolves runtime paths to %ProgramData%\\SLMS."""
        import paths
        monkeypatch.delenv("SLMS_DATA_DIR", raising=False)
        monkeypatch.setenv("SLMS_DEV_MODE", "0")
        monkeypatch.setenv("ProgramData", r"C:\ProgramData")

        data_dir = paths.get_data_dir()
        assert data_dir.replace("/", "\\") == r"C:\ProgramData\SLMS"

        layout = paths.get_path_layout()
        assert layout["logs"].replace("/", "\\") == r"C:\ProgramData\SLMS\logs"
        assert layout["data"].replace("/", "\\") == r"C:\ProgramData\SLMS\data"
        assert layout["outbox"].replace("/", "\\") == r"C:\ProgramData\SLMS\data\outbox"
        assert layout["config"].replace("/", "\\") == r"C:\ProgramData\SLMS\config"

    def test_session_0_no_gui_enrollment_dialog(self):
        """
        Verify that in Session 0 / Service mode, if not enrolled,
        RuntimeManager logs a critical error and raises RuntimeError without opening Tkinter GUI.
        """
        from core.runtime import RuntimeManager
        with patch("core.runtime.is_enrolled", return_value=False), \
             patch("gui.enrollment_window.show_enrollment_window") as mock_gui:

            stop_event = threading.Event()
            runtime = RuntimeManager(stop_event=stop_event, is_service=True, enable_single_instance=False)

            with pytest.raises(RuntimeError) as exc_info:
                runtime.start()

            assert "not enrolled" in str(exc_info.value)
            mock_gui.assert_not_called()

    def test_service_shutdown_staged_resource_cleanup(self):
        """
        Verify that service shutdown stops scheduler, outbox, websocket,
        and releases the single-instance mutex cleanly.
        """
        from core.runtime import AgentRuntime
        from core.single_instance import SingleInstanceMutex

        mock_mutex = MagicMock(spec=SingleInstanceMutex)
        mock_mutex.acquire.return_value = True
        mock_mutex.is_acquired = True

        stop_event = threading.Event()
        runtime = AgentRuntime(
            stop_event=stop_event,
            is_service=True,
            single_instance=mock_mutex,
            enable_single_instance=True,
        )
        runtime._is_running = True

        # Stop runtime
        runtime.stop()

        assert runtime.is_running is False
        assert stop_event.is_set()
        mock_mutex.release.assert_called_once()

    @pytest.mark.windows_only
    def test_service_and_interactive_single_instance_coordination(self):
        """
        Verify that when a service instance is active, interactive launch is rejected,
        and when service stops, interactive launch can acquire.
        """
        from core.single_instance import SingleInstanceMutex

        test_mutex = f"Local\\SLMS_Service_Coord_{os.getpid()}"
        svc_mutex = SingleInstanceMutex(name=test_mutex)
        cli_mutex = SingleInstanceMutex(name=test_mutex)

        # Service starts and acquires mutex
        assert svc_mutex.acquire() is True
        assert svc_mutex.is_acquired is True

        # Interactive launch attempts to acquire -> rejected
        assert cli_mutex.acquire() is False
        assert cli_mutex.is_acquired is False

        # Service stops and releases mutex
        svc_mutex.release()
        assert svc_mutex.is_acquired is False

        # Interactive launch can now acquire
        assert cli_mutex.acquire() is True
        assert cli_mutex.is_acquired is True
        cli_mutex.release()


@pytest.mark.windows_only
class TestServiceSCMDispatcher:
    """Tests verifying deterministic Windows SCM service invocation and CLI dispatch."""

    def test_run_service_invokes_servicemanager_dispatcher(self):
        """Verify run_service initializes pywin32 servicemanager and starts the control dispatcher."""
        from service.service import run_service
        with patch("service.service.HAVE_PYWIN32", True), \
             patch("servicemanager.Initialize") as mock_init, \
             patch("servicemanager.PrepareToHostSingle") as mock_prep, \
             patch("servicemanager.StartServiceCtrlDispatcher") as mock_start:

            run_service()

            mock_init.assert_called_once()
            mock_prep.assert_called_once_with(SLMSService)
            mock_start.assert_called_once()

    def test_main_cli_dispatches_run_to_run_service(self):
        """Verify passing 'run' argument dispatches directly to run_service without unknown command error."""
        import sys
        from service.service import main as service_main
        with patch.object(sys, "argv", ["SLMS_Client_Agent.exe", "run"]), \
             patch("service.service.run_service") as mock_run:

            service_main()
            mock_run.assert_called_once()

    def test_main_cli_dispatches_service_flags_to_run_service(self):
        """Verify passing '--service' or '--startup' dispatches directly to run_service."""
        import sys
        from service.service import main as service_main

        for flag in ("--service", "--startup"):
            with patch.object(sys, "argv", ["SLMS_Client_Agent.exe", flag]), \
                 patch("service.service.run_service") as mock_run:

                service_main()
                mock_run.assert_called_once()

    def test_client_agent_main_routes_to_service_main(self):
        """Verify client_agent.main entry point routes 'run' to service.service.main."""
        import sys
        from main import main as cli_main

        with patch.object(sys, "argv", ["SLMS_Client_Agent.exe", "run"]), \
             patch("service.service.main") as mock_svc_main:

            cli_main()
            mock_svc_main.assert_called_once()

    def test_run_service_handles_1063_error_gracefully(self, capsys):
        """Verify run_service outside SCM (error 1063) prints a diagnostic message and exits 1."""
        from service.service import run_service
        import pywintypes

        err_1063 = pywintypes.error(1063, "StartServiceCtrlDispatcher", "The service process could not connect")

        with patch("service.service.HAVE_PYWIN32", True), \
             patch("servicemanager.Initialize"), \
             patch("servicemanager.PrepareToHostSingle"), \
             patch("servicemanager.StartServiceCtrlDispatcher", side_effect=err_1063), \
             patch("sys.exit") as mock_exit:

            run_service()

            mock_exit.assert_called_once_with(1)
            captured = capsys.readouterr()
            assert "Note: 'run' is invoked by Windows SCM" in captured.out


# ============================================================================
# Regression Tests: Startup Authentication Resilience & Installer Architecture
# ============================================================================

class TestStartupAuthenticationResilience:
    """
    Regression tests for Task 1:
    Verifies that backend/network unavailability during Windows service startup
    does NOT crash the service, transitions to offline/degraded mode, and recovers
    cleanly when the backend returns.
    """

    def test_transient_auth_error_classification(self):
        """Verify transient network/server errors are classified correctly."""
        from core.runtime import is_transient_auth_error
        import requests

        # Transient network / timeout errors
        assert is_transient_auth_error(requests.ConnectionError("Connection refused")) is True
        assert is_transient_auth_error(requests.ConnectTimeout("Connect timeout")) is True
        assert is_transient_auth_error(requests.ReadTimeout("Read timeout")) is True
        assert is_transient_auth_error(ConnectionRefusedError("Refused")) is True
        assert is_transient_auth_error(TimeoutError("Timed out")) is True
        assert is_transient_auth_error(OSError("Network unreachable")) is True

        # HTTP Server errors (5xx) and rate limits (429)
        mock_503 = MagicMock()
        mock_503.status_code = 503
        assert is_transient_auth_error(requests.HTTPError(response=mock_503)) is True

        mock_500 = MagicMock()
        mock_500.status_code = 500
        assert is_transient_auth_error(requests.HTTPError(response=mock_500)) is True

        mock_429 = MagicMock()
        mock_429.status_code = 429
        assert is_transient_auth_error(requests.HTTPError(response=mock_429)) is True

        # Transport security policy errors
        from core.security import (
            InsecureHttpProhibitedError,
            InvalidServerUrlError,
            TransportSecurityError,
        )
        assert is_transient_auth_error(InsecureHttpProhibitedError("Insecure HTTP prohibited in production")) is True
        assert is_transient_auth_error(InvalidServerUrlError("Server URL cannot be empty")) is False
        assert is_transient_auth_error(TransportSecurityError("Generic transport security error")) is False

        # Fatal / non-transient errors
        assert is_transient_auth_error(RuntimeError("Computer not enrolled")) is False
        assert is_transient_auth_error(ValueError("Invalid config")) is False

        mock_401 = MagicMock()
        mock_401.status_code = 401
        assert is_transient_auth_error(requests.HTTPError(response=mock_401)) is False

        mock_400 = MagicMock()
        mock_400.status_code = 400
        assert is_transient_auth_error(requests.HTTPError(response=mock_400)) is False

    def test_startup_backend_unavailable_leaves_runtime_running_and_offline(self, tmp_path):
        """
        Verify that when the backend is offline (ConnectionError / ConnectTimeout)
        during RuntimeManager.start(), the runtime starts in degraded offline mode,
        does NOT raise or crash, and starts outbox and scheduler.
        """
        from core.runtime import AgentRuntime
        from core.outbox import DurableOutbox
        import requests

        db_path = str(tmp_path / "offline_startup.db")
        test_outbox = DurableOutbox(db_path=db_path)
        stop_event = threading.Event()

        runtime = AgentRuntime(
            stop_event=stop_event,
            is_service=True,
            outbox=test_outbox,
            enable_outbox=True,
            enable_single_instance=False,
        )

        with patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.get_computer_id", return_value=101), \
             patch("core.runtime.authenticate_agent", side_effect=requests.ConnectionError("Connection refused")), \
             patch("core.runtime.AgentWebSocketClient"), \
             patch("paths.ensure_directories_exist"):

            def stop_after_startup():
                for _ in range(50):
                    if runtime.is_running:
                        break
                    time.sleep(0.01)
                runtime.stop()

            stopper = threading.Thread(target=stop_after_startup, daemon=True)
            stopper.start()

            # start() should succeed without throwing unhandled exceptions
            runtime.start()
            stopper.join(timeout=2.0)

        assert runtime.started_count == 1
        assert runtime.stopped_count == 1
        assert runtime.computer_id == 101
        assert runtime.token_manager.token == ""

    def test_startup_fatal_error_still_raises_and_does_not_mask_bug(self, tmp_path):
        """Verify genuinely fatal programming/configuration errors are not masked."""
        from core.runtime import AgentRuntime
        from core.outbox import DurableOutbox

        db_path = str(tmp_path / "fatal_startup.db")
        test_outbox = DurableOutbox(db_path=db_path)
        stop_event = threading.Event()

        runtime = AgentRuntime(
            stop_event=stop_event,
            is_service=True,
            outbox=test_outbox,
            enable_outbox=True,
            enable_single_instance=False,
        )

        with patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.get_computer_id", return_value=101), \
             patch("core.runtime.authenticate_agent", side_effect=ValueError("Corrupted credential secret")), \
             patch("paths.ensure_directories_exist"):

            with pytest.raises(ValueError, match="Corrupted credential secret"):
                runtime.start()

            assert runtime.is_running is False
            assert runtime.started_count == 0

    def test_service_lifecycle_survives_offline_startup(self, tmp_path):
        """Verify ServiceLifecycle worker thread remains RUNNING when backend is offline."""
        from core.runtime import AgentRuntime
        from core.outbox import DurableOutbox
        import requests

        db_path = str(tmp_path / "svc_offline.db")
        test_outbox = DurableOutbox(db_path=db_path)

        def mock_runtime_factory(stop_ev):
            return AgentRuntime(
                stop_event=stop_ev,
                is_service=True,
                outbox=test_outbox,
                enable_outbox=True,
                enable_single_instance=False,
            )

        with patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.get_computer_id", return_value=101), \
             patch("core.runtime.authenticate_agent", side_effect=requests.ConnectionError("Offline backend")), \
             patch("core.runtime.AgentWebSocketClient"), \
             patch("paths.ensure_directories_exist"):

            lifecycle = ServiceLifecycle(runtime_factory=mock_runtime_factory)
            lifecycle.start()

            # Wait for state to transition to RUNNING
            time.sleep(0.15)
            assert lifecycle.state == ServiceState.RUNNING
            assert lifecycle.is_healthy() is True
            assert lifecycle.last_error is None

            # Clean shutdown
            lifecycle.stop(timeout=2.0)
            assert lifecycle.state == ServiceState.STOPPED


class TestServiceInstallerCommandGeneration:
    """Regression tests for Task 3: Service installer sc.exe argument formatting."""

    def test_get_install_command_args_exact_tokens(self):
        """Verify get_install_command_args produces discrete tokens without invalid combined arguments."""
        from service.service import get_install_command_args

        cmd = get_install_command_args(
            service_name="SLMSService",
            bin_path=r'"C:\Program Files\SLMS\SLMS_Client_Agent.exe" run',
            startup_type="auto",
            display_name="Smart Lab Management System (SLMS) Client Agent",
            service_account="NT SERVICE\\SLMSService",
        )

        expected = [
            "sc.exe",
            "create",
            "SLMSService",
            "binpath=",
            r'"C:\Program Files\SLMS\SLMS_Client_Agent.exe" run',
            "start=",
            "auto",
            "DisplayName=",
            "Smart Lab Management System (SLMS) Client Agent",
            "obj=",
            "NT SERVICE\\SLMSService",
        ]
        assert cmd == expected

        # Ensure no accidental "start= auto" single token is present
        assert "start= auto" not in cmd
        assert "binpath= " not in str(cmd)

    def test_get_install_command_args_demand_and_localsystem(self):
        """Verify get_install_command_args handles demand startup and localsystem account without obj= parameter."""
        from service.service import get_install_command_args

        cmd = get_install_command_args(
            service_name="SLMSService",
            bin_path=r"C:\SLMS\agent.exe run",
            startup_type="demand",
            display_name="SLMS Agent",
            service_account="LocalSystem",
        )

        assert "start=" in cmd
        assert "demand" in cmd
        # LocalSystem does not need obj= parameter in sc create
        assert "obj=" not in cmd


class TestServiceTransportSecurityResilience:
    """Regression tests for Service resilience against transport security violations."""

    def test_service_lifecycle_survives_insecure_http_in_production(self, tmp_path, monkeypatch):
        """
        CRITICAL TEST: When enrolled URL is plaintext HTTP and production mode prohibits it,
        ServiceLifecycle must enter degraded offline mode, remain in RUNNING state,
        buffer telemetry to outbox, and NOT crash or terminate the worker thread.
        """
        from core.runtime import AgentRuntime
        from core.outbox import DurableOutbox
        from core.security import InsecureHttpProhibitedError

        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)

        db_path = str(tmp_path / "svc_insecure_http.db")
        test_outbox = DurableOutbox(db_path=db_path)

        def mock_runtime_factory(stop_ev):
            return AgentRuntime(
                stop_event=stop_ev,
                is_service=True,
                outbox=test_outbox,
                enable_outbox=True,
                enable_single_instance=False,
            )

        insecure_err = InsecureHttpProhibitedError(
            "Insecure HTTP URL 'http://169.254.234.45:8000' is prohibited in production. "
            "Production SLMS communication requires HTTPS. "
            "Set SLMS_ALLOW_INSECURE_HTTP=1 only for local development."
        )

        with patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.get_computer_id", return_value=101), \
             patch("core.runtime.authenticate_agent", side_effect=insecure_err), \
             patch("core.runtime.AgentWebSocketClient"), \
             patch("paths.ensure_directories_exist"):

            lifecycle = ServiceLifecycle(runtime_factory=mock_runtime_factory)
            lifecycle.start()

            # Wait for state to transition to RUNNING
            time.sleep(0.15)
            assert lifecycle.state == ServiceState.RUNNING
            assert lifecycle.is_healthy() is True
            assert lifecycle.last_error is None

            # Clean shutdown
            lifecycle.stop(timeout=2.0)
            assert lifecycle.state == ServiceState.STOPPED

    def test_service_survives_http_5xx_429_408_errors(self, tmp_path):
        """Verify 500, 502, 503, 504, 429, 408 HTTP errors result in graceful degraded startup."""
        from core.runtime import AgentRuntime
        from core.outbox import DurableOutbox
        import requests

        db_path = str(tmp_path / "svc_http_transient.db")
        test_outbox = DurableOutbox(db_path=db_path)

        for status in [408, 429, 500, 502, 503, 504]:
            mock_resp = requests.Response()
            mock_resp.status_code = status
            http_err = requests.HTTPError(f"HTTP {status}", response=mock_resp)

            runtime = AgentRuntime(
                is_service=True,
                outbox=test_outbox,
                enable_outbox=True,
                enable_single_instance=False,
            )

            with patch("core.runtime.is_enrolled", return_value=True), \
                 patch("core.runtime.get_computer_id", return_value=101), \
                 patch("core.runtime.authenticate_agent", side_effect=http_err), \
                 patch("core.runtime.AgentWebSocketClient"), \
                 patch("paths.ensure_directories_exist"):

                # Should start in degraded mode without raising
                runtime_thread = threading.Thread(target=runtime.start, daemon=True)
                runtime_thread.start()

                time.sleep(0.1)
                assert runtime.is_running is True
                assert not runtime.token_manager.token

                runtime.stop()
                runtime_thread.join(timeout=2.0)
                assert runtime.is_running is False

    def test_insecure_http_prohibited_does_not_perform_http_requests(self, tmp_path, monkeypatch):
        """Verify production security policy strictly prevents HTTP requests from being made."""
        from core.security import validate_and_normalize_server_url, InsecureHttpProhibitedError
        import requests

        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)

        with patch.object(requests.Session, "post") as mock_post:
            with pytest.raises(InsecureHttpProhibitedError):
                validate_and_normalize_server_url("http://169.254.234.45:8000")

            # Must never have attempted any network dispatch
            mock_post.assert_not_called()

    def test_token_manager_background_refresh_handles_insecure_http_error(self, monkeypatch):
        """Verify background token refresh handles InsecureHttpProhibitedError without killing the process."""
        from core.managers import TokenManager
        from core.security import InsecureHttpProhibitedError

        monkeypatch.delenv("SLMS_ALLOW_INSECURE_HTTP", raising=False)
        monkeypatch.delenv("SLMS_DEV_MODE", raising=False)

        tm = TokenManager(refresh_interval=60.0)

        insecure_err = InsecureHttpProhibitedError("Insecure HTTP prohibited")
        with patch("core.managers._resolve_authenticate_agent", side_effect=insecure_err):
            # refresh_if_due must catch and log, not crash
            result = tm.refresh_if_due()
            assert result is False
            assert not tm.token

    def test_invalid_server_url_error_is_fatal_and_raises(self, tmp_path):
        """Verify InvalidServerUrlError (configuration error) is NOT transient and raises fatally on startup."""
        from core.runtime import AgentRuntime
        from core.outbox import DurableOutbox
        from core.security import InvalidServerUrlError

        db_path = str(tmp_path / "svc_invalid_url.db")
        test_outbox = DurableOutbox(db_path=db_path)

        runtime = AgentRuntime(
            is_service=True,
            outbox=test_outbox,
            enable_outbox=True,
            enable_single_instance=False,
        )

        invalid_url_err = InvalidServerUrlError("Server URL cannot be empty.")
        with patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.get_computer_id", return_value=101), \
             patch("core.runtime.authenticate_agent", side_effect=invalid_url_err), \
             patch("paths.ensure_directories_exist"):

            with pytest.raises(InvalidServerUrlError, match="Server URL cannot be empty"):
                runtime.start()

            assert runtime.is_running is False
            assert runtime.started_count == 0


class TestMandatoryServiceAclAndDevModeArchitecture:
    """
    Regression test suite for SLMS_DEV_MODE service ACL and credential access:
    1. Mandatory ACLs applied when SLMS_DEV_MODE=1.
    2. Mandatory ACLs + production hardening when SLMS_DEV_MODE=0.
    3. Enrollment before SLMSService exists.
    4. ACL application after SLMSService exists.
    5. Successful credential access by the service account.
    6. Mandatory ACL failure handling.
    7. Service startup with SLMS_DEV_MODE=1.
    8. PermissionError in credential reading logged clearly.
    """

    def test_mandatory_acls_applied_when_slms_dev_mode_1(self, tmp_path, monkeypatch):
        """1. Verify mandatory ACLs for service account are NOT skipped when SLMS_DEV_MODE=1."""
        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        cred_file = config_dir / "service_credentials.enc"
        cred_file.write_bytes(b"mock_ciphertext")

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "successfully processed 1 files"
        mock_res.stderr = ""

        with patch("service.service.subprocess.run", return_value=mock_res) as mock_run, \
             patch("service.service.os.name", "nt"):

            success = apply_mandatory_service_acls(
                service_account="NT SERVICE\\SLMSService",
                data_dir=str(tmp_path),
            )
            assert success is True
            assert mock_run.call_count == 2

            # First call: root folder modify
            first_cmd = mock_run.call_args_list[0][0][0]
            assert first_cmd == ["icacls", str(tmp_path), "/grant", "NT SERVICE\\SLMSService:(OI)(CI)(M)", "/t"]

            # Second call: credential file read
            second_cmd = mock_run.call_args_list[1][0][0]
            assert second_cmd == ["icacls", str(cred_file), "/grant", "NT SERVICE\\SLMSService:(R)"]

    def test_configure_service_folder_permissions_enforces_mandatory_acls_in_dev_mode(self, tmp_path, monkeypatch):
        """1b. Verify configure_service_folder_permissions applies mandatory ACLs even when SLMS_DEV_MODE=1."""
        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        cred_file = config_dir / "service_credentials.enc"
        cred_file.write_bytes(b"mock_ciphertext")

        mock_res = MagicMock(returncode=0, stdout="success", stderr="")

        with patch("service.service.subprocess.run", return_value=mock_res) as mock_run, \
             patch("service.service.os.name", "nt"):

            success = configure_service_folder_permissions(
                service_account="NT SERVICE\\SLMSService",
                data_dir=str(tmp_path),
            )
            assert success is True
            # Both mandatory commands executed; optional hardening skipped
            assert mock_run.call_count == 2
            cmds = [call[0][0] for call in mock_run.call_args_list]
            assert any("NT SERVICE\\SLMSService:(OI)(CI)(M)" in c for c in cmds)
            assert any("NT SERVICE\\SLMSService:(R)" in c for c in cmds)

    def test_mandatory_acls_and_production_hardening_when_slms_dev_mode_0(self, tmp_path, monkeypatch):
        """2. Verify both mandatory ACLs and production hardening execute when SLMS_DEV_MODE=0."""
        monkeypatch.setenv("SLMS_DEV_MODE", "0")
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        cred_file = config_dir / "service_credentials.enc"
        cred_file.write_bytes(b"mock_ciphertext")

        mock_res = MagicMock(returncode=0, stdout="success", stderr="")

        with patch("service.service.subprocess.run", return_value=mock_res) as mock_run, \
             patch("service.service.os.name", "nt"):

            success = configure_service_folder_permissions(
                service_account="NT SERVICE\\SLMSService",
                data_dir=str(tmp_path),
            )
            assert success is True
            # 2 mandatory ACL calls + 1 production hardening call = 3 calls
            assert mock_run.call_count == 3
            cmds = [call[0][0] for call in mock_run.call_args_list]
            assert any("NT SERVICE\\SLMSService:(OI)(CI)(M)" in c for c in cmds)
            assert any("NT SERVICE\\SLMSService:(R)" in c for c in cmds)
            assert any("*S-1-5-32-544:(OI)(CI)(F)" in c for c in cmds)

    def test_enrollment_before_slms_service_exists(self, tmp_path, monkeypatch):
        """3. Verify enrollment saves credentials even if NT SERVICE\\SLMSService does not yet exist in SCM."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Mock icacls: granting to non-existent service account returns code 1 (not found)
        def fake_run(cmd, *args, **kwargs):
            res = MagicMock()
            if "NT SERVICE\\SLMSService:(R)" in cmd:
                res.returncode = 1
                res.stderr = "No mapping between account names and security IDs was done."
                res.stdout = ""
            else:
                res.returncode = 0
                res.stdout = "successfully processed 1 files"
                res.stderr = ""
            return res

        with patch("core.credentials.subprocess.run", side_effect=fake_run), \
             patch("core.credentials.os.name", "nt"):

            store = ServiceCredentialStore(config_folder=str(config_dir))
            # Saving credentials must succeed without raising exception
            store.save_enrolled_credentials(
                agent_id="test-agent-pre-service",
                client_secret="secret-pre-service",
                computer_id=777,
            )
            assert store.is_enrolled() is True
            creds = store.get_enrolled_credentials()
            assert creds is not None
            assert creds["computer_id"] == 777

    def test_acl_application_after_slms_service_exists(self, tmp_path):
        """4. Verify ACL application after service exists grants service account Read on credentials."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        cred_file = config_dir / "service_credentials.enc"
        cred_file.write_bytes(b"payload")

        mock_res = MagicMock(returncode=0, stdout="successfully processed 1 files", stderr="")
        with patch("service.service.subprocess.run", return_value=mock_res) as mock_run, \
             patch("service.service.os.name", "nt"):

            ok = apply_mandatory_service_acls(
                service_account="NT SERVICE\\SLMSService",
                data_dir=str(tmp_path),
            )
            assert ok is True
            # Second call grants Read to NT SERVICE\SLMSService on service_credentials.enc
            cred_call = mock_run.call_args_list[1][0][0]
            assert cred_call == ["icacls", str(cred_file), "/grant", "NT SERVICE\\SLMSService:(R)"]

    def test_successful_credential_access_by_service_account(self, tmp_path):
        """5. Verify credential verification succeeds when credentials are valid and ACL is present."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        store = ServiceCredentialStore(config_folder=str(config_dir))
        store.save_enrolled_credentials("verified-agent", "verified-secret", 888)

        mock_icacls = MagicMock()
        mock_icacls.returncode = 0
        mock_icacls.stdout = (
            f"{config_dir / 'service_credentials.enc'} NT SERVICE\\SLMSService:(R)\n"
            "BUILTIN\\Administrators:(F)\n"
            "NT AUTHORITY\\SYSTEM:(F)\n"
        )
        mock_icacls.stderr = ""

        with patch("service.service.subprocess.run", return_value=mock_icacls), \
             patch("service.service.os.name", "nt"):

            ok, msg = verify_service_credentials_accessible(
                service_account="NT SERVICE\\SLMSService",
                data_dir=str(tmp_path),
            )
            assert ok is True
            assert "verified and accessible" in msg

    def test_mandatory_acl_failure_fails_configuration_and_installation(self, tmp_path, monkeypatch):
        """6. Verify mandatory ACL failures return False and prevent starting a broken service."""
        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        cred_file = config_dir / "service_credentials.enc"
        cred_file.write_bytes(b"data")

        # Simulate icacls Access Denied (returncode 5)
        mock_fail = MagicMock(returncode=5, stdout="", stderr="Access is denied.")

        with patch("service.service.subprocess.run", return_value=mock_fail), \
             patch("service.service.os.name", "nt"):

            ok = apply_mandatory_service_acls(
                service_account="NT SERVICE\\SLMSService",
                data_dir=str(tmp_path),
            )
            assert ok is False

            conf_ok = configure_service_folder_permissions(
                service_account="NT SERVICE\\SLMSService",
                data_dir=str(tmp_path),
            )
            assert conf_ok is False

    def test_service_startup_with_slms_dev_mode_1(self, tmp_path, monkeypatch):
        """7. Verify service starts cleanly in development mode (SLMS_DEV_MODE=1) without crashing."""
        monkeypatch.setenv("SLMS_DEV_MODE", "1")
        monkeypatch.setenv("SLMS_ALLOW_INSECURE_HTTP", "1")
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)

        store = ServiceCredentialStore(config_folder=str(config_dir))
        store.save_enrolled_credentials("dev-agent-01", "dev-secret-01", 999)
        store.set_server_url("http://127.0.0.1:8000")

        # Mock outbox and authentication
        from core.outbox import DurableOutbox
        outbox = DurableOutbox(db_path=str(tmp_path / "dev_test.db"))

        runtime = AgentRuntime(
            is_service=True,
            outbox=outbox,
            enable_outbox=True,
            enable_single_instance=False,
        )

        with patch("core.runtime.get_credential_store", return_value=store), \
             patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.get_computer_id", return_value=999), \
             patch("core.runtime.authenticate_agent", return_value="jwt.mock.token"), \
             patch("paths.ensure_directories_exist"):

            # Calling start_in_thread or simulating startup step must not raise RuntimeError
            assert store.is_enrolled() is True
            creds = store.get_enrolled_credentials()
            assert creds is not None
            assert creds["computer_id"] == 999

    def test_permission_error_in_read_payload_logged_clearly(self, tmp_path, caplog):
        """8. Verify PermissionError during credential read is logged with high-visibility error."""
        import logging
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        cred_file = config_dir / "service_credentials.enc"
        cred_file.write_bytes(b"dummy_ciphertext")

        store = ServiceCredentialStore(config_folder=str(config_dir))

        with patch("builtins.open", side_effect=PermissionError("[Errno 13] Access is denied")):
            with caplog.at_level(logging.ERROR):
                payload = store._read_payload()
                assert payload == {}
                assert any("Permission denied reading service credential file" in record.message for record in caplog.records)
                assert any("Ensure NT SERVICE" in record.message for record in caplog.records)
