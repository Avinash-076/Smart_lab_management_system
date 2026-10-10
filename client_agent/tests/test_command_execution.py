"""
Unit tests for SLMS Client Agent Command Execution Subsystem (J-08).
Verifies:
- handle_lock success and OS failure
- handle_restart success and failure
- handle_shutdown success and failure
- execute_command whitelist dispatch
- execute_command rejection of unknown/disallowed commands

SAFETY CRITICAL:
Every shutdown/restart/LockWorkStation OS call MUST be mocked so that
running this test suite never locks, reboots, or halts the machine.
"""

import ctypes
import subprocess
from unittest.mock import MagicMock, patch

from server.command_handler import (
    COMMAND_WHITELIST,
    execute_command,
    handle_lock,
    handle_restart,
    handle_shutdown,
)


def test_handle_lock_success():
    """Verify handle_lock invokes LockWorkStation and returns success."""
    mock_lock = MagicMock(return_value=1)
    mock_user32 = MagicMock(LockWorkStation=mock_lock)
    mock_windll = MagicMock(user32=mock_user32)
    with patch.object(ctypes, "windll", mock_windll, create=True):
        success, message = handle_lock(None)
        assert success is True
        assert message == "Workstation locked"
        mock_lock.assert_called_once()


def test_handle_lock_os_failure():
    """Verify handle_lock handles OS failure gracefully without crashing."""
    mock_lock = MagicMock(side_effect=OSError("LockWorkStation failed with error 5"))
    mock_user32 = MagicMock(LockWorkStation=mock_lock)
    mock_windll = MagicMock(user32=mock_user32)
    with patch.object(ctypes, "windll", mock_windll, create=True):
        success, message = handle_lock(None)
        assert success is False
        assert "LockWorkStation failed" in message


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


def test_handle_message_safe_execution():
    """Verify handle_message safely broadcasts or falls back to log recording."""
    from server.command_handler import handle_message
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        success, message = handle_message("Lab closing notice")
        assert success is True
        assert "Notice broadcast" in message
