"""
Service lifecycle state management for SLMS Windows Service.

Coordinates clean state transitions:
STOPPED -> STARTING -> RUNNING -> STOPPING -> STOPPED (or FAILED).
Ensures prompt shutdown and resource cleanup upon Windows SCM stop/shutdown signals.
"""

from __future__ import annotations

from enum import Enum
import threading
from typing import Callable, Optional

from core.logger import logger
from core.runtime import AgentRuntime


class ServiceState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    FAILED = "FAILED"


class ServiceLifecycle:
    """
    Manages the runtime state and execution thread of the SLMS service.
    Provides thread-safe state inspection and controlled shutdown.
    """

    def __init__(
        self,
        runtime_factory: Optional[Callable[[threading.Event], AgentRuntime]] = None,
    ):
        self._state = ServiceState.STOPPED
        self._lock = threading.Lock()
        self.stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        self._last_error: Optional[Exception] = None

        self._worker_finished_event = threading.Event()

        if runtime_factory is not None:
            self._runtime = runtime_factory(self.stop_event)
        else:
            self._runtime = AgentRuntime(stop_event=self.stop_event, is_service=True)

    @property
    def state(self) -> ServiceState:
        with self._lock:
            return self._state

    @property
    def runtime(self) -> AgentRuntime:
        return self._runtime

    @property
    def last_error(self) -> Optional[Exception]:
        return self._last_error

    @property
    def worker_finished_event(self) -> threading.Event:
        return self._worker_finished_event

    def is_healthy(self) -> bool:
        """Return True if service is currently RUNNING and worker thread is alive."""
        with self._lock:
            if self._state != ServiceState.RUNNING:
                return False
            return self._worker_thread is not None and self._worker_thread.is_alive()

    def start(self) -> None:
        """
        Start the service runtime in a dedicated worker thread.
        Transitions state to STARTING, then RUNNING.
        """
        with self._lock:
            if self._state in (ServiceState.STARTING, ServiceState.RUNNING):
                logger.warning(f"Service start requested but state is already {self._state.value}.")
                return

            self._state = ServiceState.STARTING
            self.stop_event.clear()
            self._worker_finished_event.clear()
            self._last_error = None

        logger.info("Service lifecycle: STARTING -> Spawning worker thread...")

        def _thread_target():
            try:
                with self._lock:
                    self._state = ServiceState.RUNNING
                logger.info("Service lifecycle: RUNNING.")
                self._runtime.start()
            except Exception as e:
                with self._lock:
                    self._state = ServiceState.FAILED
                    self._last_error = e
                logger.exception(f"Service lifecycle worker thread failed: {e}")
            finally:
                with self._lock:
                    if self._state not in (ServiceState.FAILED, ServiceState.STOPPED):
                        self._state = ServiceState.STOPPED
                self._worker_finished_event.set()
                logger.info("Service lifecycle: worker thread finished.")

        self._worker_thread = threading.Thread(
            target=_thread_target,
            name="SLMS-Service-Worker",
            daemon=True,
        )
        self._worker_thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        """
        Signal runtime to stop and wait for worker thread to exit.
        Transitions state to STOPPING, then STOPPED.
        """
        with self._lock:
            if self._state in (ServiceState.STOPPING, ServiceState.STOPPED):
                logger.info(f"Service stop requested but state is already {self._state.value}.")
                return
            self._state = ServiceState.STOPPING

        logger.info("Service lifecycle: STOPPING -> Signaling stop event...")
        self.stop_event.set()
        self._runtime.stop()

        if self._worker_thread is not None and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)
            if self._worker_thread.is_alive():
                logger.warning(f"Service worker thread did not terminate within {timeout}s.")

        with self._lock:
            if self._state != ServiceState.FAILED:
                self._state = ServiceState.STOPPED

        self._worker_finished_event.set()
        logger.info("Service lifecycle: STOPPED.")
