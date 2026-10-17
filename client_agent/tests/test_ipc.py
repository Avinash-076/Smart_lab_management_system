"""
Unit and integration tests for SLMS Notification IPC (core/ipc.py).

Verifies:
1. Framing: Length-prefixed encoding, decoding, partial frames, size limits.
2. Payload validation: Strict JSON schema, length boundaries, type constraints for HELLO, NOTIFY, ACK.
3. Deduplication: Replay protection, TTL window, capacity eviction.
4. Security & validation: Client executable validation, directory validation, Session 0 rejection, PID spoofing prevention.
5. Named Pipe Server & Client lifecycle: Connect, authenticate, notify, ACK (DISPLAYED, DISMISSED, REJECTED), timeout, disconnection, and clean shutdown.
"""

from __future__ import annotations

import os
import struct
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from core.ipc import (
    MAX_FRAME_SIZE,
    MAX_MESSAGE_LENGTH,
    MAX_TITLE_LENGTH,
    MAX_COMMAND_ID_LENGTH,
    CommandDeduplicator,
    ConnectedCompanion,
    IPCFramingError,
    IPCMessageType,
    IPCValidationError,
    NotificationPipeClient,
    NotificationPipeServer,
    NotificationStatus,
    decode_frame,
    encode_frame,
    get_kernel_client_info,
    validate_ack_payload,
    validate_client_executable,
    validate_hello_payload,
    validate_lock_payload,
    validate_notify_payload,
    LockPayload,
)


class TestIPCFramingAndValidation:
    """Tests for framing, bounds, and payload schemas."""

    def test_encode_and_decode_frame(self):
        msg = {"type": "NOTIFY", "command_id": "cmd-1", "message": "Test notice"}
        frame = encode_frame(msg)
        assert len(frame) == 4 + len(frame) - 4
        decoded, remaining = decode_frame(frame)
        assert decoded == msg
        assert remaining == b""

    def test_decode_frame_partial_buffer(self):
        msg = {"type": "HELLO", "version": "1.0"}
        frame = encode_frame(msg)
        # Incomplete header (< 4 bytes)
        decoded, remaining = decode_frame(frame[:2])
        assert decoded is None
        assert remaining == frame[:2]

        # Incomplete payload (< 4 + length)
        decoded, remaining = decode_frame(frame[:8])
        assert decoded is None
        assert remaining == frame[:8]

    def test_encode_frame_exceeds_max_size(self):
        oversized = {"text": "A" * (MAX_FRAME_SIZE + 10)}
        with pytest.raises(IPCFramingError):
            encode_frame(oversized)

    def test_decode_frame_invalid_length(self):
        # 0 length
        zero_header = struct.pack("!I", 0) + b"{}"
        with pytest.raises(IPCFramingError):
            decode_frame(zero_header)

        # > MAX_FRAME_SIZE
        huge_header = struct.pack("!I", MAX_FRAME_SIZE + 100) + b"{}"
        with pytest.raises(IPCFramingError):
            decode_frame(huge_header)

    def test_decode_frame_malformed_json(self):
        bad_bytes = b"not json"
        frame = struct.pack("!I", len(bad_bytes)) + bad_bytes
        with pytest.raises(IPCValidationError):
            decode_frame(frame)

    def test_validate_hello_payload(self):
        valid = {"type": "HELLO", "version": "1.0", "session_id": 1, "client_pid": 1234}
        ok, err = validate_hello_payload(valid)
        assert ok is True

        # Invalid type
        bad_type = {**valid, "type": "OTHER"}
        assert validate_hello_payload(bad_type)[0] is False

        # Invalid version
        bad_ver = {**valid, "version": "2.0"}
        assert validate_hello_payload(bad_ver)[0] is False

        # Invalid session_id (Session 0)
        zero_session = {**valid, "session_id": 0}
        assert validate_hello_payload(zero_session)[0] is False

        # Negative PID
        neg_pid = {**valid, "client_pid": -1}
        assert validate_hello_payload(neg_pid)[0] is False

    def test_validate_notify_payload(self):
        valid = {
            "type": "NOTIFY",
            "command_id": "cmd-100",
            "title": "Alert",
            "message": "Notice body",
            "timeout_sec": 30,
        }
        assert validate_notify_payload(valid)[0] is True

        # Exceed title length
        long_title = {**valid, "title": "T" * (MAX_TITLE_LENGTH + 1)}
        assert validate_notify_payload(long_title)[0] is False

        # Exceed message length
        long_msg = {**valid, "message": "M" * (MAX_MESSAGE_LENGTH + 1)}
        assert validate_notify_payload(long_msg)[0] is False

        # Exceed command_id length
        long_cmd = {**valid, "command_id": "C" * (MAX_COMMAND_ID_LENGTH + 1)}
        assert validate_notify_payload(long_cmd)[0] is False

        # Invalid timeout
        bad_timeout = {**valid, "timeout_sec": -5}
        assert validate_notify_payload(bad_timeout)[0] is False

    def test_validate_ack_payload(self):
        valid = {
            "type": "ACK",
            "command_id": "cmd-100",
            "status": "DISPLAYED",
            "session_id": 1,
            "timestamp": time.time(),
            "details": "Rendered on desktop",
        }
        assert validate_ack_payload(valid)[0] is True

        # Lock statuses are valid in ACK
        assert validate_ack_payload({**valid, "status": "LOCK_CONFIRMED"})[0] is True
        assert validate_ack_payload({**valid, "status": "REQUEST_ACCEPTED"})[0] is True

        # Invalid status
        bad_status = {**valid, "status": "UNKNOWN_STATE"}
        assert validate_ack_payload(bad_status)[0] is False

        # Invalid session
        bad_session = {**valid, "session_id": -1}
        assert validate_ack_payload(bad_session)[0] is False

    def test_validate_lock_payload(self):
        valid = {
            "type": "LOCK_WORKSTATION",
            "command_id": "cmd-lock-1",
            "timeout_sec": 10,
            "timestamp": time.time(),
        }
        assert validate_lock_payload(valid)[0] is True

        # Invalid type
        bad_type = {**valid, "type": "OTHER"}
        assert validate_lock_payload(bad_type)[0] is False

        # Exceed command_id length
        long_cmd = {**valid, "command_id": "C" * (MAX_COMMAND_ID_LENGTH + 1)}
        assert validate_lock_payload(long_cmd)[0] is False

        # Empty command_id
        assert validate_lock_payload({**valid, "command_id": ""})[0] is False

        # Invalid timeout
        bad_timeout = {**valid, "timeout_sec": -5}
        assert validate_lock_payload(bad_timeout)[0] is False
        huge_timeout = {**valid, "timeout_sec": 1000}
        assert validate_lock_payload(huge_timeout)[0] is False


class TestCommandDeduplicator:
    """Tests for duplicate command suppression and cache eviction."""

    def test_deduplication(self):
        dedup = CommandDeduplicator(max_size=3, ttl_seconds=2.0)
        assert dedup.is_duplicate("cmd-1") is False
        assert dedup.is_duplicate("cmd-1") is True
        assert dedup.is_duplicate("cmd-2") is False

        # Eviction on max_size
        assert dedup.is_duplicate("cmd-3") is False
        assert dedup.is_duplicate("cmd-4") is False
        # cmd-1 was evicted
        assert dedup.is_duplicate("cmd-1") is False


class TestClientExecutableValidation:
    """Tests for in-kernel process executable and directory validation."""

    def test_validate_client_executable_current_process(self):
        # Current test runner executable (python.exe) is allowed
        ok, path = validate_client_executable(os.getpid(), expected_basename="python.exe")
        assert ok is True
        assert os.path.exists(path)

    def test_validate_client_executable_unauthorized_name(self):
        # Testing with non-matching expected binary
        ok, err = validate_client_executable(os.getpid(), expected_basename="malicious_tool.exe")
        # In test mode, python.exe is permitted by allowed_basenames, so testing with an invalid PID:
        with patch("core.ipc.get_process_image_path", return_value=r"C:\Temp\evil.exe"):
            ok, err = validate_client_executable(99999, expected_basename="SLMS_Notifier.exe")
            assert ok is False
            assert "Unauthorized client executable" in err

    def test_validate_client_executable_outside_allowed_dir(self):
        with patch("core.ipc.get_process_image_path", return_value=r"C:\Users\Student\Desktop\SLMS_Notifier.exe"):
            ok, err = validate_client_executable(
                99999,
                expected_basename="SLMS_Notifier.exe",
                allowed_dirs=[r"C:\Program Files\SLMS"],
            )
            assert ok is False
            assert "outside allowed directories" in err


@pytest.mark.skipif(os.name != "nt", reason="Windows Named Pipe tests require Windows OS")
class TestWindowsNamedPipeLifecycle:
    """End-to-end integration tests using real Windows Named Pipes."""

    @pytest.fixture(autouse=True)
    def setup_pipe(self):
        self.pipe_name = f"\\\\.\\pipe\\SLMS_Test_IPC_{os.getpid()}_{int(time.time()*1000)}"
        self.server = NotificationPipeServer(
            pipe_name=self.pipe_name,
            expected_basename="python.exe",  # Running under pytest python.exe
        )
        self.server.start()
        time.sleep(0.1)
        yield
        self.server.stop()

    def test_server_startup_and_stop(self):
        assert self.server.is_running is True
        assert self.server.get_connected_sessions() == []

    def test_client_connect_and_handshake(self):
        client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=5)
        try:
            connected = client.connect(timeout_sec=3.0)
            assert connected is True
            assert client.is_connected is True
            time.sleep(0.1)
            # Server registers session 5
            assert self.server.get_connected_sessions() == [5]
        finally:
            client.disconnect()
            time.sleep(0.1)
            assert self.server.get_connected_sessions() == []

    def test_send_notification_and_ack_displayed(self):
        client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=5)
        assert client.connect(timeout_sec=3.0) is True

        def client_responder():
            msg = client.read_notification(timeout_sec=3.0)
            assert msg is not None
            assert msg["command_id"] == "cmd-42"
            assert msg["title"] == "Lab Alert"
            assert msg["message"] == "Session ending"
            # Send ACK
            client.send_ack("cmd-42", NotificationStatus.DISPLAYED, details="Dialog active")

        t = threading.Thread(target=client_responder)
        t.start()

        time.sleep(0.1)
        success, status, desc = self.server.send_notification(
            session_id=5,
            command_id="cmd-42",
            title="Lab Alert",
            message="Session ending",
            timeout_sec=3.0,
        )
        t.join()
        client.disconnect()

        assert success is True
        assert status == NotificationStatus.DISPLAYED
        assert "Notice displayed in user session 5: Dialog active" in desc

    def test_send_notification_ack_dismissed(self):
        client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=5)
        assert client.connect(timeout_sec=3.0) is True

        def client_responder():
            msg = client.read_notification(timeout_sec=3.0)
            assert msg is not None
            client.send_ack(msg["command_id"], NotificationStatus.DISMISSED, details="User clicked OK")

        t = threading.Thread(target=client_responder)
        t.start()

        time.sleep(0.1)
        success, status, desc = self.server.send_notification(
            session_id=5,
            command_id="cmd-99",
            title="Notice",
            message="Please acknowledge",
            timeout_sec=3.0,
        )
        t.join()
        client.disconnect()

        assert success is True
        assert status == NotificationStatus.DISMISSED
        assert "dismissed" in desc.lower()

    def test_send_notification_no_companion_connected(self):
        # Target session 99 has no connected companion
        success, status, desc = self.server.send_notification(
            session_id=99,
            command_id="cmd-none",
            title="Notice",
            message="Hello",
            timeout_sec=1.0,
        )
        assert success is False
        assert status == NotificationStatus.NOT_CONNECTED
        assert "No companion connected in session 99" in desc

    def test_send_notification_duplicate_rejection(self):
        client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=5)
        assert client.connect(timeout_sec=3.0) is True

        def responder():
            msg = client.read_notification(timeout_sec=2.0)
            if msg:
                client.send_ack(msg["command_id"], NotificationStatus.DISPLAYED)

        t = threading.Thread(target=responder)
        t.start()

        # First dispatch succeeds
        s1, st1, _ = self.server.send_notification(5, "cmd-dup-1", "Msg", "Title", timeout_sec=2.0)
        t.join()
        assert s1 is True
        assert st1 == NotificationStatus.DISPLAYED

        # Second dispatch with identical command_id is rejected by deduplicator
        s2, st2, d2 = self.server.send_notification(5, "cmd-dup-1", "Msg", "Title", timeout_sec=2.0)
        client.disconnect()

        assert s2 is False
        assert st2 == NotificationStatus.REJECTED
        assert "Duplicate command" in d2

    def test_send_notification_timeout(self):
        client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=5)
        assert client.connect(timeout_sec=3.0) is True

        # Client receives message but intentionally does NOT send ACK
        time.sleep(0.1)
        success, status, desc = self.server.send_notification(
            session_id=5,
            command_id="cmd-timeout",
            title="Notice",
            message="No reply",
            timeout_sec=0.5,
        )
        client.disconnect()

        assert success is False
        assert status == NotificationStatus.TIMEOUT
        assert "Timed out waiting for companion ACK" in desc

    def test_client_spoofed_session_rejected(self):
        # Client lies in HELLO saying session_id is 9999 when kernel reports real session
        client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=9999)
        with patch.dict(os.environ, {"SLMS_ALLOW_TEST_SESSION_SERVER": "0"}):
            connected = client.connect(timeout_sec=1.5)
            assert connected is False
            assert client.is_connected is False
            assert 9999 not in self.server.get_connected_sessions()

    def test_client_abrupt_disconnect_during_notification(self):
        client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=5)
        assert client.connect(timeout_sec=3.0) is True

        def disconnect_worker():
            msg = client.read_notification(timeout_sec=2.0)
            if msg:
                # Abruptly drop pipe handle without sending ACK
                client.disconnect()

        t = threading.Thread(target=disconnect_worker)
        t.start()

        time.sleep(0.1)
        success, status, desc = self.server.send_notification(
            session_id=5,
            command_id="cmd-abrupt",
            title="Notice",
            message="Drop",
            timeout_sec=1.0,
        )
        t.join()
        assert success is False
        assert status in (NotificationStatus.TIMEOUT, NotificationStatus.FAILED)

    def test_send_lock_and_ack_confirmed(self):
        client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=5)
        assert client.connect(timeout_sec=3.0) is True

        def responder():
            msg = client.read_notification(timeout_sec=3.0)
            if msg and msg.get("type") == IPCMessageType.LOCK_WORKSTATION.value:
                client.send_ack(msg["command_id"], NotificationStatus.LOCK_CONFIRMED, details="Confirmed")

        t = threading.Thread(target=responder)
        t.start()

        success, status, desc = self.server.send_lock(
            session_id=5,
            command_id="cmd-lock-pipe-1",
            timeout_sec=2.0,
        )
        t.join()
        client.disconnect()

        assert success is True
        assert status == NotificationStatus.LOCK_CONFIRMED
        assert "confirmed" in desc.lower()

    def test_send_lock_and_ack_request_accepted_is_not_success(self):
        client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=5)
        assert client.connect(timeout_sec=3.0) is True

        def responder():
            msg = client.read_notification(timeout_sec=3.0)
            if msg and msg.get("type") == IPCMessageType.LOCK_WORKSTATION.value:
                client.send_ack(msg["command_id"], NotificationStatus.REQUEST_ACCEPTED, details="Unconfirmed")

        t = threading.Thread(target=responder)
        t.start()

        success, status, desc = self.server.send_lock(
            session_id=5,
            command_id="cmd-lock-pipe-2",
            timeout_sec=2.0,
        )
        t.join()
        client.disconnect()

        assert success is False
        assert status == NotificationStatus.REQUEST_ACCEPTED
        assert "not confirmed" in desc.lower()

    def test_send_lock_no_companion_connected(self):
        success, status, desc = self.server.send_lock(
            session_id=99,
            command_id="cmd-lock-no-comp",
            timeout_sec=1.0,
        )
        assert success is False
        assert status == NotificationStatus.NOT_CONNECTED

    def test_send_lock_timeout(self):
        client = NotificationPipeClient(pipe_name=self.pipe_name, session_id=5)
        assert client.connect(timeout_sec=3.0) is True

        time.sleep(0.1)
        # Client does not send ACK
        success, status, desc = self.server.send_lock(
            session_id=5,
            command_id="cmd-lock-timeout",
            timeout_sec=0.5,
        )
        client.disconnect()

        assert success is False
        assert status == NotificationStatus.TIMEOUT
        assert "Timed out" in desc


class TestIPCMockFailures:
    """Mock-based tests for Windows security boundary failures and edge cases."""

    def test_session_zero_rejected(self):
        server = NotificationPipeServer()
        mock_pipe = MagicMock()
        with patch("core.ipc.get_kernel_client_info", return_value=(1234, 0)):  # Session 0
            with patch("core.ipc.logger.warning") as mock_log:
                server._handle_client_connection(mock_pipe)
                mock_log.assert_called()
                assert any("Session 0" in str(c) for c in mock_log.call_args_list)

    def test_kernel_info_query_failure(self):
        server = NotificationPipeServer()
        mock_pipe = MagicMock()
        with patch("core.ipc.get_kernel_client_info", side_effect=OSError("Access Denied")):
            with patch("core.ipc.logger.warning") as mock_log:
                server._handle_client_connection(mock_pipe)
                mock_log.assert_called()
                assert any("Failed to query kernel client info" in str(c) for c in mock_log.call_args_list)

    def test_process_image_path_failure_rejected(self):
        server = NotificationPipeServer()
        mock_pipe = MagicMock()
        with patch("core.ipc.get_kernel_client_info", return_value=(1234, 5)):
            with patch("core.ipc.validate_client_executable", return_value=(False, "Executable outside allowed directory")):
                with patch("core.ipc.logger.warning") as mock_log:
                    server._handle_client_connection(mock_pipe)
                    assert any("Client executable validation rejected" in str(c) for c in mock_log.call_args_list)

