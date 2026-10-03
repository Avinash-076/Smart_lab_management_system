"""
Windows Cross-Process Single-Instance Protection for SLMS Client Agent.

Uses a Windows Named Mutex (Global\\SLMS_Client_Agent_Mutex) to guarantee
that only a single agent instance (Interactive CLI or Windows Service) runs
simultaneously across all Windows sessions (Session 0 and user desktop sessions).

Guarantees:
- Cross-session protection (Global\\ namespace).
- Windows kernel cleans up mutex on abnormal process termination (no stale lock files).
- Clean acquisition, duplicate rejection, and graceful release.
- Fallback/mock support for non-Windows platforms and testing environments.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from core.logger import logger

MUTEX_NAME = r"Global\SLMS_Client_Agent_Mutex"


class SingleInstanceMutex:
    """
    Cross-process single-instance named mutex.
    """

    def __init__(self, name: str = MUTEX_NAME):
        self.name = name
        self._handle: Any | None = None
        self._acquired: bool = False
        self._is_windows = (os.name == "nt")

    @property
    def is_acquired(self) -> bool:
        return self._acquired

    def acquire(self) -> bool:
        """
        Attempt to acquire the named mutex.
        Returns True if acquired successfully (this process is the only instance).
        Returns False if another instance is already holding the mutex.
        """
        if self._acquired:
            return True

        if not self._is_windows:
            self._acquired = True
            return True

        try:
            import ctypes
            from ctypes import wintypes

            ERROR_ALREADY_EXISTS = 183
            ERROR_ACCESS_DENIED = 5

            kernel32 = ctypes.windll.kernel32
            kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            kernel32.GetLastError.restype = wintypes.DWORD

            handle = kernel32.CreateMutexW(None, False, self.name)
            last_error = kernel32.GetLastError()

            if not handle:
                if last_error == ERROR_ACCESS_DENIED:
                    logger.info(
                        f"Access denied to mutex '{self.name}' (error={last_error}); another instance is running."
                    )
                    return False
                logger.warning(f"Failed to create mutex '{self.name}': error code {last_error}")
                return False

            if last_error == ERROR_ALREADY_EXISTS:
                kernel32.CloseHandle(handle)
                logger.info(f"Named mutex '{self.name}' already exists; another instance is running.")
                return False

            self._handle = handle
            self._acquired = True
            logger.debug(f"Acquired single-instance mutex '{self.name}'.")
            return True

        except Exception as e:
            logger.warning(f"Exception during single-instance mutex acquisition: {e}")
            return False

    def release(self) -> None:
        """Release the named mutex handle."""
        if not self._acquired:
            return

        if self._is_windows and self._handle:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self._handle)
            except Exception as e:
                logger.debug(f"Error closing mutex handle: {e}")
            finally:
                self._handle = None

        self._acquired = False
        logger.debug(f"Released single-instance mutex '{self.name}'.")

    def __enter__(self) -> bool:
        return self.acquire()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.release()
