"""
SLMS Interactive User Notification Companion - Main Entry Point.

Standalone entry point for SLMS_Notifier.exe.
Runs in the logged-in user's interactive Windows desktop session (Session 1..N).

Responsibilities:
1. Session-scoped single instance mutex (prevents multiple notifier instances in same session).
2. Clean logging setup.
3. Top-level exception and signal handling.
4. Starts and maintains NotificationCompanion lifecycle.
"""

from __future__ import annotations

import os
import sys

from core.logger import logger
from core.single_instance import SingleInstanceMutex
from notifier.companion import NotificationCompanion


def get_current_session_id() -> int:
    """Determine the current Windows session ID for this process."""
    env_sid = os.environ.get("SLMS_NOTIFIER_SESSION_ID")
    if env_sid and env_sid.isdigit():
        return int(env_sid)

    if os.name != "nt":
        return 1
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        sid = wintypes.DWORD(0)
        k32.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        k32.ProcessIdToSessionId.restype = wintypes.BOOL
        if k32.ProcessIdToSessionId(k32.GetCurrentProcessId(), ctypes.byref(sid)):
            return sid.value
    except Exception:
        pass
    return 1


def main() -> None:
    """Launch the SLMS Notification Companion."""
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("--help", "-h", "help"):
        if sys.stdout is not None:
            print("SLMS Notification Companion (SLMS_Notifier.exe)")
            print("Runs in the active user desktop session to securely display administrative notices.")
        return

    session_id = get_current_session_id()
    mutex_name = f"Local\\SLMS_Notifier_Mutex_Session_{session_id}"
    mutex = SingleInstanceMutex(name=mutex_name)

    if not mutex.acquire():
        logger.info(f"SLMS Notification Companion is already active in session {session_id}. Exiting duplicate instance.")
        sys.exit(0)

    try:
        logger.info(f"Starting SLMS Notification Companion in session {session_id} (PID: {os.getpid()})...")
        companion = NotificationCompanion(session_id=session_id)
        companion.run_forever()
    except Exception as exc:
        logger.exception(f"Fatal error in SLMS Notification Companion: {exc}")
        sys.exit(1)
    finally:
        mutex.release()


if __name__ == "__main__":
    main()
