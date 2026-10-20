"""
Tests for Windows Cross-Process Single-Instance Protection (Phase E).

Verifies:
1. First instance acquires named mutex successfully.
2. Second instance attempting to acquire the same mutex is rejected.
3. Mutex is cleanly released on exit / cleanup.
4. After release, another instance can acquire the mutex.
5. RuntimeManager and AgentRuntime terminate cleanly (without crashing) when duplicate instance detected.
6. Context manager (__enter__ / __exit__) semantics.
7. Service and interactive collision behavior.
"""

from __future__ import annotations

import os
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from core.runtime import AgentRuntime, RuntimeManager
from core.single_instance import SingleInstanceMutex, MUTEX_NAME


class TestSingleInstanceMutex:

    @pytest.mark.windows_only
    def test_single_instance_acquisition_and_release(self):
        """Verify initial acquisition succeeds and explicit release frees the mutex."""
        test_mutex_name = f"Local\\SLMS_Test_Mutex_{os.getpid()}_1"
        mutex1 = SingleInstanceMutex(name=test_mutex_name)

        # 1. First instance acquires
        assert mutex1.acquire() is True
        assert mutex1.is_acquired is True

        # Re-acquiring by same object returns True
        assert mutex1.acquire() is True

        # 2. Second instance cannot acquire while first is active
        mutex2 = SingleInstanceMutex(name=test_mutex_name)
        assert mutex2.acquire() is False
        assert mutex2.is_acquired is False

        # 3. First instance releases
        mutex1.release()
        assert mutex1.is_acquired is False

        # 4. Second instance can now acquire
        assert mutex2.acquire() is True
        assert mutex2.is_acquired is True
        mutex2.release()
        assert mutex2.is_acquired is False

    @pytest.mark.windows_only
    def test_single_instance_context_manager(self):
        """Verify context manager acquires on enter and releases on exit."""
        test_mutex_name = f"Local\\SLMS_Test_Mutex_{os.getpid()}_2"
        mutex1 = SingleInstanceMutex(name=test_mutex_name)

        with mutex1 as acquired:
            assert acquired is True
            assert mutex1.is_acquired is True

            # Inside context, second instance cannot acquire
            mutex2 = SingleInstanceMutex(name=test_mutex_name)
            assert mutex2.acquire() is False

        # After exiting context, mutex1 is released
        assert mutex1.is_acquired is False

        # mutex2 can now acquire
        with mutex2 as acquired2:
            assert acquired2 is True
            assert mutex2.is_acquired is True

    def test_runtime_manager_terminates_cleanly_on_duplicate_instance(self):
        """
        Verify RuntimeManager.start() exits cleanly (without unhandled exceptions)
        when another instance is already holding the single-instance mutex.
        """
        mock_mutex = MagicMock(spec=SingleInstanceMutex)
        mock_mutex.acquire.return_value = False  # Simulate duplicate instance
        mock_mutex.is_acquired = False

        stop_event = threading.Event()
        runtime = RuntimeManager(
            stop_event=stop_event,
            is_service=False,
            single_instance=mock_mutex,
            enable_single_instance=True,
        )

        # start() should return cleanly without raising
        runtime.start()

        assert runtime.is_running is False
        assert runtime.started_count == 0
        mock_mutex.acquire.assert_called_once()

    def test_service_mode_clean_exit_on_duplicate_instance(self):
        """
        Verify that in Windows Service mode (is_service=True), duplicate detection
        exits cleanly without crashing the service host.
        """
        mock_mutex = MagicMock(spec=SingleInstanceMutex)
        mock_mutex.acquire.return_value = False
        mock_mutex.is_acquired = False

        stop_event = threading.Event()
        runtime = AgentRuntime(
            stop_event=stop_event,
            is_service=True,
            single_instance=mock_mutex,
            enable_single_instance=True,
        )

        runtime.start()

        assert runtime.is_running is False
        assert runtime.started_count == 0
        mock_mutex.acquire.assert_called_once()

    def test_agent_runtime_releases_mutex_on_stop(self):
        """Verify AgentRuntime releases single-instance mutex when stopped."""
        mock_mutex = MagicMock(spec=SingleInstanceMutex)
        mock_mutex.acquire.return_value = True
        mock_mutex.is_acquired = True

        stop_event = threading.Event()
        runtime = AgentRuntime(
            stop_event=stop_event,
            is_service=False,
            single_instance=mock_mutex,
            enable_single_instance=True,
        )

        # Trigger cleanup
        runtime._cleanup()

        mock_mutex.release.assert_called_once()

    def test_non_windows_platform_fallback(self):
        """Verify single instance behavior on non-Windows platforms."""
        mutex = SingleInstanceMutex(name="TestNonWindows")
        mutex._is_windows = False

        assert mutex.acquire() is True
        assert mutex.is_acquired is True
        mutex.release()
        assert mutex.is_acquired is False

    @pytest.mark.windows_only
    def test_access_denied_with_nonexistent_mutex_falls_back_to_local(self):
        """
        Verify that if Global\\ mutex creation fails with ERROR_ACCESS_DENIED
        and the mutex does not exist (ERROR_FILE_NOT_FOUND), the implementation
        gracefully falls back to a session-local mutex and succeeds.
        """
        import ctypes
        from core.single_instance import ERROR_ACCESS_DENIED, ERROR_FILE_NOT_FOUND

        mutex = SingleInstanceMutex(name=r"Global\SLMS_Test_AccessDenied_Fallback")

        call_count = {"create": 0}
        dummy_handle = ctypes.c_void_p(12345)

        def mock_create_mutex(sa, initial_owner, name):
            call_count["create"] += 1
            if call_count["create"] == 1:
                # First call is for Global\: simulate access denied
                return None
            else:
                # Second call is for Local\ fallback: simulate success
                return dummy_handle

        def mock_get_last_error():
            if call_count["create"] == 1:
                return ERROR_ACCESS_DENIED
            return 0

        def mock_open_mutex(access, inherit, name):
            # Mutex does not exist in kernel
            return None

        with patch("ctypes.windll.kernel32.CreateMutexW", side_effect=mock_create_mutex), \
             patch("ctypes.windll.kernel32.GetLastError", side_effect=mock_get_last_error), \
             patch("ctypes.windll.kernel32.OpenMutexW", side_effect=mock_open_mutex), \
             patch("ctypes.windll.kernel32.CloseHandle", return_value=True):

            # In mock_open_mutex, GetLastError needs to return ERROR_FILE_NOT_FOUND
            def mock_get_last_error_with_open():
                if call_count["create"] == 1:
                    # After OpenMutexW fails
                    return ERROR_FILE_NOT_FOUND
                return 0

            with patch("ctypes.windll.kernel32.GetLastError", side_effect=[ERROR_ACCESS_DENIED, ERROR_FILE_NOT_FOUND, 0]):
                acquired = mutex.acquire()
                assert acquired is True
                assert mutex.is_acquired is True
                assert mutex._handle == dummy_handle

    @pytest.mark.windows_only
    def test_access_denied_with_existing_mutex_rejects(self):
        """
        Verify that if Global\\ mutex creation fails with ERROR_ACCESS_DENIED
        and OpenMutexW succeeds (the mutex is indeed held by another instance),
        acquire() returns False without creating a duplicate.
        """
        import ctypes
        from core.single_instance import ERROR_ACCESS_DENIED

        mutex = SingleInstanceMutex(name=r"Global\SLMS_Test_AccessDenied_Held")
        dummy_open_handle = ctypes.c_void_p(99999)

        with patch("ctypes.windll.kernel32.CreateMutexW", return_value=None), \
             patch("ctypes.windll.kernel32.GetLastError", return_value=ERROR_ACCESS_DENIED), \
             patch("ctypes.windll.kernel32.OpenMutexW", return_value=dummy_open_handle), \
             patch("ctypes.windll.kernel32.CloseHandle", return_value=True) as mock_close:

            acquired = mutex.acquire()
            assert acquired is False
            assert mutex.is_acquired is False
            mock_close.assert_called_once_with(dummy_open_handle)

