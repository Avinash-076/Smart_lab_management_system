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
ERROR_FILE_NOT_FOUND = 2
ERROR_ACCESS_DENIED = 5
ERROR_ALREADY_EXISTS = 183
SYNCHRONIZE = 0x00100000


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
            ERROR_FILE_NOT_FOUND = 2
            SYNCHRONIZE = 0x00100000

            kernel32 = ctypes.windll.kernel32
            advapi32 = ctypes.windll.advapi32

            class SECURITY_ATTRIBUTES(ctypes.Structure):
                _fields_ = [
                    ("nLength", wintypes.DWORD),
                    ("lpSecurityDescriptor", wintypes.LPVOID),
                    ("bInheritHandle", wintypes.BOOL),
                ]

            kernel32.CreateMutexW.argtypes = [ctypes.POINTER(SECURITY_ATTRIBUTES), wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.CreateMutexW.restype = wintypes.HANDLE
            kernel32.OpenMutexW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
            kernel32.OpenMutexW.restype = wintypes.HANDLE
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            kernel32.GetLastError.restype = wintypes.DWORD

            # Build permissive security descriptor allowing cross-session access (Everyone / World)
            sa = None
            pSD = wintypes.LPVOID()
            sddl = "D:(A;;GA;;;WD)"  # Allow Generic All to World
            if hasattr(advapi32, "ConvertStringSecurityDescriptorToSecurityDescriptorW"):
                advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
                    wintypes.LPCWSTR,
                    wintypes.DWORD,
                    ctypes.POINTER(wintypes.LPVOID),
                    ctypes.POINTER(wintypes.ULONG),
                ]
                advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
                if advapi32.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, ctypes.byref(pSD), None):
                    sa = SECURITY_ATTRIBUTES()
                    sa.nLength = ctypes.sizeof(SECURITY_ATTRIBUTES)
                    sa.lpSecurityDescriptor = pSD.value
                    sa.bInheritHandle = False

            sa_ptr = ctypes.byref(sa) if sa is not None else None
            try:
                handle = kernel32.CreateMutexW(sa_ptr, False, self.name)
                last_error = kernel32.GetLastError()
            finally:
                if pSD and pSD.value:
                    kernel32.LocalFree(pSD)

            if handle and last_error != ERROR_ALREADY_EXISTS:
                self._handle = handle
                self._acquired = True
                logger.debug(f"Acquired single-instance mutex '{self.name}'.")
                return True

            if handle and last_error == ERROR_ALREADY_EXISTS:
                kernel32.CloseHandle(handle)
                logger.info(f"Named mutex '{self.name}' already exists; another instance is running.")
                return False

            if not handle:
                if last_error == ERROR_ACCESS_DENIED:
                    # Check if mutex actually exists in kernel
                    test_open = kernel32.OpenMutexW(SYNCHRONIZE, False, self.name)
                    open_err = kernel32.GetLastError()
                    if test_open:
                        kernel32.CloseHandle(test_open)
                        logger.info(
                            f"Mutex '{self.name}' exists and is held by another instance across sessions."
                        )
                        return False
                    elif open_err == ERROR_ACCESS_DENIED:
                        logger.info(
                            f"Access denied opening existing mutex '{self.name}'; another instance is running."
                        )
                        return False
                    elif open_err == ERROR_FILE_NOT_FOUND:
                        # Mutex does NOT exist: failure was solely Global\ namespace creation permission
                        logger.warning(
                            f"Cannot create Global mutex '{self.name}' due to namespace permissions. "
                            "Falling back to session-local single-instance mutex."
                        )
                        fallback_name = self.name.replace(r"Global\\", r"Local\\")
                        fb_handle = kernel32.CreateMutexW(None, False, fallback_name)
                        fb_err = kernel32.GetLastError()
                        if fb_handle and fb_err != ERROR_ALREADY_EXISTS:
                            self._handle = fb_handle
                            self._acquired = True
                            logger.info(f"Acquired session-local fallback single-instance mutex '{fallback_name}'.")
                            return True
                        if fb_handle:
                            kernel32.CloseHandle(fb_handle)
                        logger.info(f"Fallback mutex '{fallback_name}' already exists; another instance is running.")
                        return False

                logger.warning(f"Failed to create mutex '{self.name}': error code {last_error}")
                return False

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
