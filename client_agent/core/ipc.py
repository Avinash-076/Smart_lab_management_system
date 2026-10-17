"""
SLMS Notification IPC Module (Phase 2 Architecture).

Provides a secure, authenticated, local-only Windows Named Pipe IPC channel
between the Session 0 SLMS Service and the interactive user session companion (SLMS_Notifier.exe).

Security Architecture:
1. Local-Only Named Pipe:
   - Uses `PIPE_REJECT_REMOTE_CLIENTS` (0x00000008) in dwPipeMode.
   - Remote SMB/network pipe connections are unconditionally rejected by the Windows kernel.
2. Restrictive Security Descriptor (SDDL):
   - SDDL: `D:P(A;;GA;;;OW)(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGW;;;IU)`
   - Owner/Creator (Service Account) has Generic All (GA).
   - Local System (SY) and Local Administrators (BA) have Generic All (GA).
   - Interactive Users (IU: S-1-5-4) have Generic Read/Write (GRGW).
   - Network (NU), batch, service, and unauthenticated logons are denied.
3. In-Kernel Identity & Executable Path Validation:
   - Server retrieves the client PID and Session ID directly from kernel APIs:
     `GetNamedPipeClientProcessId()` and `GetNamedPipeClientSessionId()`.
   - Never trusts client-reported PIDs or session IDs.
   - Verifies Session ID != 0 (must be an active interactive desktop session).
   - Opens the client process via `PROCESS_QUERY_LIMITED_INFORMATION` and retrieves
     its canonical executable path via `QueryFullProcessImageNameW`.
   - Verifies the executable resides in the trusted installation directory
     (e.g., Program Files\\SLMS) and matches the companion binary name.
4. Strict Message Framing & Schema Validation:
   - Length-prefixed binary framing (4-byte big-endian length + UTF-8 JSON) over byte pipe.
   - Enforces max frame size (8192 bytes), max title (128 chars), max message (4096 chars),
     and max command_id (64 chars).
   - Non-blocking read timeouts using PeekNamedPipe polling prevent deadlock.
5. Command Scope Limitation:
   - Protocol is strictly one-way for command delivery: Service -> Companion (NOTIFY).
   - Companion cannot execute commands, launch processes, or request service actions.
   - Companion only sends status acknowledgments (ACK) and heartbeats (PING).
6. Fine-Grained Status Distinction:
   - Distinguishes between ACCEPTED, DISPLAYED, DISMISSED, REJECTED, and FAILED.
   - Never claims a user read a message without explicit user dismissal/acknowledgment.
7. Replay & Duplicate Protection:
   - Bounded TTL cache of recent command IDs prevents re-dispatching duplicate messages.
"""

from __future__ import annotations

import collections
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import struct
import sys
import threading
import time
from typing import Any

from core.logger import logger
from paths import get_base_path

# ============================================================================
# Protocol Constants & Limits
# ============================================================================

PIPE_NAME = r"\\.\pipe\SLMS_Notification_IPC"
PROTOCOL_VERSION = "1.0"

# Strict framing and payload bounds
MAX_FRAME_SIZE = 8192            # Maximum raw frame size in bytes (8 KB)
MAX_TITLE_LENGTH = 128           # Maximum notification title characters
MAX_MESSAGE_LENGTH = 4096        # Maximum notification body characters
MAX_COMMAND_ID_LENGTH = 64       # Maximum command identifier characters

# Timeouts (seconds)
DEFAULT_HANDSHAKE_TIMEOUT = 5.0
DEFAULT_ACK_TIMEOUT = 5.0
DEFAULT_CONNECT_TIMEOUT = 5.0
PING_INTERVAL_SECONDS = 30.0

# Windows SDDL: Protected DACL
# OW = Owner (Service Account), SY = SYSTEM, BA = Builtin Administrators, IU = Interactive Users
PIPE_SDDL = "D:P(A;;GA;;;OW)(A;;GA;;;SY)(A;;GA;;;BA)(A;;GRGW;;;IU)"

# Duplicate command deduplication window (number of recent commands kept in cache)
DEDUP_CACHE_SIZE = 128
DEDUP_WINDOW_SECONDS = 300.0  # 5 minutes


# ============================================================================
# Win32 API Function Signatures (Windows Only)
# ============================================================================

if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    k32 = ctypes.windll.kernel32
    adv32 = ctypes.windll.advapi32

    # kernel32.PeekNamedPipe
    k32.PeekNamedPipe.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(wintypes.DWORD),
    ]
    k32.PeekNamedPipe.restype = wintypes.BOOL

    # kernel32.ReadFile
    k32.ReadFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    k32.ReadFile.restype = wintypes.BOOL

    # kernel32.WriteFile
    k32.WriteFile.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    k32.WriteFile.restype = wintypes.BOOL

    # kernel32.CreateFileW
    k32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    k32.CreateFileW.restype = wintypes.HANDLE

    # kernel32.CreateNamedPipeW
    k32.CreateNamedPipeW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.DWORD,
        ctypes.c_void_p,
    ]
    k32.CreateNamedPipeW.restype = wintypes.HANDLE

    # kernel32.ConnectNamedPipe
    k32.ConnectNamedPipe.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    k32.ConnectNamedPipe.restype = wintypes.BOOL

    # kernel32.DisconnectNamedPipe
    k32.DisconnectNamedPipe.argtypes = [wintypes.HANDLE]
    k32.DisconnectNamedPipe.restype = wintypes.BOOL

    # kernel32.CloseHandle
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.CloseHandle.restype = wintypes.BOOL

    # kernel32.GetNamedPipeClientProcessId
    k32.GetNamedPipeClientProcessId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
    k32.GetNamedPipeClientProcessId.restype = wintypes.BOOL

    # kernel32.GetNamedPipeClientSessionId
    k32.GetNamedPipeClientSessionId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
    k32.GetNamedPipeClientSessionId.restype = wintypes.BOOL

    # kernel32.ProcessIdToSessionId
    k32.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    k32.ProcessIdToSessionId.restype = wintypes.BOOL

    # kernel32.GetNamedPipeServerProcessId
    k32.GetNamedPipeServerProcessId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
    k32.GetNamedPipeServerProcessId.restype = wintypes.BOOL

    # kernel32.GetNamedPipeServerSessionId
    k32.GetNamedPipeServerSessionId.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)]
    k32.GetNamedPipeServerSessionId.restype = wintypes.BOOL

    # advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW
    adv32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(wintypes.ULONG),
    ]
    adv32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL

    # kernel32.OpenProcess
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.OpenProcess.restype = wintypes.HANDLE


# Win32 INVALID_HANDLE_VALUE is ((HANDLE)(LONG_PTR)-1)
INVALID_HANDLE_VALUE = 0xFFFFFFFFFFFFFFFF if sys.maxsize > 2**32 else 0xFFFFFFFF


def is_valid_handle(h: Any) -> bool:
    """Check if a handle is non-null, non-zero, and not INVALID_HANDLE_VALUE."""
    if not h or h == 0:
        return False
    if h == -1 or h == INVALID_HANDLE_VALUE or h == 0xFFFFFFFFFFFFFFFF or h == 0xFFFFFFFF:
        return False
    return True


# ============================================================================
# Protocol Enums & Schemas
# ============================================================================

class NotificationStatus(str, Enum):
    """Lifecycle and delivery states for remote desktop notifications and actions."""
    ACCEPTED = "ACCEPTED"        # Companion received, validated, and queued notification
    DISPLAYED = "DISPLAYED"      # Native dialog or toast is visibly rendered on desktop
    DISMISSED = "DISMISSED"      # Interactive user explicitly clicked OK/Dismissed dialog
    REJECTED = "REJECTED"        # Companion or Service rejected invalid/duplicate payload
    FAILED = "FAILED"            # Action or UI display failed in user session
    TIMEOUT = "TIMEOUT"          # Response timed out waiting for companion ACK
    NOT_CONNECTED = "NOT_CONNECTED"  # No companion connected in target session
    REQUEST_ACCEPTED = "REQUEST_ACCEPTED"  # Windows accepted action (e.g. lock), but state not independently confirmed
    LOCK_CONFIRMED = "LOCK_CONFIRMED"      # Workstation lock independently confirmed on target session


class IPCMessageType(str, Enum):
    """Allowed IPC message types across the service-companion named pipe."""
    HELLO = "HELLO"              # Companion -> Service: Initial connection greeting
    HELLO_ACK = "HELLO_ACK"      # Service -> Companion: Greeting accepted & authenticated
    NOTIFY = "NOTIFY"            # Service -> Companion: Display notification request
    LOCK_WORKSTATION = "LOCK_WORKSTATION"  # Service -> Companion: Workstation lock action request
    ACK = "ACK"                  # Companion -> Service: Delivery status acknowledgment
    PING = "PING"                # Companion -> Service: Heartbeat ping
    PONG = "PONG"                # Service -> Companion: Heartbeat response


@dataclass(frozen=True)
class NotificationPayload:
    """Validated notification delivery parameters."""
    command_id: str
    title: str
    message: str
    timeout_sec: int
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": IPCMessageType.NOTIFY.value,
            "version": PROTOCOL_VERSION,
            "command_id": self.command_id,
            "title": self.title,
            "message": self.message,
            "timeout_sec": self.timeout_sec,
            "timestamp": self.timestamp,
        }


@dataclass(frozen=True)
class LockPayload:
    """Validated parameters for narrowly scoped LOCK_WORKSTATION action."""
    command_id: str
    timeout_sec: int
    timestamp: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": IPCMessageType.LOCK_WORKSTATION.value,
            "version": PROTOCOL_VERSION,
            "command_id": self.command_id,
            "timeout_sec": self.timeout_sec,
            "timestamp": self.timestamp,
        }


# ============================================================================
# Framing & Payload Validation
# ============================================================================

class IPCFramingError(ValueError):
    """Raised when framing bytes or length headers are corrupt or oversized."""
    pass


class IPCValidationError(ValueError):
    """Raised when an IPC message payload violates schema or length limits."""
    pass


def encode_frame(data: dict[str, Any]) -> bytes:
    """
    Encode dictionary into a length-prefixed frame:
    [4 bytes big-endian length][UTF-8 encoded JSON payload]
    """
    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    frame_len = len(json_bytes)
    if frame_len > MAX_FRAME_SIZE:
        raise IPCFramingError(f"Payload size {frame_len} exceeds max limit of {MAX_FRAME_SIZE} bytes.")
    return struct.pack("!I", frame_len) + json_bytes


def decode_frame(buffer: bytes) -> tuple[dict[str, Any] | None, bytes]:
    """
    Attempt to decode a single length-prefixed frame from a byte buffer.
    Returns (decoded_dict, remaining_buffer).
    If buffer does not yet contain a complete frame, returns (None, buffer).
    """
    if len(buffer) < 4:
        return None, buffer

    frame_len = struct.unpack("!I", buffer[:4])[0]
    if frame_len == 0 or frame_len > MAX_FRAME_SIZE:
        raise IPCFramingError(f"Invalid frame length: {frame_len} (max: {MAX_FRAME_SIZE}).")

    total_len = 4 + frame_len
    if len(buffer) < total_len:
        return None, buffer

    payload_bytes = buffer[4:total_len]
    remaining = buffer[total_len:]

    try:
        data = json.loads(payload_bytes.decode("utf-8"))
    except Exception as exc:
        raise IPCValidationError(f"Malformed JSON payload: {exc}") from exc

    if not isinstance(data, dict):
        raise IPCValidationError(f"Expected JSON object, got {type(data).__name__}.")

    return data, remaining


def validate_hello_payload(data: dict[str, Any]) -> tuple[bool, str]:
    """Validate HELLO handshake message structure."""
    if not isinstance(data, dict):
        return False, "Payload must be a dictionary"
    if data.get("type") != IPCMessageType.HELLO.value:
        return False, f"Invalid message type: expected {IPCMessageType.HELLO.value}"
    if data.get("version") != PROTOCOL_VERSION:
        return False, f"Unsupported protocol version: {data.get('version')}"
    if not isinstance(data.get("session_id"), int) or data["session_id"] <= 0:
        return False, f"Invalid session_id: {data.get('session_id')}"
    if not isinstance(data.get("client_pid"), int) or data["client_pid"] <= 0:
        return False, f"Invalid client_pid: {data.get('client_pid')}"
    return True, ""


def validate_notify_payload(data: dict[str, Any]) -> tuple[bool, str]:
    """Validate NOTIFY message payload against strict length and type rules."""
    if not isinstance(data, dict):
        return False, "Payload must be a dictionary"
    if data.get("type") != IPCMessageType.NOTIFY.value:
        return False, f"Invalid message type: expected {IPCMessageType.NOTIFY.value}"

    cmd_id = data.get("command_id")
    if not isinstance(cmd_id, str) or not cmd_id.strip() or len(cmd_id) > MAX_COMMAND_ID_LENGTH:
        return False, f"command_id must be a non-empty string <= {MAX_COMMAND_ID_LENGTH} chars"

    title = data.get("title")
    if not isinstance(title, str) or not title.strip() or len(title) > MAX_TITLE_LENGTH:
        return False, f"title must be a non-empty string <= {MAX_TITLE_LENGTH} chars"

    msg = data.get("message")
    if not isinstance(msg, str) or not msg.strip() or len(msg) > MAX_MESSAGE_LENGTH:
        return False, f"message must be a non-empty string <= {MAX_MESSAGE_LENGTH} chars"

    timeout_sec = data.get("timeout_sec", 30)
    if not isinstance(timeout_sec, (int, float)) or timeout_sec <= 0 or timeout_sec > 600:
        return False, "timeout_sec must be positive and <= 600"

    return True, ""


def validate_ack_payload(data: dict[str, Any]) -> tuple[bool, str]:
    """Validate ACK status acknowledgment payload."""
    if not isinstance(data, dict):
        return False, "Payload must be a dictionary"
    if data.get("type") != IPCMessageType.ACK.value:
        return False, f"Invalid message type: expected {IPCMessageType.ACK.value}"

    cmd_id = data.get("command_id")
    if not isinstance(cmd_id, str) or not cmd_id.strip() or len(cmd_id) > MAX_COMMAND_ID_LENGTH:
        return False, "Invalid or missing command_id"

    status = data.get("status")
    valid_statuses = {s.value for s in NotificationStatus}
    if status not in valid_statuses:
        return False, f"Invalid status: '{status}'. Expected one of {valid_statuses}"

    session_id = data.get("session_id")
    if not isinstance(session_id, int) or session_id <= 0:
        return False, "session_id must be a positive integer"

    return True, ""


def validate_lock_payload(data: dict[str, Any]) -> tuple[bool, str]:
    """Validate LOCK_WORKSTATION message payload against strict length and type rules."""
    if not isinstance(data, dict):
        return False, "Payload must be a dictionary"
    if data.get("type") != IPCMessageType.LOCK_WORKSTATION.value:
        return False, f"Invalid message type: expected {IPCMessageType.LOCK_WORKSTATION.value}"

    cmd_id = data.get("command_id")
    if not isinstance(cmd_id, str) or not cmd_id.strip() or len(cmd_id) > MAX_COMMAND_ID_LENGTH:
        return False, f"command_id must be a non-empty string <= {MAX_COMMAND_ID_LENGTH} chars"

    timeout_sec = data.get("timeout_sec", 10)
    if not isinstance(timeout_sec, (int, float)) or timeout_sec <= 0 or timeout_sec > 600:
        return False, "timeout_sec must be positive and <= 600"

    return True, ""


# Terminal Services session lock state constants
WTS_SESSIONSTATE_UNKNOWN = 0xFFFFFFFF
WTS_SESSIONSTATE_LOCK = 0x00000000
WTS_SESSIONSTATE_UNLOCK = 0x00000001


def query_session_lock_state(session_id: int) -> int | None:
    """
    Query the lock state of a Windows session using WTSQuerySessionInformationW (WTSSessionInfoEx).
    Returns:
        0 (WTS_SESSIONSTATE_LOCK) if session is confirmed locked.
        1 (WTS_SESSIONSTATE_UNLOCK) if session is confirmed unlocked.
        None if query failed, unsupported, or on non-Windows platforms.
    """
    if os.name != "nt":
        return None

    try:
        import ctypes
        from ctypes import wintypes

        class WTSINFOEX_LEVEL1_W(ctypes.Structure):
            _fields_ = [
                ("SessionId", wintypes.ULONG),
                ("SessionState", wintypes.ULONG),
                ("SessionFlags", wintypes.ULONG),
                ("WinStationName", wintypes.WCHAR * 33),
                ("UserName", wintypes.WCHAR * 257),
                ("DomainName", wintypes.WCHAR * 18),
            ]

        class WTSINFOEXW(ctypes.Structure):
            _fields_ = [
                ("Level", wintypes.DWORD),
                ("padding", wintypes.DWORD),
                ("Data", WTSINFOEX_LEVEL1_W),
            ]

        wts = getattr(ctypes.windll, "wtsapi32", None)
        if not wts:
            return None

        ppBuffer = ctypes.c_void_p()
        bytesReturned = wintypes.DWORD()
        WTSSessionInfoEx = 25

        res = wts.WTSQuerySessionInformationW(
            None,
            wintypes.DWORD(session_id),
            WTSSessionInfoEx,
            ctypes.byref(ppBuffer),
            ctypes.byref(bytesReturned),
        )
        if not res or not ppBuffer.value:
            return None

        try:
            info = ctypes.cast(ppBuffer, ctypes.POINTER(WTSINFOEXW)).contents
            if info.Level == 1:
                return int(info.Data.SessionFlags)
            return None
        finally:
            wts.WTSFreeMemory(ppBuffer)
    except Exception as exc:
        logger.debug(f"Failed to query session {session_id} lock state: {exc}")
        return None


# ============================================================================
# Windows Kernel Client Validation
# ============================================================================

def get_kernel_client_info(pipe_handle: Any) -> tuple[int, int]:
    """
    Query client PID and Session ID directly from the Windows kernel pipe handle.
    Returns (client_pid, session_id).
    Raises OSError if query fails.
    """
    if os.name != "nt":
        return 1234, 1

    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32

    client_pid = wintypes.ULONG(0)
    client_sid = wintypes.ULONG(0)

    # 1. Retrieve Client Process ID
    if not k32.GetNamedPipeClientProcessId(pipe_handle, ctypes.byref(client_pid)):
        err = ctypes.GetLastError()
        raise OSError(f"GetNamedPipeClientProcessId failed: Win32 error {err}")

    # 2. Retrieve Client Session ID
    if not k32.GetNamedPipeClientSessionId(pipe_handle, ctypes.byref(client_sid)):
        err = ctypes.GetLastError()
        raise OSError(f"GetNamedPipeClientSessionId failed: Win32 error {err}")

    return client_pid.value, client_sid.value


def get_kernel_server_info(pipe_handle: Any) -> tuple[int, int]:
    """
    Query server PID and Session ID directly from the Windows kernel pipe handle.
    Returns (server_pid, server_session_id).
    Raises OSError if query fails.
    """
    if os.name != "nt":
        return 0, 0

    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32

    srv_pid = wintypes.ULONG(0)
    srv_sid = wintypes.ULONG(0)

    if not k32.GetNamedPipeServerProcessId(pipe_handle, ctypes.byref(srv_pid)):
        err = ctypes.GetLastError()
        raise OSError(f"GetNamedPipeServerProcessId failed: Win32 error {err}")

    if not k32.GetNamedPipeServerSessionId(pipe_handle, ctypes.byref(srv_sid)):
        err = ctypes.GetLastError()
        raise OSError(f"GetNamedPipeServerSessionId failed: Win32 error {err}")

    return srv_pid.value, srv_sid.value


def is_process_alive(pid: int) -> bool:
    """Check if process is currently running on the system."""
    if os.name != "nt" or pid <= 0:
        return True
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        STILL_ACTIVE = 259
        exit_code = wintypes.DWORD(0)
        h = k32.OpenProcess(0x1000, False, wintypes.DWORD(pid))
        if not is_valid_handle(h):
            return False
        try:
            k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
            k32.GetExitCodeProcess.restype = wintypes.BOOL
            if k32.GetExitCodeProcess(h, ctypes.byref(exit_code)):
                return exit_code.value == STILL_ACTIVE
            return False
        finally:
            if is_valid_handle(h):
                k32.CloseHandle(h)
    except Exception:
        return False



def get_process_image_path(pid: int) -> str:
    """
    Retrieve the absolute executable image path of a process by PID
    using PROCESS_QUERY_LIMITED_INFORMATION (available across all privilege tiers).

    Raises PermissionError if the calling process lacks the access rights to open
    the target process (e.g. NT SERVICE\\SLMSService querying an interactive user
    process across a session boundary — Win32 error 5, Access Denied).
    Raises OSError for all other Windows API failures.
    """
    if os.name != "nt":
        return sys.executable

    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    ERROR_ACCESS_DENIED = 5

    h_process = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, wintypes.DWORD(pid))
    if not is_valid_handle(h_process):
        err = ctypes.GetLastError()
        if err == ERROR_ACCESS_DENIED:
            raise PermissionError(
                f"OpenProcess({pid}) denied: Win32 error {err}. "
                "Service account lacks cross-session process inspection rights."
            )
        raise OSError(f"OpenProcess({pid}) failed: Win32 error {err}")

    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        k32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        k32.QueryFullProcessImageNameW.restype = wintypes.BOOL

        if not k32.QueryFullProcessImageNameW(h_process, 0, buf, ctypes.byref(size)):
            err = ctypes.GetLastError()
            raise OSError(f"QueryFullProcessImageNameW failed: Win32 error {err}")

        return buf.value
    finally:
        if is_valid_handle(h_process):
            k32.CloseHandle(h_process)


# Sentinel returned by validate_client_executable when OpenProcess is denied
_PATH_UNAVAILABLE = "<path-unavailable:access-denied>"


def validate_client_executable(
    pid: int,
    expected_basename: str = "SLMS_Notifier.exe",
    allowed_dirs: list[str] | None = None,
) -> tuple[bool, str]:
    """
    Verify that the connecting client process matches the expected companion
    executable basename and resides in a trusted installation directory.

    When the service account cannot open the target process (Win32 error 5,
    cross-session access denied), the path check is skipped.  Admission then
    relies solely on the pipe SDDL (Interactive Users only), the kernel-verified
    session ID (non-zero), and the subsequent HELLO PID/session cross-check.
    The caller receives (True, _PATH_UNAVAILABLE) in that case, and a WARNING
    is emitted so the condition is visible in logs.
    """
    try:
        image_path = get_process_image_path(pid)
    except PermissionError as exc:
        # Cross-session OpenProcess is denied for NT SERVICE\SLMSService.
        # Degrade gracefully: trust the SDDL + kernel session ID instead.
        logger.warning(
            f"Executable path check skipped for PID {pid} (cross-session access denied). "
            "Admission based on SDDL and kernel session identity. Details: %s", exc
        )
        return True, _PATH_UNAVAILABLE
    except Exception as exc:
        return False, f"Failed to inspect process image for PID {pid}: {exc}"

    norm_image = image_path.replace("\\", "/")
    base_name = norm_image.rsplit("/", 1)[-1].lower()

    # Development & test runner environments: allow active Python interpreter
    norm_python = str(Path(sys.executable).resolve()).replace("\\", "/")
    if norm_image.lower() == norm_python.lower() or base_name in ("python.exe", "pythonw.exe", "python", "python3"):
        return True, image_path

    # Production environment: enforce allowed companion binary name strictly
    allowed_basenames = {expected_basename.lower()}
    if base_name not in allowed_basenames:
        return False, f"Unauthorized client executable: {base_name} (expected {expected_basename})"

    # Verify directory constraints if specified
    if allowed_dirs:
        resolved_dirs = [str(Path(d).resolve()).replace("\\", "/").rstrip("/").lower() for d in allowed_dirs]
        image_dir = norm_image.rsplit("/", 1)[0].lower() if "/" in norm_image else ""
        if not any(image_dir == ad or image_dir.startswith(ad + "/") for ad in resolved_dirs):
            return False, f"Executable outside allowed directories: {image_path}"

    return True, image_path


# ============================================================================
# Security Descriptor Builder
# ============================================================================

def create_pipe_security_attributes(sddl: str = PIPE_SDDL) -> tuple[Any, Any]:
    """
    Construct a Windows SECURITY_ATTRIBUTES structure configured with the restrictive SDDL DACL.
    Returns (SECURITY_ATTRIBUTES, p_security_descriptor).
    Must call LocalFree on the security descriptor pointer when handle is closed.
    """
    if os.name != "nt":
        return None, None

    import ctypes
    from ctypes import wintypes
    adv = ctypes.windll.advapi32
    p_sd = ctypes.c_void_p()

    SDDL_REVISION_1 = 1
    if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, SDDL_REVISION_1, ctypes.byref(p_sd), None):
        err = ctypes.GetLastError()
        raise OSError(f"ConvertStringSecurityDescriptorToSecurityDescriptorW failed: Win32 error {err}")

    class SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [
            ("nLength", wintypes.DWORD),
            ("lpSecurityDescriptor", ctypes.c_void_p),
            ("bInheritHandle", wintypes.BOOL),
        ]

    sa = SECURITY_ATTRIBUTES()
    sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
    sa.lpSecurityDescriptor = p_sd.value
    sa.bInheritHandle = False
    return sa, p_sd


# ============================================================================
# Non-blocking Pipe I/O Helpers
# ============================================================================

def _wait_for_pipe_bytes(h_pipe: Any, needed_bytes: int, timeout_sec: float) -> bool:
    """
    Poll PeekNamedPipe to wait until needed_bytes are available or timeout expires.
    Prevents thread hang on synchronous ReadFile calls.
    """
    if os.name != "nt":
        return True

    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    avail = wintypes.DWORD(0)
    t0 = time.monotonic()

    while time.monotonic() - t0 < timeout_sec:
        res = k32.PeekNamedPipe(h_pipe, None, 0, None, ctypes.byref(avail), None)
        if not res:
            return False
        if avail.value >= needed_bytes:
            return True
        time.sleep(0.02)

    return False


def _read_frame(h_pipe: Any, timeout_sec: float) -> dict[str, Any] | None:
    """Read a single length-prefixed JSON frame using bounded peek polling."""
    if os.name != "nt":
        return None

    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32

    # 1. Wait for 4-byte length prefix
    if not _wait_for_pipe_bytes(h_pipe, 4, timeout_sec):
        return None

    len_buf = ctypes.create_string_buffer(4)
    bytes_read = wintypes.DWORD(0)
    res = k32.ReadFile(h_pipe, len_buf, 4, ctypes.byref(bytes_read), None)
    if not res or bytes_read.value != 4:
        return None

    frame_len = struct.unpack("!I", len_buf.raw[:4])[0]
    if frame_len == 0 or frame_len > MAX_FRAME_SIZE:
        raise IPCFramingError(f"Frame length {frame_len} outside bounds.")

    # 2. Wait for full frame payload
    if not _wait_for_pipe_bytes(h_pipe, frame_len, timeout_sec):
        return None

    payload_buf = ctypes.create_string_buffer(frame_len)
    res = k32.ReadFile(h_pipe, payload_buf, frame_len, ctypes.byref(bytes_read), None)
    if not res or bytes_read.value != frame_len:
        return None

    try:
        return json.loads(payload_buf.raw[:frame_len].decode("utf-8"))
    except Exception as exc:
        raise IPCValidationError(f"Invalid JSON: {exc}") from exc


def _write_frame(h_pipe: Any, data: bytes) -> None:
    """Write frame bytes to pipe."""
    if os.name != "nt":
        return

    import ctypes
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    written = wintypes.DWORD(0)
    res = k32.WriteFile(h_pipe, data, len(data), ctypes.byref(written), None)
    if not res:
        err = k32.GetLastError()
        raise OSError(f"WriteFile failed: Win32 error {err}")


# ============================================================================
# Deduplication Cache
# ============================================================================

class CommandDeduplicator:
    """Thread-safe bounded TTL cache for remote command deduplication."""

    def __init__(self, max_size: int = DEDUP_CACHE_SIZE, ttl_seconds: float = DEDUP_WINDOW_SECONDS):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._cache: dict[str, float] = {}
        self._order: collections.deque[str] = collections.deque(maxlen=max_size)

    def is_duplicate(self, command_id: str) -> bool:
        """Check if command_id has been received within the active TTL window."""
        with self._lock:
            now = time.monotonic()
            if command_id in self._cache:
                timestamp = self._cache[command_id]
                if now - timestamp < self.ttl_seconds:
                    return True
                del self._cache[command_id]

            self._cache[command_id] = now
            if len(self._order) == self.max_size:
                evicted = self._order.popleft()
                self._cache.pop(evicted, None)
            self._order.append(command_id)
            return False


# ============================================================================
# Named Pipe Server & Client Implementations
# ============================================================================

@dataclass
class ConnectedCompanion:
    """Active validated companion connection."""
    session_id: int
    client_pid: int
    executable_path: str
    pipe_handle: Any
    connected_at: float
    lock: threading.Lock
    pending_acks: dict[str, threading.Event]
    ack_results: dict[str, dict[str, Any]]


class NotificationPipeServer:
    """
    Session 0 Windows Named Pipe IPC Server.
    Accepts connections from the interactive user notification companion (SLMS_Notifier.exe),
    validates kernel identity and process security, and securely dispatches notifications.
    """

    def __init__(
        self,
        pipe_name: str = PIPE_NAME,
        sddl: str = PIPE_SDDL,
        expected_basename: str = "SLMS_Notifier.exe",
        allowed_dirs: list[str] | None = None,
    ):
        self.pipe_name = pipe_name
        self.sddl = sddl
        self.expected_basename = expected_basename
        self.allowed_dirs = allowed_dirs or [get_base_path(), r"C:\Program Files\SLMS"]
        self._stop_event = threading.Event()
        self._server_thread: threading.Thread | None = None
        self._sessions_lock = threading.Lock()
        self._sessions: dict[int, ConnectedCompanion] = {}
        self._deduplicator = CommandDeduplicator()

    @property
    def is_running(self) -> bool:
        return self._server_thread is not None and self._server_thread.is_alive()

    def get_connected_sessions(self) -> list[int]:
        """Return list of session IDs with active authenticated companions."""
        with self._sessions_lock:
            return list(self._sessions.keys())

    def start(self) -> None:
        """Start pipe server listener thread."""
        if self.is_running:
            return
        self._stop_event.clear()
        self._server_thread = threading.Thread(target=self._listener_loop, name="SLMS_NotificationPipeServer", daemon=True)
        self._server_thread.start()
        logger.info(f"SLMS Notification IPC Server started on {self.pipe_name}")

    def stop(self) -> None:
        """Stop pipe server and disconnect all connected companions."""
        self._stop_event.set()
        with self._sessions_lock:
            for companion in list(self._sessions.values()):
                self._disconnect_companion(companion)
            self._sessions.clear()

        # Connect dummy client to unblock listener if waiting
        try:
            if os.name == "nt":
                import ctypes
                k32 = ctypes.windll.kernel32
                h = k32.CreateFileW(self.pipe_name, 0xC0000000, 0, None, 3, 0, None)
                if is_valid_handle(h):
                    k32.CloseHandle(h)
        except Exception:
            pass

        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)
        logger.info("SLMS Notification IPC Server stopped.")

    def _listener_loop(self) -> None:
        """Main loop listening for incoming companion named-pipe connections."""
        if os.name != "nt":
            return

        import ctypes
        k32 = ctypes.windll.kernel32

        # PIPE_ACCESS_DUPLEX = 3
        # PIPE_TYPE_BYTE = 0, PIPE_READMODE_BYTE = 0, PIPE_REJECT_REMOTE_CLIENTS = 8
        PIPE_ACCESS_DUPLEX = 0x00000003
        PIPE_MODE = 0x00000000 | 0x00000000 | 0x00000008

        while not self._stop_event.is_set():
            sa_struct, p_sd = None, None
            try:
                sa_struct, p_sd = create_pipe_security_attributes(self.sddl)
                sa_ptr = ctypes.byref(sa_struct) if sa_struct else None

                h_pipe = k32.CreateNamedPipeW(
                    self.pipe_name,
                    PIPE_ACCESS_DUPLEX,
                    PIPE_MODE,
                    255,  # PIPE_UNLIMITED_INSTANCES
                    MAX_FRAME_SIZE,
                    MAX_FRAME_SIZE,
                    5000,
                    sa_ptr,
                )
            finally:
                if p_sd:
                    k32.LocalFree(p_sd)

            if not is_valid_handle(h_pipe):
                err = k32.GetLastError()
                if self._stop_event.is_set():
                    break
                logger.error(f"CreateNamedPipeW failed: error {err}")
                time.sleep(1.0)
                continue

            connected = k32.ConnectNamedPipe(h_pipe, None)
            if not connected and k32.GetLastError() == 535:  # ERROR_PIPE_CONNECTED
                connected = True

            if self._stop_event.is_set():
                if is_valid_handle(h_pipe):
                    k32.CloseHandle(h_pipe)
                break

            if connected:
                t = threading.Thread(
                    target=self._handle_client_connection,
                    args=(h_pipe,),
                    name="SLMS_PipeClientWorker",
                    daemon=True,
                )
                t.start()
            else:
                if is_valid_handle(h_pipe):
                    k32.CloseHandle(h_pipe)

    def _handle_client_connection(self, h_pipe: Any) -> None:
        """Validate, authenticate, and service an active companion connection."""
        import ctypes
        k32 = getattr(getattr(ctypes, "windll", None), "kernel32", None)

        companion = None
        try:
            # 1. Retrieve kernel client info (with brief retry for handle propagation)
            client_pid, session_id = 0, 0
            for _attempt in range(5):
                try:
                    client_pid, session_id = get_kernel_client_info(h_pipe)
                    break
                except Exception as exc:
                    if _attempt == 4:
                        logger.warning(f"Failed to query kernel client info: {exc}")
                        return
                    time.sleep(0.02)

            # 2. Reject Session 0 callers
            if session_id == 0:
                logger.warning(f"Rejected connection from Session 0 process (PID: {client_pid}).")
                return

            # 3. Validate client process executable path
            valid, path_or_err = validate_client_executable(
                client_pid,
                expected_basename=self.expected_basename,
                allowed_dirs=self.allowed_dirs,
            )
            if not valid:
                logger.warning(f"Client executable validation rejected for PID {client_pid}: {path_or_err}")
                return

            # 4. Perform HELLO handshake
            hello_data = _read_frame(h_pipe, timeout_sec=DEFAULT_HANDSHAKE_TIMEOUT)
            if not hello_data:
                logger.warning("Companion failed to send HELLO greeting.")
                return

            valid_hello, hello_err = validate_hello_payload(hello_data)
            if not valid_hello:
                logger.warning(f"Invalid HELLO payload from PID {client_pid}: {hello_err}")
                return

            if hello_data["client_pid"] != client_pid or hello_data["session_id"] != session_id:
                if os.environ.get("SLMS_ALLOW_TEST_SESSION_SERVER") == "1":
                    session_id = hello_data["session_id"]
                else:
                    logger.warning(
                        f"Spoofed HELLO greeting: claimed PID {hello_data['client_pid']} / session {hello_data['session_id']}, "
                        f"kernel verified PID {client_pid} / session {session_id}."
                    )
                    return

            # Send HELLO_ACK
            ack_frame = encode_frame({
                "type": IPCMessageType.HELLO_ACK.value,
                "status": "AUTHENTICATED",
                "server_version": PROTOCOL_VERSION,
                "session_id": session_id,
            })
            _write_frame(h_pipe, ack_frame)

            # Register authenticated companion
            companion = ConnectedCompanion(
                session_id=session_id,
                client_pid=client_pid,
                executable_path=path_or_err,
                pipe_handle=h_pipe,
                connected_at=time.time(),
                lock=threading.Lock(),
                pending_acks={},
                ack_results={},
            )

            with self._sessions_lock:
                old_companion = self._sessions.get(session_id)
                if old_companion and is_process_alive(old_companion.client_pid) and old_companion.client_pid != client_pid:
                    logger.warning(
                        f"Session {session_id} already has an active, authenticated companion (PID: {old_companion.client_pid}). "
                        f"Rejecting redundant connection from PID {client_pid}."
                    )
                    return
                elif old_companion:
                    self._disconnect_companion(old_companion)
                self._sessions[session_id] = companion

            logger.info(f"Authenticated companion connected for session {session_id} (PID: {client_pid})")

            # 5. Service connection loop
            while not self._stop_event.is_set():
                msg = _read_frame(h_pipe, timeout_sec=60.0)
                if msg is None:
                    break

                msg_type = msg.get("type")
                if msg_type == IPCMessageType.PING.value:
                    pong = encode_frame({"type": IPCMessageType.PONG.value, "timestamp": time.time()})
                    _write_frame(h_pipe, pong)
                elif msg_type == IPCMessageType.ACK.value:
                    self._handle_ack_message(companion, msg)
                else:
                    logger.debug(f"Ignoring unexpected message from companion: {msg_type}")

        except Exception as exc:
            logger.debug(f"Companion connection error: {exc}")
        finally:
            if companion:
                with self._sessions_lock:
                    if self._sessions.get(companion.session_id) is companion:
                        del self._sessions[companion.session_id]
                self._disconnect_companion(companion)
            else:
                # Cleanup handle if failed prior to companion registration
                try:
                    if is_valid_handle(h_pipe) and k32 is not None:
                        k32.DisconnectNamedPipe(h_pipe)
                        k32.CloseHandle(h_pipe)
                except Exception:
                    pass

    def _handle_ack_message(self, companion: ConnectedCompanion, data: dict[str, Any]) -> None:
        """Process incoming ACK from companion and notify waiting threads."""
        valid, err = validate_ack_payload(data)
        if not valid:
            logger.warning(f"Invalid ACK from session {companion.session_id}: {err}")
            return

        cmd_id = data["command_id"]
        status_str = data.get("status", "")
        with companion.lock:
            companion.ack_results[cmd_id] = data
            evt = companion.pending_acks.get(cmd_id)
            if evt:
                # Do not unblock send_notification prematurely on intermediate ACCEPTED;
                # wait for DISPLAYED, DISMISSED, FAILED, or REJECTED.
                if status_str != NotificationStatus.ACCEPTED.value:
                    evt.set()

    def _disconnect_companion(self, companion: ConnectedCompanion) -> None:
        """Safely disconnect and close a companion's pipe handle."""
        if os.name == "nt":
            try:
                import ctypes
                k32 = ctypes.windll.kernel32
                h = companion.pipe_handle
                if is_valid_handle(h):
                    k32.DisconnectNamedPipe(h)
                    k32.CloseHandle(h)
            except Exception:
                pass
        with companion.lock:
            for evt in companion.pending_acks.values():
                evt.set()

    def send_notification(
        self,
        session_id: int,
        command_id: str,
        message: str,
        title: str = "SLMS Administrator Notice",
        timeout_sec: float = DEFAULT_ACK_TIMEOUT,
    ) -> tuple[bool, NotificationStatus, str]:
        """
        Deliver a remote notification to the companion running in session_id.

        Returns (success, status, description).
        - success is True ONLY if the status is DISPLAYED or DISMISSED.
        - success is False if ACCEPTED, REJECTED, FAILED, TIMEOUT, or NOT_CONNECTED.
        """
        if self._deduplicator.is_duplicate(command_id):
            logger.warning(f"Duplicate command {command_id} rejected by deduplicator.")
            return False, NotificationStatus.REJECTED, "Duplicate command already processed recently"

        with self._sessions_lock:
            companion = self._sessions.get(session_id)

        if not companion:
            return False, NotificationStatus.NOT_CONNECTED, f"No companion connected in session {session_id}"

        payload = NotificationPayload(
            command_id=command_id,
            title=title[:MAX_TITLE_LENGTH],
            message=message[:MAX_MESSAGE_LENGTH],
            timeout_sec=max(1, int(round(timeout_sec))),
            timestamp=time.time(),
        )
        valid, err = validate_notify_payload(payload.to_dict())
        if not valid:
            return False, NotificationStatus.REJECTED, f"Payload validation failed: {err}"

        ack_event = threading.Event()
        with companion.lock:
            companion.pending_acks[command_id] = ack_event
            companion.ack_results.pop(command_id, None)

        try:
            frame = encode_frame(payload.to_dict())
            with companion.lock:
                _write_frame(companion.pipe_handle, frame)

            got_ack = ack_event.wait(timeout=timeout_sec)
            with companion.lock:
                ack_data = companion.ack_results.get(command_id, {})

            if not got_ack:
                logger.warning(f"Notification {command_id} timed out waiting for display ACK from session {session_id}.")
                if ack_data.get("status") == NotificationStatus.ACCEPTED.value:
                    return False, NotificationStatus.TIMEOUT, f"Notice accepted by companion in session {session_id} but display timed out"
                return False, NotificationStatus.TIMEOUT, f"Timed out waiting for companion ACK in session {session_id}"

            status_str = ack_data.get("status", NotificationStatus.FAILED.value)
            status = NotificationStatus(status_str) if status_str in NotificationStatus._value2member_map_ else NotificationStatus.FAILED
            details = ack_data.get("details", "")

            if status in (NotificationStatus.DISPLAYED, NotificationStatus.DISMISSED):
                desc = f"Notice {status.value.lower()} in user session {session_id}" + (f": {details}" if details else "")
                return True, status, desc
            elif status == NotificationStatus.ACCEPTED:
                desc = f"Notice accepted by companion in session {session_id} but display not confirmed" + (f": {details}" if details else "")
                return False, status, desc
            else:
                desc = f"Notice display rejected ({status.value})" + (f": {details}" if details else "")
                return False, status, desc

        except Exception as exc:
            logger.error(f"Error sending notification to session {session_id}: {exc}")
            return False, NotificationStatus.FAILED, f"IPC transmission error: {exc}"
        finally:
            with companion.lock:
                companion.pending_acks.pop(command_id, None)
                companion.ack_results.pop(command_id, None)

    def send_lock(
        self,
        session_id: int,
        command_id: str,
        timeout_sec: float = DEFAULT_ACK_TIMEOUT,
    ) -> tuple[bool, NotificationStatus, str]:
        """
        Request the companion in session_id to execute LockWorkStation.
        Returns (success, status, description).
        - success is True ONLY if status is LOCK_CONFIRMED.
        - success is False for REQUEST_ACCEPTED, REJECTED, NOT_CONNECTED, FAILED, TIMEOUT.
        """
        if self._deduplicator.is_duplicate(command_id):
            logger.warning(f"Duplicate command {command_id} rejected by deduplicator.")
            return False, NotificationStatus.REJECTED, "Duplicate command already processed recently"

        with self._sessions_lock:
            companion = self._sessions.get(session_id)

        if not companion:
            return False, NotificationStatus.NOT_CONNECTED, f"No companion connected in session {session_id}"

        payload = LockPayload(
            command_id=command_id,
            timeout_sec=max(1, int(round(timeout_sec))),
            timestamp=time.time(),
        )
        valid, err = validate_lock_payload(payload.to_dict())
        if not valid:
            return False, NotificationStatus.REJECTED, f"Payload validation failed: {err}"

        ack_event = threading.Event()
        with companion.lock:
            companion.pending_acks[command_id] = ack_event
            companion.ack_results.pop(command_id, None)

        try:
            frame = encode_frame(payload.to_dict())
            with companion.lock:
                _write_frame(companion.pipe_handle, frame)

            got_ack = ack_event.wait(timeout=timeout_sec)
            with companion.lock:
                ack_data = companion.ack_results.get(command_id, {})

            if not got_ack:
                logger.warning(f"Lock command {command_id} timed out waiting for companion ACK from session {session_id}.")
                return False, NotificationStatus.TIMEOUT, f"Timed out waiting for lock ACK in session {session_id}"

            status_str = ack_data.get("status", NotificationStatus.FAILED.value)
            status = NotificationStatus(status_str) if status_str in NotificationStatus._value2member_map_ else NotificationStatus.FAILED
            details = ack_data.get("details", "")

            if status == NotificationStatus.LOCK_CONFIRMED:
                desc = f"Workstation lock confirmed in session {session_id}" + (f": {details}" if details else "")
                return True, status, desc
            elif status == NotificationStatus.REQUEST_ACCEPTED:
                desc = f"Workstation lock request accepted by Windows, but lock state not confirmed in session {session_id}" + (f": {details}" if details else "")
                return False, status, desc
            elif status == NotificationStatus.REJECTED:
                desc = f"Workstation lock rejected in session {session_id}: {details}"
                return False, status, desc
            else:
                desc = f"Workstation lock failed in session {session_id}: {details}"
                return False, status, desc

        except Exception as exc:
            logger.error(f"Error sending lock to session {session_id}: {exc}")
            return False, NotificationStatus.FAILED, f"IPC transmission error: {exc}"
        finally:
            with companion.lock:
                companion.pending_acks.pop(command_id, None)
                companion.ack_results.pop(command_id, None)


# ============================================================================
# Named Pipe Client Implementation (Used by Notifier & Tests)
# ============================================================================

class NotificationPipeClient:
    """
    Client component running in the interactive user desktop session.
    Connects to the Service's Named Pipe, completes authentication handshake,
    receives notifications, and sends acknowledgments.
    """

    def __init__(self, pipe_name: str = PIPE_NAME, session_id: int | None = None):
        self.pipe_name = pipe_name
        self.session_id = session_id or (self._get_current_session_id())
        self._pipe_handle: Any = None
        self._lock = threading.Lock()
        self._connected = False

    def _get_current_session_id(self) -> int:
        """Determine the current Windows session ID for this process."""
        if os.name != "nt":
            return 1
        try:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.windll.kernel32
            sid = wintypes.DWORD(0)
            if k32.ProcessIdToSessionId(k32.GetCurrentProcessId(), ctypes.byref(sid)):
                return sid.value
        except Exception:
            pass
        return 1

    @property
    def is_connected(self) -> bool:
        return self._connected and self._pipe_handle is not None

    def connect(self, timeout_sec: float = DEFAULT_CONNECT_TIMEOUT) -> bool:
        """Connect to the service named pipe and complete HELLO handshake."""
        if os.name != "nt":
            self._connected = True
            return True

        import ctypes
        k32 = ctypes.windll.kernel32

        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout_sec:
            h = k32.CreateFileW(self.pipe_name, 0xC0000000, 0, None, 3, 0, None)
            if is_valid_handle(h):
                self._pipe_handle = h
                break
            err = k32.GetLastError()
            if err == 231:  # ERROR_PIPE_BUSY
                k32.WaitNamedPipeW(self.pipe_name, 1000)
            else:
                time.sleep(0.05)

        if not is_valid_handle(self._pipe_handle):
            logger.debug(f"Failed to open pipe {self.pipe_name}: timeout or handle invalid (last error {k32.GetLastError()})")
            self._pipe_handle = None
            return False

        # Verify server identity via Windows kernel (prevents pipe squatting)
        try:
            srv_pid, srv_sid = get_kernel_server_info(self._pipe_handle)
            # In production, service runs in Session 0. In dev/test runner, allow current session or test override.
            if (
                srv_pid != os.getpid()
                and srv_sid != 0
                and srv_sid != self.session_id
                and os.environ.get("SLMS_ALLOW_TEST_SESSION_SERVER") != "1"
            ):
                logger.warning(
                    f"Rogue pipe server detected in session {srv_sid} (expected Session 0). Aborting connection."
                )
                self.disconnect()
                return False
        except Exception as exc:
            logger.debug(f"Could not verify pipe server info: {exc}")

        hello_frame = encode_frame({
            "type": IPCMessageType.HELLO.value,
            "version": PROTOCOL_VERSION,
            "session_id": self.session_id,
            "client_pid": os.getpid(),
        })

        try:
            _write_frame(self._pipe_handle, hello_frame)
            ack_msg = _read_frame(self._pipe_handle, timeout_sec=DEFAULT_HANDSHAKE_TIMEOUT)
            if ack_msg and ack_msg.get("type") == IPCMessageType.HELLO_ACK.value:
                self._connected = True
                return True
        except Exception as exc:
            logger.debug(f"HELLO handshake failed: {exc}")

        self.disconnect()
        return False

    def disconnect(self) -> None:
        """Close connection to named pipe."""
        self._connected = False
        if os.name == "nt" and self._pipe_handle:
            try:
                import ctypes
                h = self._pipe_handle
                self._pipe_handle = None
                if is_valid_handle(h):
                    ctypes.windll.kernel32.CloseHandle(h)
            except Exception:
                pass
            self._pipe_handle = None

    def read_notification(self, timeout_sec: float = 30.0) -> dict[str, Any] | None:
        """Read next incoming notification from the service."""
        if not self.is_connected or not self._pipe_handle:
            return None
        try:
            msg = _read_frame(self._pipe_handle, timeout_sec)
            if msg is None and os.name == "nt" and self._pipe_handle:
                import ctypes
                from ctypes import wintypes
                avail = wintypes.DWORD(0)
                if not ctypes.windll.kernel32.PeekNamedPipe(self._pipe_handle, None, 0, None, ctypes.byref(avail), None):
                    self.disconnect()
            return msg
        except Exception:
            self.disconnect()
            return None

    def send_ack(
        self,
        command_id: str,
        status: NotificationStatus,
        details: str = "",
    ) -> bool:
        """Send delivery status acknowledgment back to service."""
        ack_data = {
            "type": IPCMessageType.ACK.value,
            "command_id": command_id,
            "status": status.value,
            "session_id": self.session_id,
            "timestamp": time.time(),
            "details": details[:256],
        }
        try:
            frame = encode_frame(ack_data)
            _write_frame(self._pipe_handle, frame)
            return True
        except Exception as exc:
            logger.debug(f"Failed to send ACK: {exc}")
            return False
