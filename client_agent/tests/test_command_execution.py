"""
Unit tests for SLMS Client Agent Command Execution Subsystem (J-08).
Verifies:
- handle_lock success and OS failure
- handle_restart success and failure
- handle_shutdown success and failure
- execute_command whitelist dispatch
- execute_command rejection of unknown/disallowed commands
- handle_message cross-session delivery mechanisms and strict failure semantics

SAFETY CRITICAL:
Every shutdown/restart/LockWorkStation OS call MUST be mocked so that
running this test suite never locks, reboots, or halts the machine.
"""

import ctypes
import os
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from server.command_handler import (
    COMMAND_WHITELIST,
    execute_command,
    handle_lock,
    handle_message,
    handle_restart,
    handle_shutdown,
)


from core.ipc import NotificationStatus


def test_handle_lock_companion_confirmed():
    """Verify handle_lock returns True when companion reports LOCK_CONFIRMED."""
    mock_server = MagicMock()
    mock_server.get_connected_sessions.return_value = [5]
    mock_server.send_lock.return_value = (
        True,
        NotificationStatus.LOCK_CONFIRMED,
        "Workstation lock confirmed in session 5",
    )

    with patch("server.command_handler.get_notification_server", return_value=mock_server):
        success, message = handle_lock(None, command_id="cmd-lock-1")

    assert success is True
    assert "confirmed" in message.lower()
    mock_server.send_lock.assert_called_once_with(
        session_id=5,
        command_id="cmd-lock-1",
        timeout_sec=5.0,
    )


def test_handle_lock_companion_request_accepted_is_not_success():
    """
    CRITICAL: Verify handle_lock returns False (not True) when Windows accepted the
    API call but locked state was not independently confirmed (REQUEST_ACCEPTED).
    This ensures REQUEST_ACCEPTED is never silently treated as success.
    """
    mock_server = MagicMock()
    mock_server.get_connected_sessions.return_value = [5]
    mock_server.send_lock.return_value = (
        False,
        NotificationStatus.REQUEST_ACCEPTED,
        "Workstation lock request accepted by Windows, but lock state not confirmed in session 5",
    )

    with patch("server.command_handler.get_notification_server", return_value=mock_server):
        success, message = handle_lock(None, command_id="cmd-lock-2")

    assert success is False
    assert "not confirmed" in message.lower() or "REQUEST_ACCEPTED" in message


def test_handle_lock_no_companion_connected():
    """Verify handle_lock returns False with NOT_CONNECTED when no companion is connected."""
    mock_server = MagicMock()
    mock_server.get_connected_sessions.return_value = []

    with patch("server.command_handler.get_notification_server", return_value=mock_server):
        success, message = handle_lock(None, command_id="cmd-lock-3")

    assert success is False
    assert "NOT_CONNECTED" in message


def test_handle_lock_wrong_session_requested():
    """Verify handle_lock returns False when caller requests a session without an active companion."""
    mock_server = MagicMock()
    mock_server.get_connected_sessions.return_value = [2]

    with patch("server.command_handler.get_notification_server", return_value=mock_server):
        success, message = handle_lock({"session_id": 99}, command_id="cmd-lock-4")

    assert success is False
    assert "NOT_CONNECTED" in message
    assert "99" in message


def test_handle_lock_companion_timeout():
    """Verify handle_lock handles companion acknowledgment timeout cleanly."""
    mock_server = MagicMock()
    mock_server.get_connected_sessions.return_value = [5]
    mock_server.send_lock.return_value = (
        False,
        NotificationStatus.TIMEOUT,
        "Timed out waiting for lock ACK in session 5",
    )

    with patch("server.command_handler.get_notification_server", return_value=mock_server):
        success, message = handle_lock(None, command_id="cmd-lock-5")

    assert success is False
    assert "timed out" in message.lower()


def test_handle_lock_companion_api_failed():
    """Verify handle_lock returns False when companion reports user32 API failure."""
    mock_server = MagicMock()
    mock_server.get_connected_sessions.return_value = [5]
    mock_server.send_lock.return_value = (
        False,
        NotificationStatus.FAILED,
        "Workstation lock failed in session 5: user32.LockWorkStation returned 0: Win32 error 5",
    )

    with patch("server.command_handler.get_notification_server", return_value=mock_server):
        success, message = handle_lock(None, command_id="cmd-lock-6")

    assert success is False
    assert "failed" in message.lower()


@pytest.mark.windows_only
@pytest.mark.skipif(os.name != "nt", reason="Direct user32.LockWorkStation execution requires Windows")
def test_handle_lock_direct_interactive_confirmed():
    """Verify direct non-service execution returns True only when lock state is confirmed."""
    mock_user32 = MagicMock()
    mock_user32.LockWorkStation.return_value = 1

    mock_kernel32 = MagicMock()
    mock_kernel32.GetCurrentProcessId.return_value = 1000

    def fake_pid_to_sid(pid, byref_sid):
        byref_sid._obj.value = 1  # Interactive session 1
        return 1

    mock_kernel32.ProcessIdToSessionId.side_effect = fake_pid_to_sid

    class _FakeWindll:
        user32 = mock_user32
        kernel32 = mock_kernel32

    with patch("server.command_handler.get_notification_server", return_value=None), \
         patch("ctypes.windll", _FakeWindll(), create=True), \
         patch("server.command_handler.query_session_lock_state", return_value=0):
        success, message = handle_lock(None)

    assert success is True
    assert "confirmed" in message.lower()


@pytest.mark.windows_only
@pytest.mark.skipif(os.name != "nt", reason="Direct user32.LockWorkStation execution requires Windows")
def test_handle_lock_direct_interactive_unconfirmed_never_returns_true():
    """Verify direct non-service execution returns False when lock state cannot be confirmed."""
    mock_user32 = MagicMock()
    mock_user32.LockWorkStation.return_value = 1

    mock_kernel32 = MagicMock()
    mock_kernel32.GetCurrentProcessId.return_value = 1000

    def fake_pid_to_sid(pid, byref_sid):
        byref_sid._obj.value = 1  # Interactive session 1
        return 1

    mock_kernel32.ProcessIdToSessionId.side_effect = fake_pid_to_sid

    class _FakeWindll:
        user32 = mock_user32
        kernel32 = mock_kernel32

    with patch("server.command_handler.get_notification_server", return_value=None), \
         patch("ctypes.windll", _FakeWindll(), create=True), \
         patch("server.command_handler.query_session_lock_state", return_value=1):  # Still unlocked
        success, message = handle_lock(None)

    assert success is False
    assert "REQUEST_ACCEPTED" in message or "not confirmed" in message.lower()


@pytest.mark.windows_only
@pytest.mark.skipif(os.name != "nt", reason="Direct user32.LockWorkStation execution requires Windows")
def test_handle_lock_direct_interactive_os_failure():
    """Verify direct non-service execution returns False on LockWorkStation failure."""
    mock_user32 = MagicMock()
    mock_user32.LockWorkStation.return_value = 0  # Win32 failure

    mock_kernel32 = MagicMock()
    mock_kernel32.GetCurrentProcessId.return_value = 1000

    def fake_pid_to_sid(pid, byref_sid):
        byref_sid._obj.value = 1
        return 1

    mock_kernel32.ProcessIdToSessionId.side_effect = fake_pid_to_sid

    class _FakeWindll:
        user32 = mock_user32
        kernel32 = mock_kernel32

    with patch("server.command_handler.get_notification_server", return_value=None), \
         patch("ctypes.windll", _FakeWindll(), create=True), \
         patch("ctypes.GetLastError", return_value=5, create=True):
        success, message = handle_lock(None)

    assert success is False
    assert "failed" in message.lower()



def test_handle_restart_success():
    """Verify handle_restart invokes shutdown /r /t 5 with check=True."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        success, message = handle_restart(None)

        assert success is True
        assert message == "Restart scheduled in 5 seconds"
        mock_run.assert_called_once_with(["shutdown", "/r", "/t", "5"], check=True)


def test_handle_restart_failure():
    """Verify handle_restart catches CalledProcessError or OSError."""
    with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, ["shutdown"])):
        success, message = handle_restart(None)

        assert success is False
        assert "Command '['shutdown']' returned non-zero exit status 1" in message or "1" in message


def test_handle_shutdown_success():
    """Verify handle_shutdown invokes shutdown /s /t 5 with check=True."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        success, message = handle_shutdown(None)

        assert success is True
        assert message == "Shutdown scheduled in 5 seconds"
        mock_run.assert_called_once_with(["shutdown", "/s", "/t", "5"], check=True)


def test_handle_shutdown_failure():
    """Verify handle_shutdown catches OSError safely."""
    with patch("subprocess.run", side_effect=OSError("Privilege not held")):
        success, message = handle_shutdown(None)

        assert success is False
        assert "Privilege not held" in message


def test_execute_command_dispatch_known_commands():
    """Verify execute_command dispatches to handlers registered in COMMAND_WHITELIST."""
    for cmd_type in COMMAND_WHITELIST:
        with patch.dict(COMMAND_WHITELIST, {cmd_type: MagicMock(return_value=(True, f"Mocked {cmd_type}"))}):
            success, msg = execute_command(cmd_type, payload={"test": 1})
            assert success is True
            assert msg == f"Mocked {cmd_type}"
            COMMAND_WHITELIST[cmd_type].assert_called_once_with({"test": 1})


def test_execute_command_lock_passes_command_id():
    """Verify execute_command passes command_id down to handle_lock."""
    with patch.dict(COMMAND_WHITELIST, {"lock": MagicMock(return_value=(True, "Lock executed"))}):
        success, msg = execute_command("lock", payload={"session_id": 1}, command_id="cmd-999")
        assert success is True
        assert msg == "Lock executed"
        COMMAND_WHITELIST["lock"].assert_called_once_with({"session_id": 1}, command_id="cmd-999")


def test_execute_command_rejects_unknown_command():
    """Verify execute_command rejects unknown, unwhitelisted commands."""
    unknown_types = [
        "format_drive",
        "rmdir",
        "download_exec",
        "powershell",
        "",
        "DROP_TABLE",
    ]
    for unknown in unknown_types:
        success, message = execute_command(unknown)
        assert success is False
        assert "Unknown or disallowed command" in message


def test_execute_command_catches_unhandled_exception():
    """Verify execute_command catches unexpected exceptions in handler without crashing."""
    with patch.dict(COMMAND_WHITELIST, {"message": MagicMock(side_effect=RuntimeError("Unexpected crash"))}):
        success, message = execute_command("message", "test")
        assert success is False
        assert "Execution exception: Unexpected crash" in message


def test_execute_command_bounds_long_message():
    """Verify execute_command truncates result message to at most 255 characters."""
    very_long_msg = "X" * 500
    with patch.dict(COMMAND_WHITELIST, {"message": MagicMock(return_value=(True, very_long_msg))}):
        success, message = execute_command("message", "test")
        assert success is True
        assert len(message) <= 255
        assert message.endswith("...")


# ============================================================================
# Phase 5: Comprehensive Message Delivery Subsystem Tests
# ============================================================================

def test_handle_message_wts_success():
    """Verify handle_message returns True when WTSSendMessageW accepts the display request."""
    with patch("server.command_handler._get_active_sessions", return_value=[1]), \
         patch("server.command_handler._send_wts_message", return_value=(True, "Notice display request accepted by Windows Terminal Services for session(s): 1")):
        success, message = handle_message("Important maintenance notice")
        assert success is True
        assert "Notice display request accepted by Windows Terminal Services" in message


def test_handle_message_msg_exe_success():
    """Verify handle_message falls back to msg.exe and succeeds when msg.exe accepts."""
    with patch("server.command_handler._get_active_sessions", return_value=[2]), \
         patch("server.command_handler._send_wts_message", return_value=(False, "WTSSendMessage failed (Win32 error 1722)")), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        success, message = handle_message("Lab closing notice")
        assert success is True
        assert "Notice display request accepted by Windows msg.exe" in message


def test_handle_message_task_scheduler_success():
    """Verify handle_message falls back to Task Scheduler and succeeds."""
    with patch("server.command_handler._get_active_sessions", return_value=[1]), \
         patch("server.command_handler._get_logged_in_users", return_value=["student"]), \
         patch("server.command_handler._send_wts_message", return_value=(False, "WTS failed")), \
         patch("subprocess.run", side_effect=FileNotFoundError("msg.exe not found")), \
         patch("server.command_handler._send_task_message", return_value=(True, "Notice dialog launched via Task Scheduler for user(s): student")):
        success, message = handle_message("Task message")
        assert success is True
        assert "Notice dialog launched via Task Scheduler" in message


def test_handle_message_user_session_success():
    """Verify handle_message falls back to user session execution and succeeds."""
    with patch("server.command_handler._get_active_sessions", return_value=[1]), \
         patch("server.command_handler._get_logged_in_users", return_value=["student"]), \
         patch("server.command_handler._send_wts_message", return_value=(False, "WTS failed")), \
         patch("subprocess.run", side_effect=FileNotFoundError("msg.exe not found")), \
         patch("server.command_handler._send_task_message", return_value=(False, "Task failed")), \
         patch("server.command_handler._send_user_session_message", return_value=(True, "Notice dialog launched in user session via CreateProcessAsUser")):
        success, message = handle_message("Direct user session message")
        assert success is True
        assert "CreateProcessAsUser" in message


def test_handle_message_no_interactive_user_session():
    """Verify handle_message returns False when no interactive user session or logon exists."""
    with patch("server.command_handler._get_active_sessions", return_value=[]), \
         patch("server.command_handler._get_logged_in_users", return_value=[]):
        success, message = handle_message("Alert when nobody logged in")
        assert success is False
        assert message == "No interactive user session available to display notice"


def test_handle_message_every_display_mechanism_fails():
    """
    CRITICAL: Verify that when all display mechanisms fail, handle_message NEVER returns
    success merely because the message was logged. It must return False with diagnostics.
    """
    with patch("server.command_handler._get_active_sessions", return_value=[1]), \
         patch("server.command_handler._get_logged_in_users", return_value=["student"]), \
         patch("server.command_handler._send_wts_message", return_value=(False, "WTSSendMessage failed (Win32 error 5)")), \
         patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="Access is denied", stdout="")), \
         patch("server.command_handler._send_task_message", return_value=(False, "Task Scheduler rejected: Access is denied")), \
         patch("server.command_handler._send_user_session_message", return_value=(False, "CreateProcessAsUser failed")):
        success, message = handle_message("Confidential alert message 12345")
        assert success is False
        assert "Notice could not be displayed on client desktop" in message
        # Ensure raw message content is not leaked in the failure diagnostic
        assert "Confidential alert message" not in message
        assert "12345" not in message


def test_handle_message_windows_api_failure():
    """Verify handle_message gracefully handles WTSSendMessage Win32 API failure."""
    with patch("server.command_handler._get_active_sessions", return_value=[1]), \
         patch("server.command_handler._send_wts_message", return_value=(False, "WTSSendMessage failed (Win32 error 5)")), \
         patch("subprocess.run", side_effect=OSError("OS call failed")), \
         patch("server.command_handler._send_task_message", return_value=(False, "Task Scheduler rejected")), \
         patch("server.command_handler._send_user_session_message", return_value=(False, "User token failed")):
        success, message = handle_message("Test failure")
        assert success is False
        assert "Notice could not be displayed" in message


def test_handle_message_logged_only_fallback_never_returns_true():
    """Verify that logging-only never produces True for message execution."""
    with patch("server.command_handler._get_active_sessions", return_value=[1]), \
         patch("server.command_handler._send_wts_message", return_value=(False, "WTS failed")), \
         patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="Failed", stdout="")), \
         patch("server.command_handler._send_task_message", return_value=(False, "Task failed")), \
         patch("server.command_handler._send_user_session_message", return_value=(False, "User failed")):
        success, message = handle_message("Log only test")
        assert success is False
        assert not message.startswith("Notice recorded in agent log")
