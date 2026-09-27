"""
SLMS Client Agent Application Usage Tracking Module.

Detects active application usage and completed usage sessions.

Phase 4 Hardening:
- D-09: Stable process identity based on (PID, create_time) rather than (PID, name).
  Prevents false session merging on PID reuse.
- D-10: Persistent usage state across agent/service restarts.
  Stores active sessions atomically in DATA_DIR/usage_state.json.
  Surviving processes resume tracking across restart without restarting duration
  or fabricating stop events.
- D-11: Transient drop / false-stop protection.
  Distinguishes confirmed process termination (PID no longer exists) from
  transient enumeration/access failures (grace period applied).
  Reappearing processes recover without false stop/start events.
- D-12: Filter out obvious OS kernel and idle pseudo-processes (PID <= 4,
  System Idle Process, System, Registry, Memory Compression) from usage tracking.
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from datetime import datetime, timezone
from typing import Any

import psutil

from core.logger import logger
from paths import DATA_DIR

# Obvious OS kernel/system pseudo-processes excluded from student application usage (D-12)
_EXCLUDED_PROCESS_NAMES = {
    "system idle process",
    "system",
    "registry",
    "memory compression",
}

# Number of consecutive missed scan cycles allowed before closing a session
# if the PID cannot be confirmed dead immediately (D-11)
MAX_GRACE_CYCLES = 2

# In-memory active usage sessions
# Key: (pid: int, create_time: float)
# Value: dict containing application_name, started_at, last_seen_at, consecutive_misses
_ACTIVE_SESSIONS: dict[tuple[int, float], dict[str, Any]] = {}
_INITIALIZED: bool = False


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_default_state_path() -> str:
    return os.path.join(DATA_DIR, "usage_state.json")


def _is_excluded_process(pid: int, name: str) -> bool:
    """
    Check if a process is an excluded OS pseudo-process (D-12).
    """
    if pid <= 4:
        return True
    if name.casefold() in _EXCLUDED_PROCESS_NAMES:
        return True
    return False


def _safe_create_time(process: psutil.Process, default: float | None = None) -> float | None:
    """
    Safely extract process create_time, returning default if inaccessible.
    """
    try:
        ct = process.create_time()
        if ct is not None and ct > 0:
            return float(ct)
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, OSError):
        pass
    except Exception:
        pass
    return default


def _get_running_applications() -> dict[tuple[int, float], dict[str, Any]]:
    """
    Read currently running processes.
    Identifies processes by stable (pid, create_time) identity (D-09).
    Excludes OS kernel/system pseudo-processes (D-12).
    """
    running: dict[tuple[int, float], dict[str, Any]] = {}
    now = _utc_now()
    now_ts = now.timestamp()

    try:
        proc_iter = psutil.process_iter(["pid", "name", "create_time"])
    except Exception as e:
        logger.warning(f"Failed to enumerate processes for usage tracking: {e}")
        return running

    for process in proc_iter:
        try:
            info = process.info
            pid = info.get("pid")
            name = info.get("name")
            create_time = info.get("create_time")

            if pid is None:
                continue

            pid = int(pid)

            if not name:
                continue

            name = str(name).strip()
            if not name:
                continue

            # Exclude OS kernel pseudo-processes (D-12)
            if _is_excluded_process(pid, name):
                continue

            # Handle process creation time
            if create_time is None or create_time <= 0:
                # Fallback: attempt direct call
                create_time = _safe_create_time(process, default=now_ts)

            create_time = round(float(create_time), 3)

            started_at: datetime | None = None
            try:
                started_at = datetime.fromtimestamp(create_time, tz=timezone.utc)
            except (ValueError, OSError, OverflowError):
                started_at = now

            identity = (pid, create_time)

            running[identity] = {
                "pid": pid,
                "create_time": create_time,
                "application_name": name,
                "started_at": started_at,
                "last_seen_at": now,
            }

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue

    return running


def _build_session(
    application_name: str,
    started_at: datetime,
    ended_at: datetime,
) -> dict[str, Any]:
    """
    Convert an ended process session into the backend usage-session payload format.
    """
    duration_seconds = max(0, int((ended_at - started_at).total_seconds()))

    return {
        "application_name": application_name,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_seconds": duration_seconds,
    }


def save_usage_state(state_file: str | None = None) -> None:
    """
    Persist active usage sessions atomically to disk (D-10).
    """
    path = state_file or _get_default_state_path()
    try:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)

        serialized: dict[str, Any] = {}
        for (pid, ct), sess in _ACTIVE_SESSIONS.items():
            key = f"{pid}_{ct}"
            started_at = sess["started_at"]
            if isinstance(started_at, datetime):
                started_at_str = started_at.isoformat()
            else:
                started_at_str = str(started_at)

            last_seen = sess.get("last_seen_at")
            if isinstance(last_seen, datetime):
                last_seen_str = last_seen.isoformat()
            else:
                last_seen_str = started_at_str

            serialized[key] = {
                "pid": pid,
                "create_time": ct,
                "application_name": sess["application_name"],
                "started_at": started_at_str,
                "last_seen_at": last_seen_str,
                "consecutive_misses": sess.get("consecutive_misses", 0),
            }

        target_dir = os.path.dirname(os.path.abspath(path))
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="utf-8") as tf:
                temp_name = tf.name
                json.dump(serialized, tf, indent=2)
            os.replace(temp_name, path)
            temp_name = None
        finally:
            if temp_name and os.path.exists(temp_name):
                try:
                    os.remove(temp_name)
                except Exception:
                    pass

    except Exception as e:
        logger.warning(f"Failed to persist usage state to {path}: {e}")



def load_usage_state(state_file: str | None = None) -> list[dict[str, Any]]:
    """
    Load persisted usage sessions from disk and reconcile against active OS processes (D-10).
    Returns completed sessions for processes that terminated while the agent was stopped.
    """
    global _ACTIVE_SESSIONS
    path = state_file or _get_default_state_path()

    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to read usage state from {path}: {e}")
        return []

    if not isinstance(data, dict):
        return []

    completed_during_down: list[dict[str, Any]] = []
    now = _utc_now()

    for key, sess_data in data.items():
        try:
            pid = int(sess_data["pid"])
            create_time = float(sess_data["create_time"])
            app_name = str(sess_data["application_name"])
            started_at = datetime.fromisoformat(sess_data["started_at"])
            last_seen_str = sess_data.get("last_seen_at")
            last_seen = datetime.fromisoformat(last_seen_str) if last_seen_str else started_at
            identity = (pid, create_time)

            # Check if this process is STILL running in the OS
            is_alive = False
            if psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    proc_ct = _safe_create_time(proc)
                    if proc_ct is not None and abs(proc_ct - create_time) < 1.0:
                        is_alive = True
                except (psutil.NoSuchProcess, psutil.ZombieProcess):
                    is_alive = False
                except psutil.AccessDenied:
                    # Exists but cannot read create_time; conservatively consider alive
                    is_alive = True

            if is_alive:
                # Process survived agent restart: resume tracking seamlessly (D-10)
                _ACTIVE_SESSIONS[identity] = {
                    "pid": pid,
                    "create_time": create_time,
                    "application_name": app_name,
                    "started_at": started_at,
                    "last_seen_at": now,
                    "consecutive_misses": 0,
                }
            else:
                # Process terminated while agent was stopped: emit completed session
                completed_during_down.append(
                    _build_session(
                        application_name=app_name,
                        started_at=started_at,
                        ended_at=last_seen,
                    )
                )

        except Exception as e:
            logger.debug(f"Skipping corrupted session entry in {path}: {e}")
            continue

    save_usage_state(path)
    return completed_during_down


def collect_usage_sessions(state_file: str | None = None) -> list[dict[str, Any]]:
    """
    Detect completed application usage sessions.

    D-09: Identifies processes by (PID, create_time).
    D-10: State is persisted across restarts.
    D-11: Transient drops are held in grace period; confirmed dead processes are closed.
    D-12: System kernel pseudo-processes are excluded.
    """
    global _ACTIVE_SESSIONS, _INITIALIZED

    # On first run, load persisted state from disk
    completed_sessions: list[dict[str, Any]] = []
    if not _INITIALIZED:
        completed_sessions.extend(load_usage_state(state_file))
        _INITIALIZED = True

    now = _utc_now()
    current_sessions = _get_running_applications()

    # Protection against global enumeration failure:
    # If psutil returns 0 processes when we previously tracked active processes,
    # do NOT falsely terminate all sessions (D-11).
    if not current_sessions and len(_ACTIVE_SESSIONS) > 5:
        logger.warning(
            "Process enumeration returned 0 processes while active sessions exist. "
            "Skipping usage reconciliation to prevent false-stop events."
        )
        return completed_sessions

    # ------------------------------------------
    # 1. Detect newly started processes & update active
    # ------------------------------------------
    for identity, process_data in current_sessions.items():
        if identity not in _ACTIVE_SESSIONS:
            _ACTIVE_SESSIONS[identity] = {
                "pid": process_data["pid"],
                "create_time": process_data["create_time"],
                "application_name": process_data["application_name"],
                "started_at": process_data["started_at"],
                "last_seen_at": now,
                "consecutive_misses": 0,
            }
        else:
            # Process was previously tracked: update last_seen and reset miss counter (D-11 recovery)
            _ACTIVE_SESSIONS[identity]["last_seen_at"] = now
            _ACTIVE_SESSIONS[identity]["consecutive_misses"] = 0

    # ------------------------------------------
    # 2. Reconcile missing processes with false-stop protection (D-11)
    # ------------------------------------------
    previous_identities = list(_ACTIVE_SESSIONS.keys())
    for identity in previous_identities:
        if identity in current_sessions:
            continue

        session = _ACTIVE_SESSIONS[identity]
        pid, create_time = identity

        # Check whether process termination is confirmed by the OS
        confirmed_dead = False
        if not psutil.pid_exists(pid):
            # OS confirms PID does not exist anymore
            confirmed_dead = True
        else:
            # PID still exists; check if it is PID reuse or transient access issue
            try:
                proc = psutil.Process(pid)
                proc_ct = _safe_create_time(proc)
                if proc_ct is not None and abs(proc_ct - create_time) >= 1.0:
                    # PID exists but has a different creation time -> confirmed PID reuse!
                    confirmed_dead = True
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                confirmed_dead = True
            except psutil.AccessDenied:
                # Process is still running but access is temporarily denied
                confirmed_dead = False

        if confirmed_dead:
            # Confirmed process termination: close session immediately
            closed_session = _ACTIVE_SESSIONS.pop(identity, None)
            if closed_session:
                completed_sessions.append(
                    _build_session(
                        application_name=closed_session["application_name"],
                        started_at=closed_session["started_at"],
                        ended_at=now,
                    )
                )
        else:
            # Process not confirmed dead: apply grace cycles for transient drop (D-11)
            session["consecutive_misses"] = session.get("consecutive_misses", 0) + 1
            if session["consecutive_misses"] > MAX_GRACE_CYCLES:
                # Grace period exceeded; close session
                closed_session = _ACTIVE_SESSIONS.pop(identity, None)
                if closed_session:
                    completed_sessions.append(
                        _build_session(
                            application_name=closed_session["application_name"],
                            started_at=closed_session["started_at"],
                            ended_at=now,
                        )
                    )

    # Persist updated state (D-10)
    save_usage_state(state_file)

    return completed_sessions


def get_active_usage_count() -> int:
    """
    Return the number of currently tracked processes.
    """
    return len(_ACTIVE_SESSIONS)


def reset_usage_tracking(state_file: str | None = None) -> None:
    """
    Clear all currently tracked usage sessions and remove persisted state.
    Mainly useful during testing or clean shutdown.
    """
    global _ACTIVE_SESSIONS, _INITIALIZED
    _ACTIVE_SESSIONS.clear()
    _INITIALIZED = False

    path = state_file or _get_default_state_path()
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
