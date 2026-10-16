import base64
import ctypes
from ctypes import wintypes
import os
import subprocess
import threading

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


def _get_active_user_session_id() -> int | None:
    """Find the active interactive user console session ID."""
    if os.name != "nt":
        return None
    try:
        kernel32 = getattr(ctypes.windll, "kernel32", None)
        wtsapi32 = getattr(ctypes.windll, "wtsapi32", None)
        if not (kernel32 and wtsapi32):
            return None

        console_sid = kernel32.WTSGetActiveConsoleSessionId()
        if isinstance(console_sid, int) and console_sid != 0xFFFFFFFF and console_sid != 0:
            return console_sid

        # Fallback: enumerate active sessions
        pSessionInfo = ctypes.POINTER(WTS_SESSION_INFOW)()
        count = wintypes.DWORD()
        if wtsapi32.WTSEnumerateSessionsW(None, 0, 1, ctypes.byref(pSessionInfo), ctypes.byref(count)):
            active_id = None
            for i in range(count.value):
                s = pSessionInfo[i]
                if s.State == 0 and s.SessionId != 0:  # WTSActive and not Session 0
                    active_id = s.SessionId
                    break
            wtsapi32.WTSFreeMemory(pSessionInfo)
            if active_id is not None:
                return active_id

        # If console_sid is 1 or active, return it
        if isinstance(console_sid, int) and console_sid != 0xFFFFFFFF:
            return console_sid
    except Exception as exc:
        logger.debug(f"Error querying active user session ID: {exc}")
    return None


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


def _send_user_session_message(message: str, title: str = "SLMS Administrator Notice") -> bool:
    """
    Display a native Windows message dialog directly on the active user's desktop
    via PowerShell spawned in the user's session context.
    """
    try:
        ps_code = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show({repr(message)}, {repr(title)}, [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)"
        encoded_cmd = base64.b64encode(ps_code.encode("utf-16le")).decode("ascii")
        cmd = f"powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand {encoded_cmd}"
        return _execute_in_user_session(cmd)
    except Exception as exc:
        logger.debug(f"Failed to launch user session message: {exc}")
        return False


def _send_wts_message(message: str, title: str = "SLMS Administrator Notice", timeout_sec: int = 120) -> bool:
    """
    Deliver administrative notice to interactive user desktop sessions via WTSSendMessageW.
    This safely bridges Session 0 (Windows Service) to active interactive user desktop sessions
    without requiring msg.exe or interactive services detection.
    """
    if os.name != "nt":
        return False

    try:
        wtsapi32 = getattr(ctypes.windll, "wtsapi32", None)
        kernel32 = getattr(ctypes.windll, "kernel32", None)
        if not (wtsapi32 and kernel32):
            return False
    except (AttributeError, OSError) as exc:
        logger.debug(f"wtsapi32 or kernel32 unavailable: {exc}")
        return False

    target_sessions: set[int] = set()

    try:
        console_sid = kernel32.WTSGetActiveConsoleSessionId()
        if isinstance(console_sid, int) and console_sid != 0xFFFFFFFF:
            target_sessions.add(int(console_sid))
    except Exception as exc:
        logger.debug(f"Failed to query active console session ID: {exc}")

    try:
        pSessionInfo = ctypes.POINTER(WTS_SESSION_INFOW)()
        count = wintypes.DWORD()
        if wtsapi32.WTSEnumerateSessionsW(None, 0, 1, ctypes.byref(pSessionInfo), ctypes.byref(count)):
            for i in range(count.value):
                s = pSessionInfo[i]
                if s.State == 0:  # WTSActive
                    target_sessions.add(int(s.SessionId))
            wtsapi32.WTSFreeMemory(pSessionInfo)
    except Exception as enum_err:
        logger.debug(f"Failed to enumerate WTS sessions: {enum_err}")

    if not target_sessions:
        target_sessions.add(1)

    style = 0x40 | 0x40000 | 0x10000
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

    delivered = False
    for sid in target_sessions:
        resp = wintypes.DWORD()
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
                delivered = True
                logger.info(f"WTSSendMessageW delivered successfully to session {sid}")
            else:
                logger.debug(f"WTSSendMessageW returned 0 for session {sid}")
        except Exception as e:
            logger.debug(f"WTSSendMessageW error on session {sid}: {e}")

    return delivered


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


def _lock_via_task_scheduler() -> bool:
    """
    Lock the workstation display by scheduling an immediate interactive task
    under the active logged-in user context.
    """
    if os.name != "nt":
        return False
    users = _get_logged_in_users()
    if not users:
        logger.info("No interactive user logged in; workstation is at lock/login screen.")
        return True

    success = False
    for user in users:
        task_name = f"SLMSLock_{user}"
        tr_cmd = "rundll32.exe user32.dll,LockWorkStation"
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
                    success = True
                    logger.info(f"Lock task successfully dispatched for user {user}")
            subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True, text=True, check=False, timeout=5)
        except Exception as e:
            logger.debug(f"schtasks lock error for {user}: {e}")
    return success


def _send_task_message(message: str, title: str = "SLMS Administrator Notice") -> bool:
    """
    Display a topmost message box on the active interactive desktop by scheduling
    a lightweight VBScript MsgBox task for the logged-in user.
    """
    if os.name != "nt":
        return False
    users = _get_logged_in_users()
    if not users:
        logger.info("No active user logged in to display notice.")
        return False

    import tempfile
    vbs_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False, encoding="utf-8") as f:
            vbs_path = f.name
            clean_msg = message.replace('"', '""')
            clean_title = title.replace('"', '""')
            # 64 = MB_ICONINFORMATION, 4096 = System Modal (topmost)
            f.write(f'MsgBox "{clean_msg}", 64 + 4096, "{clean_title}"\n')

        success = False
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
                        success = True
                        logger.info(f"Notice dialog successfully launched on desktop for user {user}")
                subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], capture_output=True, text=True, check=False, timeout=5)
            except Exception as e:
                logger.debug(f"schtasks message error for {user}: {e}")

        return success
    except Exception as exc:
        logger.debug(f"Error creating task message script: {exc}")
        return False
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


def handle_message(payload):
    """
    Handle administrative message notice.
    Service-safe architecture: Eliminates Session 0 MessageBoxW calls.
    Uses WTSSendMessageW, msg.exe, Task Scheduler, and CreateProcessAsUserW
    to ensure the dialog displays on the active interactive desktop.
    """
    raw_message = str(payload).strip() if payload else "Message from administrator"
    message = raw_message[:1024] if len(raw_message) > 1024 else raw_message
    logger.info(f"Administrator notice received: {message}")

    # 1. Native Windows Terminal Services API (crosses Session 0 boundary safely to desktop)
    wts_delivered = False
    try:
        wts_delivered = _send_wts_message(message, title="SLMS Administrator Notice")
    except Exception as exc:
        logger.debug(f"WTSSendMessage broadcast exception: {exc}")

    # 2. Attempt broadcast to active interactive user sessions via Windows msg.exe
    msg_delivered = False
    try:
        result = subprocess.run(
            ["msg", "*", "/time:15", message],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if result.returncode == 0:
            msg_delivered = True
        else:
            logger.debug(
                f"msg.exe returned code {result.returncode}: "
                f"{result.stderr.strip() or result.stdout.strip()}"
            )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        logger.debug(f"msg.exe broadcast unavailable or timed out: {exc}")
    except Exception as exc:
        logger.debug(f"msg.exe unexpected error: {exc}")

    # 3. Task Scheduler interactive execution inside logged-in user desktop
    task_delivered = False
    if not (wts_delivered or msg_delivered):
        try:
            task_delivered = _send_task_message(message, title="SLMS Administrator Notice")
        except Exception as exc:
            logger.debug(f"Task Scheduler message exception: {exc}")

    # 4. Direct user session process creation via CreateProcessAsUserW (LocalSystem privilege)
    user_delivered = False
    if not (wts_delivered or msg_delivered or task_delivered):
        try:
            user_delivered = _send_user_session_message(message, title="SLMS Administrator Notice")
        except Exception as exc:
            logger.debug(f"User session message exception: {exc}")

    if wts_delivered or msg_delivered or task_delivered or user_delivered:
        return True, "Notice broadcast to interactive user session(s)"

    # Non-interactive fallback: notice was safely recorded in agent logs
    return True, f"Notice recorded in agent log: {message}"


def handle_lock(payload):
    """
    Lock the workstation display.
    Supports both user desktop execution (user32.LockWorkStation) and Session 0
    Windows Service execution (Task Scheduler and CreateProcessAsUser to invoke LockWorkStation
    inside the active user's interactive desktop).
    """
    try:
        if hasattr(ctypes, "windll") and hasattr(ctypes.windll, "user32"):
            ctypes.windll.user32.LockWorkStation()
    except Exception as e:
        logger.exception("Failed to lock workstation via user32")
        return False, str(e)

    # When running as a Windows Service in Session 0, calling LockWorkStation() directly
    # does not lock the interactive user desktop session. Dispatch LockWorkStation
    # inside the active user's interactive desktop session.
    if os.name == "nt":
        try:
            locked = _lock_via_task_scheduler()
            if not locked:
                _execute_in_user_session("rundll32.exe user32.dll,LockWorkStation")
        except Exception as lock_err:
            logger.debug(f"Session 0 lock delegation error: {lock_err}")

    return True, "Workstation locked"


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
    payload=None
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
        f"Executing command: {command_type}"
    )

    try:
        success, message = handler(payload)
    except Exception as exc:
        logger.exception(
            f"Unhandled exception in command handler for '{command_type}': {exc}"
        )
        success, message = False, f"Execution exception: {exc}"

    if message and len(message) > 255:
        message = message[:252] + "..."

    return success, message