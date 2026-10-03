"""
SLMS Client Agent Scheduler Module.

H-04 Drift-Free Interval Scheduling:
Replaces naive sequential `work -> sleep(interval)` with monotonic target-based
scheduling (`next_target = previous_target + interval`).
Prevents execution time of collectors/uploads from causing cumulative clock drift.
Provides interruptible waits, task overrun catch-up handling, and clean shutdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import threading
import time
from typing import Any, Callable

from core.logger import logger


@dataclass
class ScheduledJob:
    """Represents an independently scheduled recurring task."""
    name: str
    interval: float
    callback: Callable[[], Any]
    initial_delay: float = 0.0
    next_run: float = field(init=False)
    last_run: float | None = field(default=None, init=False)
    run_count: int = field(default=0, init=False)
    is_active: bool = field(default=True, init=False)

    def __post_init__(self) -> None:
        self.next_run = time.monotonic() + self.initial_delay


class Scheduler:
    """
    Fixed-cadence, drift-free execution engine for recurring runtime tasks.
    Coordinates job executions using monotonic clock intervals and interruptible
    event waits.
    """

    def __init__(self, stop_event: threading.Event | None = None):
        self.stop_event = stop_event or threading.Event()
        self._jobs: dict[str, ScheduledJob] = {}
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    def add_job(
        self,
        name: str,
        interval: float,
        callback: Callable[[], Any],
        initial_delay: float = 0.0,
    ) -> ScheduledJob:
        """
        Register a recurring job with a fixed interval in seconds.
        """
        if interval <= 0:
            raise ValueError(f"Interval for job '{name}' must be positive, got {interval}")

        with self._lock:
            job = ScheduledJob(
                name=name,
                interval=interval,
                callback=callback,
                initial_delay=initial_delay,
            )
            self._jobs[name] = job
            logger.debug(f"Scheduler registered job '{name}' (interval={interval}s, initial_delay={initial_delay}s)")
            return job

    def remove_job(self, name: str) -> bool:
        """Remove a registered job by name."""
        with self._lock:
            if name in self._jobs:
                del self._jobs[name]
                return True
            return False

    def get_job(self, name: str) -> ScheduledJob | None:
        """Retrieve job descriptor by name."""
        with self._lock:
            return self._jobs.get(name)

    def run_pending(self, now: float | None = None) -> list[str]:
        """
        Execute all jobs that are due at the given timestamp.
        Useful for deterministic testing or single-step execution.
        Returns the list of job names executed.
        """
        if now is None:
            now = time.monotonic()

        executed: list[str] = []
        with self._lock:
            for job in list(self._jobs.values()):
                if not job.is_active:
                    continue
                if now >= job.next_run:
                    executed.append(job.name)
                    try:
                        job.callback()
                    except Exception as exc:
                        logger.exception(f"Unhandled error in scheduled job '{job.name}': {exc}")
                    finally:
                        job.run_count += 1
                        job.last_run = now

                        # Compute next target without drift (H-04)
                        target = job.next_run + job.interval
                        # Overrun catch-up handling: if execution took longer than interval,
                        # jump to next future cycle instead of queuing burst backlog
                        if now >= target:
                            logger.warning(
                                f"Scheduled job '{job.name}' overran cadence "
                                f"(now={now:.2f}, target={target:.2f}). Rescheduling next run."
                            )
                            job.next_run = now + job.interval
                        else:
                            job.next_run = target

        return executed

    def next_wait_time(self, now: float | None = None) -> float:
        """Calculate seconds until the next due job (or fallback default if no jobs)."""
        if now is None:
            now = time.monotonic()

        with self._lock:
            active_jobs = [j for j in self._jobs.values() if j.is_active]
            if not active_jobs:
                return 1.0
            min_next = min(j.next_run for j in active_jobs)
            return max(0.0, min_next - now)

    def start(self) -> None:
        """Start the scheduler background worker loop."""
        with self._lock:
            if self._is_running:
                logger.warning("Scheduler is already running.")
                return
            self._is_running = True

            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="SLMS-Scheduler",
            )
            self._thread.start()
            logger.info("Scheduler started.")

    def stop(self, timeout: float = 5.0) -> None:
        """Signal scheduler to stop and wait for worker thread to exit."""
        with self._lock:
            if not self._is_running:
                return
            self._is_running = False

        self.stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        logger.info("Scheduler stopped cleanly.")

    def _run_loop(self) -> None:
        """Main scheduler execution loop."""
        while not self.stop_event.is_set():
            now = time.monotonic()
            self.run_pending(now=now)

            if self.stop_event.is_set():
                break

            wait_duration = self.next_wait_time(now=time.monotonic())
            # Cap sleep to 1.0s to remain responsive to stop signals and clock changes
            step_wait = min(wait_duration, 1.0)
            if self.stop_event.wait(timeout=step_wait):
                break

        with self._lock:
            self._is_running = False
