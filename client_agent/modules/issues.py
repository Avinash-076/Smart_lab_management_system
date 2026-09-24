from __future__ import annotations

from datetime import datetime, timezone


from config import (
    DISK_CRITICAL_THRESHOLD,
    RAM_HIGH_THRESHOLD,
)

# ==========================================
# Active Reported Issues
# ==========================================
#
# Stores issues that have already been reported
# and are still active.
#
# Example:
#
# {
#     "high_ram": True,
#     "low_disk": True,
# }
#
# This prevents the client from creating the
# same issue every monitoring cycle.
#

_ACTIVE_ISSUES: set[str] = set()


def _utc_now() -> str:
    """
    Return the current UTC time as ISO format.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


def _build_issue(
    issue_key: str,
    title: str,
    description: str,
    severity: str,
) -> dict:
    """
    Build an issue payload for the backend.

    The timestamp is included in the description
    so the administrator can see when the problem
    was detected.
    """

    detected_at = _utc_now()

    return {
        "issue_key": issue_key,
        "title": title,
        "description": (
            f"{description}\n\n"
            f"Detected at: {detected_at}"
        ),
        "severity": severity,
    }


def detect_issues(
    data: dict,
) -> list[dict]:
    """
    Detect system problems from collected client data.

    Current rules:

    RAM > 85%
        -> high severity

    Disk > 90%
        -> critical severity

    Only newly detected issues are returned.

    When a problem disappears, its internal state
    is cleared so that a future occurrence can be
    reported again.
    """

    hardware = data.get(
        "hardware"
    ) or {}

    detected_keys: set[str] = set()

    issues: list[dict] = []

    # ------------------------------------------
    # RAM
    # ------------------------------------------

    ram_percent = hardware.get(
        "ram_percent"
    )

    try:
        ram_percent = float(
            ram_percent
        )
    except (
        TypeError,
        ValueError,
    ):
        ram_percent = None

    if (
        ram_percent is not None
        and ram_percent > RAM_HIGH_THRESHOLD
    ):

        issue_key = "high_ram"

        detected_keys.add(
            issue_key
        )

        if issue_key not in _ACTIVE_ISSUES:

            issues.append(
                _build_issue(
                    issue_key=issue_key,
                    title="High Memory Usage",
                    description=(
                        "RAM usage is above the "
                        f"{RAM_HIGH_THRESHOLD}% threshold. "
                        f"Current RAM usage: "
                        f"{ram_percent:.1f}%."
                    ),
                    severity="high",
                )
            )

    # ------------------------------------------
    # Disk
    # ------------------------------------------

    disk_percent = hardware.get(
        "disk_percent"
    )

    try:
        disk_percent = float(
            disk_percent
        )
    except (
        TypeError,
        ValueError,
    ):
        disk_percent = None

    if (
        disk_percent is not None
        and disk_percent > DISK_CRITICAL_THRESHOLD
    ):

        issue_key = "low_disk"

        detected_keys.add(
            issue_key
        )

        if issue_key not in _ACTIVE_ISSUES:

            issues.append(
                _build_issue(
                    issue_key=issue_key,
                    title="Low Disk Space",
                    description=(
                        "System disk usage is above the "
                        f"{DISK_CRITICAL_THRESHOLD}% threshold. "
                        f"Current disk usage: "
                        f"{disk_percent:.1f}%."
                    ),
                    severity="critical",
                )
            )

    # ------------------------------------------
    # Update active issue state
    # ------------------------------------------

    # Add newly detected issues.
    _ACTIVE_ISSUES.update(
        detected_keys
    )

    # Remove issues that are no longer present.
    recovered_keys = (
        _ACTIVE_ISSUES
        - detected_keys
    )

    _ACTIVE_ISSUES.difference_update(
        recovered_keys
    )

    return issues


def get_active_issues() -> set[str]:
    """
    Return a copy of currently active issue keys.
    """

    return set(
        _ACTIVE_ISSUES
    )


def reset_issue_tracking() -> None:
    """
    Clear issue tracking.

    Mainly useful for testing.
    """

    _ACTIVE_ISSUES.clear()