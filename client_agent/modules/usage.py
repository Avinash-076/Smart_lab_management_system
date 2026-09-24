from __future__ import annotations

from datetime import datetime, timezone

import psutil


# Stores currently running applications/processes.
#
# Key:
#     (pid, process_name)
#
# Value:
#     {
#         "application_name": str,
#         "started_at": datetime
#     }
#
# This allows us to detect:
#
# Process appears:
#     START
#
# Process continues:
#     UPDATE duration
#
# Process disappears:
#     END
#
_ACTIVE_SESSIONS: dict[tuple[int, str], dict] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_running_applications() -> dict[tuple[int, str], dict]:
    """
    Read currently running processes.

    Returns a dictionary containing process identity,
    application name and start time.
    """

    running: dict[tuple[int, str], dict] = {}

    for process in psutil.process_iter(
        [
            "pid",
            "name",
            "create_time",
        ]
    ):
        try:
            info = process.info

            pid = info.get("pid")
            name = info.get("name")
            create_time = info.get("create_time")

            if pid is None:
                continue

            if not name:
                continue

            name = str(name).strip()

            if not name:
                continue

            started_at = None

            if create_time:
                try:
                    started_at = datetime.fromtimestamp(
                        create_time,
                        tz=timezone.utc,
                    )
                except (
                    ValueError,
                    OSError,
                    OverflowError,
                ):
                    started_at = None

            if started_at is None:
                started_at = _utc_now()

            identity = (
                int(pid),
                name.casefold(),
            )

            running[identity] = {
                "application_name": name,
                "started_at": started_at,
            }

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
            psutil.ZombieProcess,
        ):
            continue

        except Exception:
            continue

    return running


def _build_session(
    application_name: str,
    started_at: datetime,
    ended_at: datetime,
) -> dict:
    """
    Convert an active process into the backend usage-session format.
    """

    duration_seconds = max(
        0,
        int(
            (
                ended_at - started_at
            ).total_seconds()
        ),
    )

    return {
        "application_name": application_name,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_seconds": duration_seconds,
    }


def collect_usage_sessions() -> list[dict]:
    """
    Detect completed application/process usage sessions.

    A session is returned when a previously running process
    is no longer running.

    The current active processes remain in memory until they
    disappear from the next scan.
    """

    global _ACTIVE_SESSIONS

    now = _utc_now()

    current_sessions = _get_running_applications()

    completed_sessions: list[dict] = []

    # ------------------------------------------
    # Detect newly started processes
    # ------------------------------------------

    for identity, process_data in current_sessions.items():

        if identity not in _ACTIVE_SESSIONS:

            _ACTIVE_SESSIONS[identity] = {
                "application_name": process_data[
                    "application_name"
                ],
                "started_at": process_data[
                    "started_at"
                ],
            }

    # ------------------------------------------
    # Detect processes that have stopped
    # ------------------------------------------

    previous_identities = set(
        _ACTIVE_SESSIONS.keys()
    )

    current_identities = set(
        current_sessions.keys()
    )

    stopped_identities = (
        previous_identities
        - current_identities
    )

    for identity in stopped_identities:

        session = _ACTIVE_SESSIONS.pop(
            identity,
            None,
        )

        if session is None:
            continue

        started_at = session["started_at"]

        application_name = session[
            "application_name"
        ]

        completed_sessions.append(
            _build_session(
                application_name=application_name,
                started_at=started_at,
                ended_at=now,
            )
        )

    return completed_sessions


def get_active_usage_count() -> int:
    """
    Return the number of currently tracked processes.
    """

    return len(_ACTIVE_SESSIONS)


def reset_usage_tracking() -> None:
    """
    Clear all currently tracked usage sessions.

    Mainly useful during testing or controlled shutdown.
    """

    global _ACTIVE_SESSIONS

    _ACTIVE_SESSIONS.clear()