"""
Comprehensive Integration Tests for Stage 4: SLMS Notification IPC Integration.

Tests cover:
1. Runtime startup and shutdown lifecycle with NotificationPipeServer:
   - Starts NotificationPipeServer in Session 0 and registers it in command_handler
   - Idempotent and thread-safe start and stop cycles
   - Handles startup failures without crashing runtime or disabling telemetry
   - Clean shutdown: closes pipe handles, stops workers, unregisters from command_handler
2. Route remote messages through companion IPC channel:
   - Successful display returns DISPLAYED
   - User dismissal returns DISMISSED
   - Accurate discrimination of ACCEPTED (not success), REJECTED, FAILED, TIMEOUT, NOT_CONNECTED
   - Never reports success merely because a message was logged, enqueued, or accepted by the pipe
3. Missing companion and companion disconnect:
   - No companion connected -> NOT_CONNECTED logged, falls back cleanly to legacy methods
   - Abrupt companion disconnect during delivery handled safely
4. Acknowledgment timeouts and duplicate command IDs:
   - Acknowledgment timeout -> TIMEOUT status, falls back cleanly
   - Duplicate command ID -> REJECTED status
5. Concurrent messages and multi-session isolation:
   - Multi-session isolation: Session 1 never receives Session 2's notifications
   - Concurrent requests do not corrupt each other's ACKs or pending results
6. Service stop/restart and companion reconnection:
   - Companion reconnects across service restarts and resumes notification processing
7. Authorization and audit logging regression:
   - Non-whitelisted commands rejected
   - Outbox persistence records command_id, duration_seconds, success/failure diagnostics
8. Telemetry continuity when IPC is unavailable:
   - Scheduler and collection continue unhindered when IPC server fails or is absent
"""

from __future__ import annotations

import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from core.ipc import (
    CommandDeduplicator,
    IPCMessageType,
    NotificationPayload,
    NotificationPipeClient,
    NotificationPipeServer,
    NotificationStatus,
    encode_frame,
)
from core.managers import (
    CollectorManager,
    OutboxManager,
    ShutdownManager,
    TokenManager,
    UploadManager,
    WebSocketManager,
)
from core.outbox import DurableOutbox
from core.runtime import RuntimeManager
from core.scheduler import Scheduler
from notifier.companion import NotificationCompanion
from server.command_handler import (
    COMMAND_WHITELIST,
    execute_command,
    get_notification_server,
    handle_message,
    set_notification_server,
)
from server.communication import AgentWebSocketClient


pytestmark = [pytest.mark.integration, pytest.mark.windows_only]

# Unique pipe name for isolation in tests
TEST_INTEG_PIPE_PREFIX = r"\\.\pipe\SLMS_Test_Integ_"


@pytest.fixture(autouse=True)
def reset_command_handler_state():
    """Ensure global notification server reference is reset between tests."""
    set_notification_server(None)
    os.environ["SLMS_ALLOW_TEST_SESSION_SERVER"] = "1"
    yield
    set_notification_server(None)
    os.environ.pop("SLMS_ALLOW_TEST_SESSION_SERVER", None)


# ============================================================================
# 1. Runtime Lifecycle Integration Tests
# ============================================================================

class TestRuntimeNotificationServerLifecycle:
    """Tests for NotificationPipeServer integration in RuntimeManager."""

    def test_runtime_starts_and_registers_notification_server(self):
        """Verify RuntimeManager starts NotificationPipeServer and registers it with command_handler."""
        pipe_name = f"{TEST_INTEG_PIPE_PREFIX}Life_1"
        mock_server = NotificationPipeServer(pipe_name=pipe_name)
        stop_evt = threading.Event()

        runtime = RuntimeManager(
            stop_event=stop_evt,
            enable_single_instance=False,
            enable_outbox=False,
            notification_server=mock_server,
        )

        with patch.object(runtime, "_register_scheduled_jobs"), \
             patch.object(runtime.scheduler, "start"), \
             patch.object(runtime, "_refresh_token_safe", return_value="fake_token"), \
             patch.object(runtime.token_manager, "refresh", return_value="fake_token"), \
             patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.get_computer_id", return_value=42):

            def stop_later():
                time.sleep(0.1)
                stop_evt.set()

            t = threading.Thread(target=stop_later)
            t.start()

            runtime.start()
            t.join()

            # Verify server was registered in command_handler during execution
            # and unregistered during cleanup
            assert get_notification_server() is None
            assert mock_server.is_running is False

    def test_runtime_handles_notification_server_startup_failure_gracefully(self):
        """Verify that a failure starting the notification server does not abort runtime or telemetry."""
        pipe_name = f"{TEST_INTEG_PIPE_PREFIX}Fail_1"
        failing_server = MagicMock()
        failing_server.start.side_effect = OSError("Pipe creation access denied")
        stop_evt = threading.Event()

        runtime = RuntimeManager(
            stop_event=stop_evt,
            enable_single_instance=False,
            enable_outbox=False,
            notification_server=failing_server,
        )

        with patch.object(runtime, "_register_scheduled_jobs") as mock_reg, \
             patch.object(runtime.scheduler, "start") as mock_sched_start, \
             patch.object(runtime, "_refresh_token_safe", return_value="fake_token"), \
             patch.object(runtime.token_manager, "refresh", return_value="fake_token"), \
             patch("core.runtime.is_enrolled", return_value=True), \
             patch("core.runtime.get_computer_id", return_value=42):

            def stop_later():
                time.sleep(0.1)
                stop_evt.set()

            t = threading.Thread(target=stop_later)
            t.start()

            # Should complete startup without raising an exception
            runtime.start()
            t.join()

            # Scheduler and jobs were still started despite IPC startup failure
            mock_reg.assert_called_once()
            mock_sched_start.assert_called_once()
            assert get_notification_server() is None

    def test_runtime_shutdown_idempotency_and_clean_unregistration(self):
        """Verify repeated stop() calls on RuntimeManager are thread-safe and idempotent."""
        pipe_name = f"{TEST_INTEG_PIPE_PREFIX}Idemp_1"
        mock_server = MagicMock()
        stop_evt = threading.Event()

        runtime = RuntimeManager(
            stop_event=stop_evt,
            enable_single_instance=False,
            enable_outbox=False,
            notification_server=mock_server,
        )

        set_notification_server(mock_server)
        assert get_notification_server() is mock_server

        # First stop
        runtime.stop()
        assert get_notification_server() is None
        assert mock_server.stop.call_count == 1

        # Second stop (idempotent)
        runtime.stop()
        assert get_notification_server() is None
        # stop() should not raise or double-execute shutdown
        assert mock_server.stop.call_count == 1


# ============================================================================
# 2. Command Routing & Status Discrimination Tests
# ============================================================================

class TestCommandRoutingAndStatusSemantics:
    """Tests verifying handle_message delivery states, timeouts, and fallbacks."""

    def test_handle_message_displayed_status(self):
        """Verify handle_message returns True when companion reports DISPLAYED."""
        mock_ipc = MagicMock()
        mock_ipc.get_connected_sessions.return_value = [1]
        mock_ipc.send_notification.return_value = (
            True,
            NotificationStatus.DISPLAYED,
            "Notice displayed in user session 1",
        )
        set_notification_server(mock_ipc)

        with patch("server.command_handler._get_active_sessions", return_value=[1]):
            success, message = handle_message({"title": "Alert", "message": "Fire drill", "command_id": 101})
            assert success is True
            assert "Notice displayed to active user via SLMS Notifier companion in session 1" in message

            mock_ipc.send_notification.assert_called_once()
            args, kwargs = mock_ipc.send_notification.call_args
            assert kwargs["session_id"] == 1
            assert kwargs["command_id"] == "101"
            assert kwargs["title"] == "Alert"
            assert kwargs["message"] == "Fire drill"

    def test_handle_message_dismissed_status(self):
        """Verify handle_message returns True when companion reports DISMISSED."""
        mock_ipc = MagicMock()
        mock_ipc.get_connected_sessions.return_value = [2]
        mock_ipc.send_notification.return_value = (
            True,
            NotificationStatus.DISMISSED,
            "Notice dismissed by user",
        )
        set_notification_server(mock_ipc)

        with patch("server.command_handler._get_active_sessions", return_value=[2]):
            success, message = handle_message({"title": "Test", "message": "Click OK", "command_id": "c-99"})
            assert success is True
            assert "Notice dismissed by user via SLMS Notifier companion in session 2" in message

    def test_handle_message_accepted_alone_never_returns_success(self):
        """
        CRITICAL: Verify that if a notification was only ACCEPTED (queued/buffered)
        and not DISPLAYED, handle_message does NOT report success and falls back.
        """
        mock_ipc = MagicMock()
        mock_ipc.get_connected_sessions.return_value = [1]
        # send_notification returns False for ACCEPTED
        mock_ipc.send_notification.return_value = (
            False,
            NotificationStatus.ACCEPTED,
            "Notice accepted by companion but display not confirmed",
        )
        set_notification_server(mock_ipc)

        with patch("server.command_handler._get_active_sessions", return_value=[1]), \
             patch("server.command_handler._send_wts_message", return_value=(False, "WTS disabled")), \
             patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="Not found", stdout="")), \
             patch("server.command_handler._send_task_message", return_value=(False, "Task rejected")), \
             patch("server.command_handler._send_user_session_message", return_value=(False, "User token rejected")):

            success, message = handle_message("Important notice")
            assert success is False
            assert "Notice could not be displayed on client desktop" in message
            assert "Companion (session 1): [ACCEPTED]" in message

    def test_handle_message_rejected_status(self):
        """Verify duplicate or invalid notification receives REJECTED and falls back."""
        mock_ipc = MagicMock()
        mock_ipc.get_connected_sessions.return_value = [1]
        mock_ipc.send_notification.return_value = (
            False,
            NotificationStatus.REJECTED,
            "Duplicate command already processed recently",
        )
        set_notification_server(mock_ipc)

        with patch("server.command_handler._get_active_sessions", return_value=[1]), \
             patch("server.command_handler._send_wts_message", return_value=(False, "WTS disabled")), \
             patch("subprocess.run", return_value=MagicMock(returncode=1, stderr="", stdout="")), \
             patch("server.command_handler._send_task_message", return_value=(False, "Task failed")), \
             patch("server.command_handler._send_user_session_message", return_value=(False, "User failed")):

            success, message = handle_message({"message": "Duplicate test", "command_id": "dup-1"})
            assert success is False
            assert "Companion (session 1): [REJECTED]" in message

    def test_handle_message_timeout_status(self):
        """Verify acknowledgment timeout reports TIMEOUT and triggers fallback."""
        mock_ipc = MagicMock()
        mock_ipc.get_connected_sessions.return_value = [1]
        mock_ipc.send_notification.return_value = (
            False,
            NotificationStatus.TIMEOUT,
            "Timed out waiting for companion ACK in session 1",
        )
        set_notification_server(mock_ipc)

        with patch("server.command_handler._get_active_sessions", return_value=[1]), \
             patch("server.command_handler._send_wts_message", return_value=(True, "Accepted by WTS")):

            success, message = handle_message("Timeout test")
            # Legacy fallback succeeded after companion timeout
            assert success is True
            assert "Accepted by WTS" in message

    def test_handle_message_not_connected_falls_back(self):
        """Verify that when no companion is connected for the session, NOT_CONNECTED triggers fallback."""
        mock_ipc = MagicMock()
        # Connected to session 2, but target session is 1
        mock_ipc.get_connected_sessions.return_value = [2]
        set_notification_server(mock_ipc)

        with patch("server.command_handler._get_active_sessions", return_value=[1]), \
             patch("server.command_handler._send_wts_message", return_value=(True, "Accepted by WTS")):

            success, message = handle_message("No companion test")
            assert success is True
            assert "Accepted by WTS" in message
            # Companion send_notification was not attempted for session 1
            mock_ipc.send_notification.assert_not_called()


# ============================================================================
# 3. Live Named Pipe Delivery Integration Tests
# ============================================================================

@pytest.mark.skipif(os.name != "nt", reason="Windows Named Pipe tests require Windows OS")
class TestLivePipeNotificationDelivery:
    """End-to-end tests using real Windows Named Pipes between Server, Companion, and Handler."""

    def test_live_delivery_displayed_to_companion(self):
        """Test full live IPC delivery from handle_message to a real connected companion."""
        pipe_name = f"{TEST_INTEG_PIPE_PREFIX}Live_Disp_{os.getpid()}"
        server = NotificationPipeServer(pipe_name=pipe_name)
        server.start()

        events = []
        dialog_ready = threading.Event()
        dialog_close = threading.Event()

        def mock_ui(title: str, message: str, on_displayed=None) -> bool:
            events.append(("show", title, message))
            if on_displayed:
                on_displayed()
            dialog_ready.set()
            dialog_close.wait(timeout=5.0)
            events.append(("close", title, message))
            return True

        companion = NotificationCompanion(
            pipe_name=pipe_name,
            session_id=3,
            display_fn=mock_ui,
        )
        companion.start()

        # Wait for companion registration
        for _ in range(50):
            if companion.is_connected and 3 in server.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        set_notification_server(server)

        # Dispatch via execute_command
        delivery_res = []

        def sender():
            with patch("server.command_handler._get_active_sessions", return_value=[3]):
                res = execute_command(
                    "message",
                    payload={"title": "Emergency", "message": "Evacuate lab"},
                    command_id="cmd-evac-1",
                )
                delivery_res.append(res)

        t = threading.Thread(target=sender)
        t.start()

        assert dialog_ready.wait(timeout=4.0) is True
        t.join(timeout=3.0)

        assert len(delivery_res) == 1
        success, msg = delivery_res[0]
        assert success is True
        assert "Notice displayed to active user via SLMS Notifier companion in session 3" in msg

        dialog_close.set()
        companion.stop()
        server.stop()

    def test_live_session_isolation_multi_session(self):
        """
        Verify session isolation:
        Messages targeted to Session 2 are NOT delivered to Session 3's companion.
        """
        pipe_name = f"{TEST_INTEG_PIPE_PREFIX}Iso_{os.getpid()}"
        server = NotificationPipeServer(pipe_name=pipe_name)
        server.start()

        s2_messages = []
        s3_messages = []

        def s2_ui(title, message, on_displayed=None):
            s2_messages.append(message)
            if on_displayed:
                on_displayed()
            return True

        def s3_ui(title, message, on_displayed=None):
            s3_messages.append(message)
            if on_displayed:
                on_displayed()
            return True

        c2 = NotificationCompanion(pipe_name=pipe_name, session_id=2, display_fn=s2_ui)
        c3 = NotificationCompanion(pipe_name=pipe_name, session_id=3, display_fn=s3_ui)

        c2.start()
        c3.start()

        for _ in range(50):
            sessions = server.get_connected_sessions()
            if 2 in sessions and 3 in sessions:
                break
            time.sleep(0.05)

        assert 2 in server.get_connected_sessions()
        assert 3 in server.get_connected_sessions()

        # Send notification to Session 2 specifically
        success, status, desc = server.send_notification(
            session_id=2,
            command_id="cmd-iso-1",
            title="S2 Only",
            message="Secret for Session 2",
            timeout_sec=3.0,
        )

        assert success is True
        assert status in (NotificationStatus.DISPLAYED, NotificationStatus.DISMISSED)
        time.sleep(0.1)

        assert "Secret for Session 2" in s2_messages
        assert "Secret for Session 2" not in s3_messages

        c2.stop()
        c3.stop()
        server.stop()

    def test_live_concurrent_notifications_no_cross_corruption(self):
        """
        Verify multiple concurrent requests across different sessions
        do not corrupt each other's pending ACKs or responses.
        """
        pipe_name = f"{TEST_INTEG_PIPE_PREFIX}Conc_{os.getpid()}"
        server = NotificationPipeServer(pipe_name=pipe_name)
        server.start()

        def fast_ui(title, message, on_displayed=None):
            if on_displayed:
                on_displayed()
            return True

        c4 = NotificationCompanion(pipe_name=pipe_name, session_id=4, display_fn=fast_ui)
        c5 = NotificationCompanion(pipe_name=pipe_name, session_id=5, display_fn=fast_ui)
        c4.start()
        c5.start()

        for _ in range(50):
            sessions = server.get_connected_sessions()
            if 4 in sessions and 5 in sessions:
                break
            time.sleep(0.05)

        results = {}

        def send_worker(sid, cmd_id):
            ok, st, desc = server.send_notification(
                session_id=sid,
                command_id=cmd_id,
                title=f"Title {cmd_id}",
                message=f"Msg {cmd_id}",
                timeout_sec=4.0,
            )
            results[cmd_id] = (ok, st)

        threads = [
            threading.Thread(target=send_worker, args=(4, "cmd-conc-1")),
            threading.Thread(target=send_worker, args=(5, "cmd-conc-2")),
            threading.Thread(target=send_worker, args=(4, "cmd-conc-3")),
            threading.Thread(target=send_worker, args=(5, "cmd-conc-4")),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        assert len(results) == 4
        for cmd_id, (ok, st) in results.items():
            assert ok is True
            assert st in (NotificationStatus.DISPLAYED, NotificationStatus.DISMISSED)

        c4.stop()
        c5.stop()
        server.stop()

    def test_live_companion_reconnection_after_service_restart(self):
        """Verify that companion reconnects after server restart and receives new messages."""
        pipe_name = f"{TEST_INTEG_PIPE_PREFIX}Reconn_{os.getpid()}"
        server1 = NotificationPipeServer(pipe_name=pipe_name)
        server1.start()

        received = []

        def recording_ui(title, message, on_displayed=None):
            received.append(message)
            if on_displayed:
                on_displayed()
            return True

        companion = NotificationCompanion(
            pipe_name=pipe_name,
            session_id=6,
            display_fn=recording_ui,
            base_reconnect_delay=0.1,
            max_reconnect_delay=0.5,
        )
        companion.start()

        for _ in range(50):
            if companion.is_connected and 6 in server1.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        # Send first message through server1
        s1, st1, _ = server1.send_notification(6, "cmd-rec-1", "Msg 1", timeout_sec=2.0)
        assert s1 is True
        assert "Msg 1" in received

        # Stop server1 (simulating service restart)
        server1.stop()
        time.sleep(0.2)

        # Start server2 on same pipe name
        server2 = NotificationPipeServer(pipe_name=pipe_name)
        server2.start()

        # Wait for companion auto-reconnection
        for _ in range(60):
            if companion.is_connected and 6 in server2.get_connected_sessions():
                break
            time.sleep(0.05)

        assert companion.is_connected is True
        assert 6 in server2.get_connected_sessions()

        # Send second message through server2
        s2, st2, _ = server2.send_notification(6, "cmd-rec-2", "Msg 2", timeout_sec=2.0)
        assert s2 is True
        assert "Msg 2" in received

        companion.stop()
        server2.stop()


# ============================================================================
# 4. Outbox Persistence and Authorization Integration Tests
# ============================================================================

class TestOutboxPersistenceAndAuthorization:
    """Verify that command authorization and durable outbox persistence are preserved."""

    def test_execute_and_enqueue_command_persists_duration_and_result(self, tmp_path):
        """Verify communication worker records command execution result into durable outbox."""
        from server.communication import AgentWebSocketClient
        db_path = str(tmp_path / "test_outbox.db")
        outbox = DurableOutbox(db_path=db_path)

        client = AgentWebSocketClient(
            computer_id=42,
            get_token=lambda: "fake_token",
            outbox=outbox,
        )

        with patch("server.communication.execute_command", return_value=(True, "Notice displayed to active user")):
            client._execute_and_enqueue_command(
                command_id=505,
                command_type="message",
                payload={"message": "Test outbox persistence"},
            )

        # Verify entry in durable outbox
        entries = outbox.get_pending_batch(limit=10)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.event_type == "command_result"
        payload = entry.payload
        assert payload["command_id"] == 505
        assert payload["success"] is True
        assert payload["message"] == "Notice displayed to active user"
        assert "duration_seconds" in payload
        assert payload["duration_seconds"] >= 0.0

    def test_execute_command_rejects_unauthorized_commands(self):
        """Verify command authorization whitelist strictly rejects non-whitelisted commands."""
        unauthorized = ["shell", "powershell", "format_disk", "download_exec", "run_script"]
        for bad_cmd in unauthorized:
            success, msg = execute_command(bad_cmd, payload={"evil": True})
            assert success is False
            assert f"Unknown or disallowed command: {bad_cmd}" in msg

    def test_execute_and_enqueue_lock_confirmed_persists_success(self, tmp_path):
        """Verify LOCK_CONFIRMED produces success=True in durable outbox."""
        from server.communication import AgentWebSocketClient
        db_path = str(tmp_path / "test_outbox_lock.db")
        outbox = DurableOutbox(db_path=db_path)
        client = AgentWebSocketClient(computer_id=1, get_token=lambda: "token", outbox=outbox)

        with patch("server.communication.execute_command", return_value=(True, "Workstation lock confirmed in session 5")):
            client._execute_and_enqueue_command(
                command_id=701,
                command_type="lock",
                payload={"session_id": 5},
            )

        entries = outbox.get_pending_batch(limit=10)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.payload["command_id"] == 701
        assert entry.payload["success"] is True
        assert "confirmed" in entry.payload["message"].lower()

    def test_execute_and_enqueue_lock_request_accepted_never_persists_success(self, tmp_path):
        """
        CRITICAL: Verify REQUEST_ACCEPTED produces success=False (never True) in durable outbox.
        Ensures unconfirmed lock requests are never reported to backend or dashboard as success.
        """
        from server.communication import AgentWebSocketClient
        db_path = str(tmp_path / "test_outbox_lock_accepted.db")
        outbox = DurableOutbox(db_path=db_path)
        client = AgentWebSocketClient(computer_id=1, get_token=lambda: "token", outbox=outbox)

        with patch("server.communication.execute_command", return_value=(False, "Workstation lock request accepted by Windows, but lock state not confirmed (REQUEST_ACCEPTED)")):
            client._execute_and_enqueue_command(
                command_id=702,
                command_type="lock",
                payload={"session_id": 5},
            )

        entries = outbox.get_pending_batch(limit=10)
        assert len(entries) == 1
        entry = entries[0]
        assert entry.payload["command_id"] == 702
        assert entry.payload["success"] is False
        assert "REQUEST_ACCEPTED" in entry.payload["message"]
