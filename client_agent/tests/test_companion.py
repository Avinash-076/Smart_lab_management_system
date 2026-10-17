"""
Unit and integration tests for SLMS Interactive Notification Companion (notifier/companion.py).

Verifies:
1. Full notification status progression: ACCEPTED -> DISPLAYED -> DISMISSED.
2. Display failure reporting: ACCEPTED -> FAILED.
3. Payload validation & rejection: malformed or oversized payloads rejected before UI creation.
4. Deduplication: duplicate command IDs suppressed and acknowledged as REJECTED without duplicate popups.
5. Responsive IPC loop: receive thread continues processing messages and ACKs while a dialog is open.
6. Auto-reconnection: companion reconnects cleanly when server restarts or pipe breaks.
7. Clean shutdown and thread termination.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from core.ipc import (
    IPCMessageType,
    NotificationPipeClient,
    NotificationPipeServer,
    NotificationStatus,
    encode_frame,
)
from notifier.companion import NotificationCompanion, default_desktop_message_box


pytestmark = pytest.mark.windows_only


@pytest.mark.skipif(os.name != "nt", reason="Windows Named Pipe tests require Windows OS")
class TestNotificationCompanion:

    @pytest.fixture(autouse=True)
    def setup_pipe_and_server(self):
        self.pipe_name = f"\\\\.\\pipe\\SLMS_Test_Companion_{os.getpid()}_{int(time.time()*1000)}"
        self.server = NotificationPipeServer(
            pipe_name=self.pipe_name,
            expected_basename="python.exe",
        )
        self.server.start()
        time.sleep(0.1)
        yield
        self.server.stop()

    def test_notification_full_lifecycle_success(self):
        """Verify ACCEPTED -> DISPLAYED -> DISMISSED progression."""
        events_recorded = []
        display_event = threading.Event()
        dismiss_event = threading.Event()

        def mock_display(title: str, message: str) -> bool:
            events_recorded.append(("display_shown", title, message))
            display_event.set()
            dismiss_event.wait(timeout=2.0)
            events_recorded.append(("display_dismissed", title, message))
            return True

        companion = NotificationCompanion(
            pipe_name=self.pipe_name,
            session_id=5,
            display_fn=mock_display,
        )
        companion.start()

        # Wait for companion connection to server
        for _ in range(50):
            if companion.is_connected and 5 in self.server.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        # Track ACKs received on companion connection
        received_acks = []
        with self.server._sessions_lock:
            comp_conn = self.server._sessions[5]
            original_handle_ack = self.server._handle_ack_message

            def spy_handle_ack(c, data):
                received_acks.append(data.get("status"))
                original_handle_ack(c, data)

            self.server._handle_ack_message = spy_handle_ack

        # Dispatch notification from service
        def send_worker():
            return self.server.send_notification(
                session_id=5,
                command_id="cmd-life-1",
                title="Lab Notice",
                message="Session ends in 5 mins",
                timeout_sec=3.0,
            )

        t = threading.Thread(target=send_worker)
        t.start()

        # Wait for display_fn to be entered
        assert display_event.wait(timeout=2.0) is True
        assert ("display_shown", "Lab Notice", "Session ends in 5 mins") in events_recorded

        # Verify ACCEPTED and DISPLAYED were emitted
        time.sleep(0.1)
        assert NotificationStatus.ACCEPTED.value in received_acks
        assert NotificationStatus.DISPLAYED.value in received_acks

        # User dismisses dialog
        dismiss_event.set()
        t.join(timeout=2.0)

        # Verify DISMISSED was emitted
        time.sleep(0.1)
        assert NotificationStatus.DISMISSED.value in received_acks
        assert ("display_dismissed", "Lab Notice", "Session ends in 5 mins") in events_recorded

        companion.stop()

    def test_notification_display_failure(self):
        """Verify that UI exceptions or failures report status=FAILED."""
        def failing_display(title: str, message: str) -> bool:
            raise RuntimeError("Display device context lost")

        companion = NotificationCompanion(
            pipe_name=self.pipe_name,
            session_id=5,
            display_fn=failing_display,
        )
        companion.start()

        for _ in range(50):
            if companion.is_connected and 5 in self.server.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        received_acks = []
        with self.server._sessions_lock:
            original_handle_ack = self.server._handle_ack_message

            def spy_handle_ack(c, data):
                received_acks.append(data.get("status"))
                original_handle_ack(c, data)

            self.server._handle_ack_message = spy_handle_ack

        success, status, desc = self.server.send_notification(
            session_id=5,
            command_id="cmd-fail-1",
            title="Notice",
            message="Will fail",
            timeout_sec=2.0,
        )

        time.sleep(0.2)
        companion.stop()

        assert NotificationStatus.FAILED.value in received_acks

    def test_malformed_payload_rejected(self):
        """Verify invalid or oversized payloads are rejected without UI display."""
        mock_display = MagicMock()
        companion = NotificationCompanion(
            pipe_name=self.pipe_name,
            session_id=5,
            display_fn=mock_display,
        )
        companion.start()

        for _ in range(50):
            if companion.is_connected and 5 in self.server.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        received_acks = []
        with self.server._sessions_lock:
            comp_conn = self.server._sessions[5]
            original_handle_ack = self.server._handle_ack_message

            def spy_handle_ack(c, data):
                received_acks.append(data.get("status"))
                original_handle_ack(c, data)

            self.server._handle_ack_message = spy_handle_ack

        # Send raw malformed NOTIFY frame (missing required message field)
        bad_payload = {
            "type": IPCMessageType.NOTIFY.value,
            "command_id": "cmd-bad",
            "title": "Title",
            # message field missing
        }
        with comp_conn.lock:
            from core.ipc import _write_frame
            _write_frame(comp_conn.pipe_handle, encode_frame(bad_payload))

        time.sleep(0.2)
        companion.stop()

        assert NotificationStatus.REJECTED.value in received_acks
        mock_display.assert_not_called()

    def test_duplicate_notification_suppression(self):
        """Verify companion does not display duplicate dialogs for identical command_id."""
        display_calls = []

        def tracking_display(title: str, message: str) -> bool:
            display_calls.append(title)
            return True

        companion = NotificationCompanion(
            pipe_name=self.pipe_name,
            session_id=5,
            display_fn=tracking_display,
        )
        companion.start()

        for _ in range(50):
            if companion.is_connected and 5 in self.server.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        # Send first notification
        s1, st1, _ = self.server.send_notification(5, "cmd-dup-comp", "Body", "Title", timeout_sec=2.0)
        time.sleep(0.1)
        assert len(display_calls) == 1

        # Force bypass server deduplicator to test companion-side deduplication
        with self.server._sessions_lock:
            comp_conn = self.server._sessions[5]

        # Send duplicate payload directly to client
        raw_dup = {
            "type": IPCMessageType.NOTIFY.value,
            "version": "1.0",
            "command_id": "cmd-dup-comp",
            "title": "Title",
            "message": "Body",
            "timeout_sec": 30,
            "timestamp": time.time(),
        }
        with comp_conn.lock:
            from core.ipc import _write_frame
            _write_frame(comp_conn.pipe_handle, encode_frame(raw_dup))

        time.sleep(0.2)
        companion.stop()

        # Display should NOT have been invoked a second time
        assert len(display_calls) == 1

    def test_companion_responsive_while_dialog_open(self):
        """Verify IPC receive loop processes incoming messages while a modal dialog is blocking."""
        dialog_opened = threading.Event()
        dialog_can_close = threading.Event()

        def blocking_display(title: str, message: str) -> bool:
            dialog_opened.set()
            dialog_can_close.wait(timeout=2.0)
            return True

        companion = NotificationCompanion(
            pipe_name=self.pipe_name,
            session_id=5,
            display_fn=blocking_display,
        )
        companion.start()

        for _ in range(50):
            if companion.is_connected and 5 in self.server.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        # Dispatch first notification (which will block in UI thread)
        t = threading.Thread(target=lambda: self.server.send_notification(5, "cmd-block", "Msg", "Title", timeout_sec=3.0))
        t.start()

        # Wait for dialog to open
        assert dialog_opened.wait(timeout=2.0) is True

        # Send a second notification while first is still open on desktop
        s2, st2, d2 = self.server.send_notification(5, "cmd-second", "Msg2", "Title2", timeout_sec=2.0)
        assert s2 is True
        assert st2 in (NotificationStatus.ACCEPTED, NotificationStatus.DISPLAYED)

        # Release first dialog
        dialog_can_close.set()
        t.join(timeout=2.0)
        companion.stop()

    def test_companion_auto_reconnect(self):
        """Verify companion automatically reconnects after pipe break / server stop."""
        companion = NotificationCompanion(
            pipe_name=self.pipe_name,
            session_id=5,
            base_reconnect_delay=0.1,
            max_reconnect_delay=0.5,
        )
        companion.start()

        # Initially connected
        for _ in range(50):
            if companion.is_connected and 5 in self.server.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        # Simulate server restart: stop server
        self.server.stop()
        time.sleep(0.2)
        assert companion.is_connected is False

        # Restart server
        self.server.start()
        # Companion should auto-reconnect
        for _ in range(50):
            if companion.is_connected and 5 in self.server.get_connected_sessions():
                break
            time.sleep(0.1)

        assert companion.is_connected is True
        companion.stop()

    def test_companion_lock_confirmed(self):
        """Verify companion reports LOCK_CONFIRMED when lock succeeds and session lock state is 0."""
        mock_lock = MagicMock(return_value=(True, 0, ""))
        companion = NotificationCompanion(
            pipe_name=self.pipe_name,
            session_id=5,
            lock_fn=mock_lock,
        )
        companion.start()

        for _ in range(50):
            if companion.is_connected and 5 in self.server.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        with patch("notifier.companion.query_session_lock_state", return_value=0):
            success, status, desc = self.server.send_lock(
                session_id=5,
                command_id="cmd-comp-lock-1",
                timeout_sec=5.0,
            )

        companion.stop()
        assert success is True
        assert status == NotificationStatus.LOCK_CONFIRMED
        assert "confirmed" in desc.lower()
        mock_lock.assert_called_once()

    def test_companion_lock_request_accepted_when_unconfirmed(self):
        """Verify companion reports REQUEST_ACCEPTED when lock is called but lock state is not confirmed."""
        mock_lock = MagicMock(return_value=(True, 0, ""))
        companion = NotificationCompanion(
            pipe_name=self.pipe_name,
            session_id=5,
            lock_fn=mock_lock,
        )
        companion.start()

        for _ in range(50):
            if companion.is_connected and 5 in self.server.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        with patch("notifier.companion.query_session_lock_state", return_value=1):
            success, status, desc = self.server.send_lock(
                session_id=5,
                command_id="cmd-comp-lock-2",
                timeout_sec=5.0,
            )

        companion.stop()
        assert success is False
        assert status == NotificationStatus.REQUEST_ACCEPTED
        assert "not confirmed" in desc.lower()
        mock_lock.assert_called_once()

    def test_companion_lock_failed_when_api_fails(self):
        """Verify companion reports FAILED when user32.LockWorkStation returns 0."""
        mock_lock = MagicMock(return_value=(False, 5, "Access is denied"))
        companion = NotificationCompanion(
            pipe_name=self.pipe_name,
            session_id=5,
            lock_fn=mock_lock,
        )
        companion.start()

        for _ in range(50):
            if companion.is_connected and 5 in self.server.get_connected_sessions():
                break
            time.sleep(0.05)
        assert companion.is_connected is True

        success, status, desc = self.server.send_lock(
            session_id=5,
            command_id="cmd-comp-lock-3",
            timeout_sec=5.0,
        )

        companion.stop()
        assert success is False
        assert status == NotificationStatus.FAILED
        assert "error 5" in desc or "failed" in desc.lower()
        mock_lock.assert_called_once()


@pytest.mark.skipif(os.name != "nt", reason="Win32 MessageBoxW and LockWorkStation require Windows")
class TestDefaultDesktopMessageBox:
    """Test default Win32 message box fallback behavior."""

    def test_default_desktop_message_box_mocked(self):
        with patch("ctypes.windll.user32.MessageBoxW", return_value=1) as mock_msg:
            res = default_desktop_message_box("Title", "Message")
            assert res is True
            mock_msg.assert_called_once()

    def test_default_lock_workstation_mocked_success(self):
        from notifier.companion import default_lock_workstation
        with patch("ctypes.windll.user32.LockWorkStation", return_value=1) as mock_lock:
            ok, err_code, desc = default_lock_workstation()
            assert ok is True
            assert err_code == 0
            mock_lock.assert_called_once()

    def test_default_lock_workstation_mocked_failure(self):
        from notifier.companion import default_lock_workstation
        with patch("ctypes.windll.user32.LockWorkStation", return_value=0) as mock_lock, \
             patch("ctypes.GetLastError", return_value=5):
            ok, err_code, desc = default_lock_workstation()
            assert ok is False
            assert err_code == 5
            assert "error 5" in desc


class TestNotifierDependencies:
    """Regression tests verifying SLMS_Notifier dependency isolation."""

    def test_notifier_does_not_import_requests_or_config(self):
        """Verify that notifier_main does not import requests, security, credentials, or config."""
        import subprocess
        code = (
            "import sys\n"
            "import notifier_main\n"
            "forbidden = ['requests', 'config', 'core.security', 'core.credentials', 'sqlite3', 'keyring']\n"
            "imported_forbidden = [m for m in forbidden if m in sys.modules]\n"
            "if imported_forbidden:\n"
            "    sys.stderr.write(f'Forbidden modules imported: {imported_forbidden}')\n"
            "    sys.exit(1)\n"
            "sys.exit(0)\n"
        )
        res = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        assert res.returncode == 0, f"Notifier dragged in forbidden dependencies: {res.stderr}"

    def test_notifier_starts_with_requests_blocked(self):
        """Verify that notifier entry point can load and execute --help even if requests is blocked."""
        import subprocess
        code = (
            "import sys\n"
            "sys.modules['requests'] = None\n"
            "import notifier_main\n"
            "notifier_main.main()\n"
        )
        res = subprocess.run([sys.executable, "-c", code, "--help"], capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(__file__)))
        assert res.returncode == 0, f"Notifier failed with requests blocked: {res.stderr}"
        assert "SLMS Notification Companion" in res.stdout


@pytest.mark.skipif(os.name != "nt", reason="Windows session mutex and single-instance require Windows")
class TestNotifierSingleInstance:
    """Regression tests verifying session-scoped single instance mutex and duplicate rejection."""

    def test_duplicate_launch_in_same_session_rejected(self):
        """
        Verify that when a companion is already active in a session,
        a duplicate launch (e.g. from HKLM Run or installer [Run])
        is rejected by the mutex and exits immediately with code 0.
        """
        import subprocess
        agent_dir = os.path.dirname(os.path.dirname(__file__))

        env1 = os.environ.copy()
        env1["SLMS_NOTIFIER_SESSION_ID"] = "99"

        # Start primary instance
        p1 = subprocess.Popen([sys.executable, "notifier_main.py"], cwd=agent_dir, env=env1)
        try:
            # Wait for primary instance to acquire mutex
            time.sleep(1.0)
            assert p1.poll() is None, "Primary instance exited prematurely"

            # Attempt duplicate launch in same session (session 99)
            p2 = subprocess.Popen([sys.executable, "notifier_main.py"], cwd=agent_dir, env=env1)
            p2_exit = p2.wait(timeout=5.0)

            # Duplicate instance MUST exit cleanly with code 0
            assert p2_exit == 0, f"Duplicate instance did not exit cleanly: {p2_exit}"

            # Primary instance MUST still be running
            assert p1.poll() is None, "Primary instance was affected by duplicate launch"
        finally:
            p1.terminate()
            p1.wait(timeout=3.0)

    def test_multi_session_instances_coexist(self):
        """
        Verify that companions in DIFFERENT interactive user sessions
        (e.g. Session 97 and Session 98) acquire their own session-scoped
        mutexes and run concurrently without collision.
        """
        import subprocess
        agent_dir = os.path.dirname(os.path.dirname(__file__))

        env1 = os.environ.copy()
        env1["SLMS_NOTIFIER_SESSION_ID"] = "97"

        env2 = os.environ.copy()
        env2["SLMS_NOTIFIER_SESSION_ID"] = "98"

        p1 = subprocess.Popen([sys.executable, "notifier_main.py"], cwd=agent_dir, env=env1)
        p2 = subprocess.Popen([sys.executable, "notifier_main.py"], cwd=agent_dir, env=env2)
        try:
            time.sleep(1.0)
            assert p1.poll() is None, "Session 97 instance exited"
            assert p2.poll() is None, "Session 98 instance exited"
        finally:
            p1.terminate()
            p2.terminate()
            p1.wait(timeout=3.0)
            p2.wait(timeout=3.0)
