from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import os
import subprocess
import threading
import time
from typing import Any

from core.ipc import NotificationStatus, query_session_lock_state
from core.logger import logger


class WTS_SESSION_INFOW(ctypes.Structure):
    _fields_ = [
        ("SessionId", wintypes.DWORD),
        ("pWinStationName", wintypes.LPWSTR),
        ("State", wintypes.DWORD),  # WTS_CONNECTSTATE_CLASS (0 = WTSActive)
    ]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


def _get_active_sessions() -> list[int]:
    """Find all active interactive user console/RDP session IDs (excluding Session 0)."""
    if os.name != "nt":
        return []
    sessions: set[int] = set()
    try:
        kernel32 = getattr(ctypes.windll, "kernel32", None)
        wtsapi32 = getattr(ctypes.windll, "wtsapi32", None)
        if not (kernel32 and wtsapi32):
            return []

        console_sid = kernel32.WTSGetActiveConsoleSessionId()
        if isinstance(console_sid, int) and console_sid not in (0xFFFFFFFF, 0):
            sessions.add(int(console_sid))

        pSessionInfo = ctypes.POINTER(WTS_SESSION_INFOW)()
        count = wintypes.DWORD()
        if wtsapi32.WTSEnumerateSessionsW(None, 0, 1, ctypes.byref(pSessionInfo), ctypes.byref(count)):
            for i in range(count.value):
                s = pSessionInfo[i]
                if s.State == 0 and s.SessionId != 0:  # WTSActive and not Session 0
                    sessions.add(int(s.SessionId))
            wtsapi32.WTSFreeMemory(pSessionInfo)
    except Exception as exc:
        logger.debug(f"Error querying active user sessions: {exc}")
    return sorted(sessions)


def _get_active_user_session_id() -> int | None:
    """Find the active interactive user console session ID."""
    active = _get_active_sessions()
    return active[0] if active else None


def _execute_in_user_session(cmd: str) -> bool:
    """
    Spawns a process directly inside the active interactive user's desktop session.
    When running as LocalSystem (Windows Service), queries WTS user token
    and calls CreateProcessAsUserW targeting winsta0\\default.
    """
    if os.name != "nt":
        return False
    try:
        wtsapi32 = getattr(ctypes.windll, "wtsapi32", None)
        kernel32 = getattr(ctypes.windll, "kernel32", None)
        advapi32 = getattr(ctypes.windll, "advapi32", None)
        if not (wtsapi32 and kernel32 and advapi32):
            return False

        session_id = _get_active_user_session_id()
        if session_id is None:
            logger.debug("No active user session found for user session execution")
            return False

        hToken = wintypes.HANDLE()
        if not wtsapi32.WTSQueryUserToken(session_id, ctypes.byref(hToken)):
            logger.debug(f"WTSQueryUserToken failed on session {session_id}: {ctypes.GetLastError()}")
            return False

        try:
            si = STARTUPINFOW()
            si.cb = ctypes.sizeof(STARTUPINFOW)
            si.lpDesktop = "winsta0\\default"
            pi = PROCESS_INFORMATION()

            advapi32.CreateProcessAsUserW.argtypes = [
                wintypes.HANDLE,
                wintypes.LPCWSTR,
                wintypes.LPWSTR,
                ctypes.c_void_p,
                ctypes.c_void_p,
                wintypes.BOOL,
                wintypes.DWORD,
                ctypes.c_void_p,
                wintypes.LPCWSTR,
                ctypes.POINTER(STARTUPINFOW),
                ctypes.POINTER(PROCESS_INFORMATION),
            ]
            advapi32.CreateProcessAsUserW.restype = wintypes.BOOL

            cmd_buf = ctypes.create_unicode_buffer(cmd)
            res = advapi32.CreateProcessAsUserW(
                hToken,
                None,
                cmd_buf,
                None,
                None,
                False,
                0,
                None,
                None,
                ctypes.byref(si),
                ctypes.byref(pi),
            )
            if res:
                kernel32.CloseHandle(pi.hProcess)
                kernel32.CloseHandle(pi.hThread)
                logger.info(f"Successfully launched command in session {session_id}: {cmd}")
                return True
            else:
                logger.debug(f"CreateProcessAsUserW failed: error {ctypes.GetLastError()}")
                return False
        finally:
            kernel32.CloseHandle(hToken)
    except Exception as exc:
        logger.debug(f"Exception during user session execution: {exc}")
        return False


def _send_user_session_message(message: str, title: str = "SLMS Administrator Notice") -> tuple[bool, str]:
    """
    Display a native Windows message dialog directly on the active user's desktop
    via PowerShell spawned in the user's session context.
    Returns (success, description).
    """
    try:
        ps_code = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show({repr(message)}, {repr(title)}, [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)"
        encoded_cmd = base64.b64encode(ps_code.encode("utf-16le")).decode("ascii")
        cmd = f"powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand {encoded_cmd}"
        if _execute_in_user_session(cmd):
            return True, "Notice dialog launched in user session via CreateProcessAsUser"
        return False, "CreateProcessAsUser failed (insufficient privileges under service account)"
    except Exception as exc:
        logger.debug(f"Failed to launch user session message: {exc}")
        return False, f"User session spawn error: {exc}"


def _send_wts_message(message: str, title: str = "SLMS Administrator Notice", timeout_sec: int = 30) -> tuple[bool, str]:
    """
    Deliver administrative notice to interactive user desktop sessions via WTSSendMessageW.
    This safely bridges Session 0 (Windows Service) to active interactive user desktop sessions
    without requiring msg.exe or interactive services detection.
    Returns (success, description).
    """
    if os.name != "nt":
        return False, "Non-Windows OS"

    try:
        wtsapi32 = getattr(ctypes.windll, "wtsapi32", None)
        kernel32 = getattr(ctypes.windll, "kernel32", None)
        if not (wtsapi32 and kernel32):
            return False, "Terminal Services API unavailable"
    except (AttributeError, OSError) as exc:
        logger.debug(f"wtsapi32 or kernel32 unavailable: {exc}")
        return False, f"WTS library unavailable: {exc}"

    target_sessions = _get_active_sessions()
    if not target_sessions:
        return False, "No active user desktop sessions found"

    # MB_OK (0x0) | MB_ICONINFORMATION (0x40) | MB_TOPMOST (0x40000) | MB_SETFOREGROUND (0x10000)
    style = 0x00000040 | 0x00040000 | 0x00010000
    title_bytes = len(title.encode("utf-16le"))
    msg_bytes = len(message.encode("utf-16le"))

    try:
        wtsapi32.WTSSendMessageW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.LPWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            wintypes.BOOL,
        ]
        wtsapi32.WTSSendMessageW.restype = wintypes.BOOL
    except Exception:
        pass

    delivered_sessions: list[int] = []
    last_err = None
    for sid in target_sessions:
        resp = wintypes.DWORD(0)
        try:
            ret = wtsapi32.WTSSendMessageW(
                None,
                sid,
                title,
                title_bytes,
                message,
                msg_bytes,
                style,
                timeout_sec,
                ctypes.byref(resp),
                False,  # Return immediately, dialog remains visible on desktop
            )
            if ret:
                delivered_sessions.append(sid)
                logger.info(f"WTSSendMessageW accepted for session {sid}")
            else:
                last_err = ctypes.GetLastError() if hasattr(ctypes, "GetLastError") else "unknown"
                logger.debug(f"WTSSendMessageW returned 0 for session {sid}: Win32 error {last_err}")
        except Exception as e:
            last_err = str(e)
            logger.debug(f"WTSSendMessageW error on session {sid}: {e}")

    if delivered_sessions:
        sids_str = ", ".join(str(s) for s in delivered_sessions)
        return True, f"Notice display request accepted by Windows Terminal Services for session(s): {sids_str}"

    err_suffix = f" (Win32 error {last_err})" if last_err is not None else ""
    return False, f"WTSSendMessageW delivery rejected by Windows{err_suffix}"


def _get_logged_in_users() -> list[str]:
    """Find currently logged-in active interactive users on Windows."""
    if os.name != "nt":
        return []
    users = set()
    # 1. quser / query user
    try:
        res = subprocess.run(["quser"], capture_output=True, text=True, check=False, timeout=3)
        if res.stdout:
            for line in res.stdout.splitlines()[1:]:
                parts = line.strip().split()
                if parts:
                    username = parts[0].lstrip(">").strip()
                    if username and username.lower() not in ("services", "rdp-tcp", "console"):
                        users.add(username)
    except Exception:
        pass

    # 2. CIM / WMI ComputerSystem UserName fallback
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", "(Get-CimInstance Win32_ComputerSystem).UserName"],
            capture_output=True,
            text=True,
            check=False,
            timeout=3,
        )
        if res.returncode == 0 and res.stdout.strip():
            raw_user = res.stdout.strip().split("\\")[-1].strip()
            if raw_user:
                users.add(raw_user)
    except Exception:
        pass

    return list(users)




def _send_task_message(message: str, title: str = "SLMS Administrator Notice") -> tuple[bool, str]:
    """
    Display a topmost message box on the active interactive desktop by scheduling
    a lightweight VBScript MsgBox task for the logged-in user.
    Returns (success, description).
    """
    if os.name != "nt":
        return False, "Non-Windows OS"
    users = _get_logged_in_users()
    if not users:
        return False, "No active user logged in"

    import tempfile
    vbs_path = None
    try:
        # Use utf-16 with BOM so native wscript.exe parses Unicode and symbols accurately
        with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False, encoding="utf-16") as f:
            vbs_path = f.name
            clean_msg = message.replace('"', '""')
            clean_title = title.replace('"', '""')
            # 64 = MB_ICONINFORMATION, 4096 = System Modal (topmost)
            f.write(f'MsgBox "{clean_msg}", 64 + 4096, "{clean_title}"\n')

        delivered_users: list[str] = []
        last_error = ""
        for user in users:
            task_name = f"SLMSNotice_{user}"
            tr_cmd = f'wscript.exe "{vbs_path}"'
            try:
                create_res = subprocess.run(
                    ["schtasks", "/create", "/tn", task_name, "/tr", tr_cmd, "/sc", "once", "/st", "23:59", "/f", "/it", "/ru", user],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=5,
                )
                if create_res.returncode == 0:
                    run_res = subprocess.run(
                        ["schtasks", "/run", "/tn", task_name],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=5,
                    )
                    if run_res.returncode == 0:
                        delivered_users.append(user)
                        logger.info(f"Notice dialog successfully launched on desktop for user {user}")
                    else:
                        last_error = (run_res.stderr.strip() or run_res.stdout.strip())[:100]
                else:
                    last_error = (create_res.stderr.strip() or create_res.stdout.strip())[:100]
                subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True, text=True, check=False, timeout=5)
            except Exception as e:
                last_error = str(e)[:100]
                logger.debug(f"schtasks message error for {user}: {e}")

        if delivered_users:
            users_str = ", ".join(delivered_users)
            return True, f"Notice dialog launched via Task Scheduler for user(s): {users_str}"

        err_suffix = f": {last_error}" if last_error else ""
        return False, f"Task Scheduler rejected interactive task{err_suffix}"
    except Exception as exc:
        logger.debug(f"Error creating task message script: {exc}")
        return False, f"Task Scheduler error: {exc}"
    finally:
        if vbs_path:
            def _cleanup():
                import time
                time.sleep(15)
                try:
                    if os.path.isfile(vbs_path):
                        os.remove(vbs_path)
                except Exception:
                    pass
            threading.Thread(target=_cleanup, daemon=True).start()


_ACTIVE_NOTIFICATION_SERVER: Any | None = None
_SERVER_LOCK = threading.Lock()


def set_notification_server(server: Any | None) -> None:
    """Register the active Session 0 NotificationPipeServer."""
    global _ACTIVE_NOTIFICATION_SERVER
    with _SERVER_LOCK:
        _ACTIVE_NOTIFICATION_SERVER = server


def get_notification_server() -> Any | None:
    """Retrieve the active Session 0 NotificationPipeServer."""
    with _SERVER_LOCK:
        return _ACTIVE_NOTIFICATION_SERVER


def handle_message(payload, command_id: int | str | None = None) -> tuple[bool, str]:
    """
    Handle administrative message notice.
    Service-safe architecture: Eliminates Session 0 MessageBoxW calls.
    First attempts delivery via the authenticated user-session companion (SLMS_Notifier)
    over local named-pipe IPC.
    Falls back to WTSSendMessageW, msg.exe, Task Scheduler, and CreateProcessAsUserW
    if no companion is active.

    Guarantees:
    - Never returns True merely because a message was logged or enqueued.
    - Accurately discriminates between companion display states (ACCEPTED, DISPLAYED,
      DISMISSED), fallback API acceptance, lack of interactive session, and mechanism failure.
    - Does not claim user acknowledged or saw the message without explicit dismissal evidence.
    """
    # Parse payload (dict or string)
    if isinstance(payload, dict):
        raw_message = str(payload.get("message") or payload.get("text") or "").strip()
        title = str(payload.get("title") or "SLMS Administrator Notice")[:128]
        cmd_id = str(command_id or payload.get("command_id") or f"cmd_{int(time.time()*1000)}")[:64]
    else:
        raw_message = str(payload).strip() if payload else "Message from administrator"
        title = "SLMS Administrator Notice"
        cmd_id = str(command_id or f"cmd_{int(time.time()*1000)}")[:64]

    message = raw_message[:4096] if len(raw_message) > 4096 else raw_message
    logger.info(f"Administrator notice dispatch requested: command_id={cmd_id}, title='{title}'")

    # Step 0: Check whether any interactive user session or user logon exists
    target_sessions = _get_active_sessions()
    logged_in_users = _get_logged_in_users() if not target_sessions else []
    if not target_sessions and not logged_in_users:
        logger.info("Notice delivery skipped: No interactive user session currently logged in.")
        return False, "No interactive user session available to display notice"

    failures = []

    # 1. Primary Route: SLMS Interactive User Companion (Named Pipe IPC)
    ipc_server = get_notification_server()
    if ipc_server is not None:
        try:
            connected_sessions = ipc_server.get_connected_sessions()
            deliver_sessions = [s for s in target_sessions if s in connected_sessions] if target_sessions else connected_sessions

            if deliver_sessions:
                delivered = []
                for sid in deliver_sessions:
                    from core.ipc import NotificationStatus
                    ok, status, desc = ipc_server.send_notification(
                        session_id=sid,
                        command_id=cmd_id,
                        message=message,
                        title=title,
                        timeout_sec=5.0,
                    )
                    if ok:
                        delivered.append((sid, status, desc))
                    else:
                        failures.append(f"Companion (session {sid}): [{status.value}] {desc}")

                if delivered:
                    sid, status, desc = delivered[0]
                    if status == NotificationStatus.DISMISSED:
                        return True, f"Notice dismissed by user via SLMS Notifier companion in session {sid}"
                    elif status == NotificationStatus.DISPLAYED:
                        return True, f"Notice displayed to active user via SLMS Notifier companion in session {sid}"
                    else:
                        failures.append(f"Companion (session {sid}): [{status.value}] {desc}")
            else:
                failures.append("Companion IPC: No active companion connected for target session(s)")
        except Exception as exc:
            logger.debug(f"Companion IPC dispatch exception: {exc}")
            failures.append(f"Companion IPC error: {exc}")
    else:
        failures.append("Companion IPC: Notification server not running")

    # 2. Native Windows Terminal Services API (legacy fallback)
    try:
        wts_ok, wts_msg = _send_wts_message(message, title=title)
        if wts_ok:
            return True, wts_msg
        failures.append(f"WTSSendMessage: {wts_msg}")
    except Exception as exc:
        logger.debug(f"WTSSendMessage broadcast exception: {exc}")
        failures.append(f"WTSSendMessage: {exc}")

    # 3. Attempt broadcast to active interactive user sessions via Windows msg.exe
    try:
        result = subprocess.run(
            ["msg", "*", "/time:15", message[:1024]],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode == 0:
            return True, "Notice display request accepted by Windows msg.exe"
        err_msg = (result.stderr.strip() or result.stdout.strip())[:80]
        failures.append(f"msg.exe (exit {result.returncode}{f': {err_msg}' if err_msg else ''})")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.debug(f"msg.exe broadcast unavailable or timed out: {exc}")
        failures.append(f"msg.exe unavailable ({exc.__class__.__name__})")
    except Exception as exc:
        logger.debug(f"msg.exe unexpected error: {exc}")
        failures.append(f"msg.exe error: {exc}")

    # 4. Task Scheduler interactive execution inside logged-in user desktop
    try:
        task_ok, task_msg = _send_task_message(message, title=title)
        if task_ok:
            return True, task_msg
        failures.append(f"TaskScheduler: {task_msg}")
    except Exception as exc:
        logger.debug(f"Task Scheduler message exception: {exc}")
        failures.append(f"TaskScheduler: {exc}")

    # 5. Direct user session process creation via CreateProcessAsUserW
    try:
        user_ok, user_msg = _send_user_session_message(message, title=title)
        if user_ok:
            return True, user_msg
        failures.append(f"UserSession: {user_msg}")
    except Exception as exc:
        logger.debug(f"User session message exception: {exc}")
        failures.append(f"UserSession: {exc}")

    # ALL mechanisms failed: NEVER return True for log fallback!
    summary = "; ".join(failures[:3])
    logger.warning(f"Notice display failed across all mechanisms: {summary}")
    return False, f"Notice could not be displayed on client desktop ({summary})"


def handle_lock(payload=None, command_id: int | str | None = None) -> tuple[bool, str]:
    """
    Lock the workstation display.

    Architecture & Result Semantics:
    1. Primary Route: SLMS Interactive User Companion (Named Pipe IPC).
       Routes the lock request to the intended interactive session via the
       authenticated companion (SLMS_Notifier) running in that session.
       The companion calls user32.LockWorkStation and verifies if the locked
       state is independently confirmed.
    2. Explicit Result Semantics:
       - LOCK_CONFIRMED: Workstation is independently confirmed locked -> returns (True, message).
       - REQUEST_ACCEPTED: Windows accepted the lock API call, but locked state was not
         independently confirmed -> returns (False, message). (Never silently mapped to True).
       - NOT_CONNECTED: No companion is connected in the target session -> returns (False, message).
       - REJECTED: Request failed authorization, validation, or deduplication -> returns (False, message).
       - FAILED: The API call or execution failed -> returns (False, message).
       - TIMEOUT: Companion timed out -> returns (False, message).
    3. Removal of Misleading Fallbacks:
       schtasks /run success and CreateProcessAsUserW process launch success alone cannot
       produce LOCK_CONFIRMED and are not used as false-success fallbacks.
    4. Direct interactive execution fallback:
       When running directly in an interactive user session without an IPC server (e.g. CLI/tests),
       user32.LockWorkStation is called directly, and confirmed via session lock query.
    """
    cmd_id = str(command_id or f"cmd_lock_{int(time.time() * 1000)}")[:64]
    intended_session = None
    if isinstance(payload, dict):
        intended_session = payload.get("session_id")

    console_sid = _get_active_user_session_id()

    # 1. Primary Route: Companion IPC Server
    ipc_server = get_notification_server()
    if ipc_server is not None:
        connected_sessions = ipc_server.get_connected_sessions()

        if intended_session is not None:
            if intended_session not in connected_sessions:
                logger.warning(
                    f"Workstation lock rejected: requested session {intended_session} "
                    f"has no connected companion (connected: {connected_sessions})."
                )
                return False, f"Workstation lock failed: companion not connected in requested session {intended_session} (NOT_CONNECTED)"
            dest_session = intended_session
        else:
            # Route to intended interactive console session, or first connected companion
            if console_sid is not None and console_sid in connected_sessions:
                dest_session = console_sid
            elif connected_sessions:
                dest_session = connected_sessions[0]
            else:
                dest_session = None

        if dest_session is not None:
            logger.info(f"Routing workstation lock {cmd_id} to companion in session {dest_session}...")
            success, status, desc = ipc_server.send_lock(
                session_id=dest_session,
                command_id=cmd_id,
                timeout_sec=5.0,
            )
            logger.info(f"Companion lock response for session {dest_session}: success={success}, status={status.value}, desc='{desc}'")
            return success, desc
        else:
            logger.warning("Workstation lock failed: no interactive companion connected in any session.")
            return False, "Workstation lock failed: no companion connected in active user session (NOT_CONNECTED)"

    # 2. Non-service / Direct Interactive Execution (e.g. running directly in user session or tests without IPC)
    if os.name == "nt":
        import ctypes as _ctypes
        _in_session_0 = False
        _current_sid = 0
        try:
            _sid_val = _ctypes.wintypes.DWORD(0)
            if _ctypes.windll.kernel32.ProcessIdToSessionId(
                _ctypes.windll.kernel32.GetCurrentProcessId(),
                _ctypes.byref(_sid_val),
            ):
                _current_sid = _sid_val.value
                _in_session_0 = _sid_val.value == 0
        except Exception:
            pass

        if not _in_session_0 and _current_sid != 0:
            try:
                if hasattr(_ctypes, "windll") and hasattr(_ctypes.windll, "user32"):
                    ret = _ctypes.windll.user32.LockWorkStation()
                    if ret:
                        lock_state = query_session_lock_state(_current_sid)
                        if lock_state == 0:  # WTS_SESSIONSTATE_LOCK
                            return True, f"Workstation lock confirmed on session {_current_sid}"
                        return False, f"Workstation lock request accepted by Windows on session {_current_sid}, but lock state not confirmed (REQUEST_ACCEPTED)"
                    err = _ctypes.GetLastError()
                    logger.warning(f"user32.LockWorkStation() returned 0: Win32 error {err}")
                    return False, f"user32.LockWorkStation failed with Win32 error {err} (FAILED)"
            except Exception as e:
                logger.exception("Failed to lock workstation via direct user32 call")
                return False, f"Workstation lock error: {e} (FAILED)"

        # In Session 0 without IPC server: cannot lock without companion
        logger.warning("Workstation lock failed: running in Session 0 and no notification IPC server is registered.")
        return False, "Workstation lock failed: service in Session 0 requires an active companion (NOT_CONNECTED)"

    return False, "Workstation lock not supported on this platform"


def handle_restart(payload):
    try:
        subprocess.run(
            [
                "shutdown",
                "/r",
                "/t",
                "5"
            ],
            check=True
        )

        return True, "Restart scheduled in 5 seconds"

    except Exception as e:
        logger.exception(
            "Failed to restart computer"
        )

        return False, str(e)


def handle_shutdown(payload):
    try:
        subprocess.run(
            [
                "shutdown",
                "/s",
                "/t",
                "5"
            ],
            check=True
        )

        return True, "Shutdown scheduled in 5 seconds"

    except Exception as e:
        logger.exception(
            "Failed to shutdown computer"
        )

        return False, str(e)


COMMAND_WHITELIST = {
    "message": handle_message,
    "lock": handle_lock,
    "restart": handle_restart,
    "shutdown": handle_shutdown,
}


def execute_command(
    command_type: str,
    payload=None,
    command_id: int | str | None = None,
):
    handler = COMMAND_WHITELIST.get(
        command_type
    )

    if handler is None:

        logger.warning(
            f"Rejected unknown command: {command_type}"
        )

        return (
            False,
            f"Unknown or disallowed command: {command_type}"
        )

    logger.info(
        f"Executing command: {command_type}" + (f" (id={command_id})" if command_id else "")
    )

    try:
        if command_type in ("message", "lock") and command_id is not None:
            try:
                success, message = handler(payload, command_id=command_id)
            except TypeError:
                success, message = handler(payload)
        else:
            success, message = handler(payload)
    except Exception as exc:
        logger.exception(
            f"Unhandled exception in command handler for '{command_type}': {exc}"
        )
        success, message = False, f"Execution exception: {exc}"

    if message and len(message) > 255:
        message = message[:252] + "..."

    return success, message