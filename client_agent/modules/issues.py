# ==========================================
# Smart Lab Management System
# Client Agent - Issue Detection & Lifecycle Management (Phase 6)
# ==========================================

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
import logging
import os
import tempfile
import time
from typing import Any, Callable
import uuid

import config
from paths import ISSUE_STATE_FILE

logger = logging.getLogger("slms_issues")


# ==========================================
# Issue Architecture & Authority (F-03)
# ==========================================
#
# Client Issue Authority:
# - The client agent evaluates endpoint-level hardware and system health.
# - It is authoritative for detecting local operational degradation and
#   submitting formal, persistent Issue tickets (POST /api/issues/agent).
#
# Backend Alert Authority:
# - The backend (app/services/alert_service.py) continuously inspects incoming
#   metric telemetry streams across the fleet to generate real-time Notification
#   alerts for dashboard operators.
#
# Distinction & Non-Interference:
# - Client Issues represent formal incident tickets that require administrative
#   remediation, tracking, and resolution.
# - Backend Notifications represent transient telemetry alert events.
# - Neither replaces or overrides the other; they are separate, complementary
#   mechanisms across the client-server boundary.
# ==========================================


class IssueLifecycleState(str, Enum):
    """
    Formal lifecycle states for client-side issue incidents.

    Lifecycle:
    NO_ACTIVE_INCIDENT -> DETECTED (confirming) -> QUEUED (emitted/enqueued)
                       -> SENT (dispatched) -> ACKNOWLEDGED (delivered)
                       -> RECOVERED (hysteresis cleared) -> NO_ACTIVE_INCIDENT
    """
    NO_ACTIVE_INCIDENT = "NO_ACTIVE_INCIDENT"
    DETECTED = "DETECTED"           # Threshold breached; awaiting debounce confirmation
    QUEUED = "QUEUED"               # Debounce confirmed; emitted for outbox delivery
    SENT = "SENT"                   # Outbox worker has dispatched to backend
    ACKNOWLEDGED = "ACKNOWLEDGED"   # Backend acknowledged receipt (delivery confirmed)
    RECOVERED = "RECOVERED"         # Metric returned below recovery threshold


# Backward-compatible in-memory cache synchronized with persistent state
_ACTIVE_ISSUES: set[str] = set()


def _utc_now() -> str:
    """Return current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


# ==========================================
# Issue Rule Definition & Catalog (F-03)
# ==========================================

@dataclass
class IssueRuleDefinition:
    """
    Centralized, declarative definition of an endpoint issue rule.
    """
    issue_key: str
    title: str
    severity: str
    trigger_threshold: float
    recovery_threshold: float
    description_template: str
    metric_extractor: Callable[[dict], float | None]

    def is_triggered(self, value: float | None) -> bool:
        """Return True if metric value breaches the trigger threshold."""
        if value is None:
            return False
        return value > self.trigger_threshold

    def is_recovered(self, value: float | None) -> bool:
        """Return True if metric value has returned to or below recovery threshold (hysteresis)."""
        if value is None:
            return False
        return value <= self.recovery_threshold

    def format_description(self, value: float) -> str:
        """Format the rule description with current value and trigger threshold."""
        return self.description_template.format(
            trigger_threshold=self.trigger_threshold,
            recovery_threshold=self.recovery_threshold,
            current_value=value,
        )


def _extract_ram_percent(data: dict) -> float | None:
    """Extract RAM usage percent safely from collected data."""
    hardware = data.get("hardware")
    if hasattr(hardware, "is_failed") and hardware.is_failed:
        return None
    hw_dict = hardware.data if hasattr(hardware, "data") else hardware
    if not isinstance(hw_dict, dict):
        return None
    val = hw_dict.get("ram_percent")
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _extract_disk_percent(data: dict) -> float | None:
    """Extract Disk usage percent safely from collected data."""
    hardware = data.get("hardware")
    if hasattr(hardware, "is_failed") and hardware.is_failed:
        return None
    hw_dict = hardware.data if hasattr(hardware, "data") else hardware
    if not isinstance(hw_dict, dict):
        return None
    val = hw_dict.get("disk_percent")
    try:
        return float(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def get_issue_rules() -> list[IssueRuleDefinition]:
    """
    Retrieve the centralized catalog of active issue rules with
    configurable thresholds derived from client_agent/config.py.
    """
    ram_trigger = float(getattr(config, "RAM_HIGH_THRESHOLD", 85.0))
    ram_recovery = float(getattr(config, "RAM_RECOVERY_THRESHOLD", 80.0))
    disk_trigger = float(getattr(config, "DISK_CRITICAL_THRESHOLD", 90.0))
    disk_recovery = float(getattr(config, "DISK_RECOVERY_THRESHOLD", 85.0))

    return [
        IssueRuleDefinition(
            issue_key="high_ram",
            title="High Memory Usage",
            severity="high",
            trigger_threshold=ram_trigger,
            recovery_threshold=ram_recovery,
            description_template=(
                "RAM usage is above the {trigger_threshold}% threshold. "
                "Current RAM usage: {current_value:.1f}%."
            ),
            metric_extractor=_extract_ram_percent,
        ),
        IssueRuleDefinition(
            issue_key="low_disk",
            title="Low Disk Space",
            severity="critical",
            trigger_threshold=disk_trigger,
            recovery_threshold=disk_recovery,
            description_template=(
                "System disk usage is above the {trigger_threshold}% threshold. "
                "Current disk usage: {current_value:.1f}%."
            ),
            metric_extractor=_extract_disk_percent,
        ),
    ]


# ==========================================
# Persistent State Storage (F-01)
# ==========================================

def _get_default_state() -> dict:
    return {
        "version": 1,
        "active_incidents": {},
        "recent_recoveries": {},
    }


def load_issue_state(state_file: str | None = None) -> dict:
    """
    Load persistent issue incident state from JSON file.
    Returns safe default empty structure if file is missing or corrupted.
    """
    target = state_file or ISSUE_STATE_FILE
    if not os.path.exists(target):
        return _get_default_state()

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                logger.warning(f"Corrupted issue state in {target} (not a dict). Resetting.")
                return _get_default_state()
            data.setdefault("version", 1)
            data.setdefault("active_incidents", {})
            data.setdefault("recent_recoveries", {})
            return data
    except Exception as e:
        logger.warning(f"Failed to load issue state from {target}: {e}. Returning clean state.")
        return _get_default_state()


def save_issue_state(state: dict, state_file: str | None = None) -> None:
    """
    Persist issue incident state using atomic replacement (temp file -> replace).
    Ensures state corruption cannot occur if the process is terminated mid-write.
    """
    target = state_file or ISSUE_STATE_FILE
    target_dir = os.path.dirname(target)
    if target_dir:
        os.makedirs(target_dir, exist_ok=True)

    state["updated_at"] = _utc_now()

    # Synchronize backward-compatible _ACTIVE_ISSUES in-memory set
    global _ACTIVE_ISSUES
    active_keys = {
        k for k, inc in state.get("active_incidents", {}).items()
        if inc.get("state") in (
            IssueLifecycleState.DETECTED.value,
            IssueLifecycleState.QUEUED.value,
            IssueLifecycleState.SENT.value,
            IssueLifecycleState.ACKNOWLEDGED.value,
        )
    }
    _ACTIVE_ISSUES = active_keys

    temp_path = None
    try:
        fd, temp_path = tempfile.mkstemp(
            prefix="issue_state_",
            suffix=".tmp",
            dir=target_dir or ".",
        )
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        os.replace(temp_path, target)
    except Exception as e:
        logger.error(f"Failed to atomically persist issue state to {target}: {e}")
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


# ==========================================
# Payload Construction
# ==========================================

def _build_issue(
    issue_key: str,
    incident_id: str,
    title: str,
    description: str,
    severity: str,
) -> dict:
    """
    Build an issue payload for local outbox delivery and backend ingestion.
    """
    detected_at = _utc_now()
    return {
        "issue_key": issue_key,
        "incident_id": incident_id,
        "title": title,
        "description": (
            f"{description}\n\n"
            f"Detected at: {detected_at}"
        ),
        "severity": severity,
    }


# ==========================================
# Detection, Debounce & Hysteresis (F-01, F-04)
# ==========================================

def detect_issues(
    data: dict,
    state_file: str | None = None,
) -> list[dict]:
    """
    Detect system problems from collected client data using centralized rules,
    consecutive-cycle debounce, hysteresis recovery, and persistent state.

    Lifecycle:
    1. Single breach creates DETECTED incident with count=1.
    2. Debounce requires consecutive breaches >= ISSUE_DEBOUNCE_CYCLES.
    3. Once debounce is met, transitions to QUEUED and emits payload.
    4. While active, subsequent cycles do not re-emit duplicate records.
    5. Hysteresis prevents clearing until metric drops <= recovery threshold.
    6. Upon recovery, transitions to RECOVERED and resets state.
    """
    rules = get_issue_rules()
    state = load_issue_state(state_file)
    active_incidents: dict = state.get("active_incidents", {})
    recent_recoveries: dict = state.get("recent_recoveries", {})

    debounce_cycles = max(1, int(getattr(config, "ISSUE_DEBOUNCE_CYCLES", 2)))
    cooldown_seconds = max(0, int(getattr(config, "ISSUE_COOLDOWN_SECONDS", 0)))
    now_ts = time.time()
    now_utc = _utc_now()

    emitted_issues: list[dict] = []
    state_modified = False

    for rule in rules:
        val = rule.metric_extractor(data)
        if val is None:
            # Missing or corrupted metric does not trigger or recover issues
            continue

        key = rule.issue_key
        incident = active_incidents.get(key)

        # ----------------------------------------------------
        # Scenario 1: No active incident currently tracked
        # ----------------------------------------------------
        if incident is None:
            if rule.is_triggered(val):
                # Check cooldown if configured
                rec = recent_recoveries.get(key)
                if rec and cooldown_seconds > 0:
                    rec_ts = rec.get("recovered_at_ts", 0)
                    if (now_ts - rec_ts) < cooldown_seconds:
                        logger.debug(
                            f"Issue {key} breached threshold but ignored due to active cooldown "
                            f"({now_ts - rec_ts:.1f}s / {cooldown_seconds}s)."
                        )
                        continue

                incident_id = uuid.uuid4().hex[:12]
                if debounce_cycles == 1:
                    # Debounce satisfied immediately
                    payload = _build_issue(
                        issue_key=key,
                        incident_id=incident_id,
                        title=rule.title,
                        description=rule.format_description(val),
                        severity=rule.severity,
                    )
                    active_incidents[key] = {
                        "issue_key": key,
                        "incident_id": incident_id,
                        "state": IssueLifecycleState.QUEUED.value,
                        "consecutive_count": 1,
                        "first_detected_at": now_utc,
                        "last_confirmed_at": now_utc,
                        "cleared_at": None,
                        "payload": payload,
                        "enqueued": False,
                        "emitted": True,
                    }
                    emitted_issues.append(payload)
                    state_modified = True
                    logger.warning(
                        f"Issue {key} triggered and confirmed immediately (incident_id={incident_id})."
                    )
                else:
                    # Cycle 1 of debounce confirmation
                    active_incidents[key] = {
                        "issue_key": key,
                        "incident_id": incident_id,
                        "state": IssueLifecycleState.DETECTED.value,
                        "consecutive_count": 1,
                        "first_detected_at": now_utc,
                        "last_confirmed_at": now_utc,
                        "cleared_at": None,
                        "payload": None,
                        "enqueued": False,
                        "emitted": False,
                    }
                    state_modified = True
                    logger.info(
                        f"Issue {key} breached trigger threshold (sample 1/{debounce_cycles}). "
                        f"Awaiting debounce confirmation."
                    )
            continue

        # ----------------------------------------------------
        # Scenario 2: Incident is in DETECTED (confirming debounce)
        # ----------------------------------------------------
        if incident.get("state") == IssueLifecycleState.DETECTED.value:
            if rule.is_triggered(val):
                count = incident.get("consecutive_count", 1) + 1
                incident["consecutive_count"] = count
                incident["last_confirmed_at"] = now_utc
                state_modified = True

                if count >= debounce_cycles:
                    # Debounce threshold satisfied!
                    incident_id = incident["incident_id"]
                    payload = _build_issue(
                        issue_key=key,
                        incident_id=incident_id,
                        title=rule.title,
                        description=rule.format_description(val),
                        severity=rule.severity,
                    )
                    incident["state"] = IssueLifecycleState.QUEUED.value
                    incident["payload"] = payload
                    incident["emitted"] = True
                    emitted_issues.append(payload)
                    logger.warning(
                        f"Issue {key} debounce confirmed ({count}/{debounce_cycles} cycles). "
                        f"Transitioning to QUEUED (incident_id={incident_id})."
                    )
                else:
                    logger.info(
                        f"Issue {key} breached trigger threshold (sample {count}/{debounce_cycles})."
                    )
            else:
                # Transient spike subsided before debounce reached; cancel detection
                logger.info(
                    f"Issue {key} transient threshold breach subsided before debounce confirmation. "
                    "Resetting detection state."
                )
                active_incidents.pop(key, None)
                state_modified = True
            continue

        # ----------------------------------------------------
        # Scenario 3: Incident is ACTIVE (QUEUED, SENT, or ACKNOWLEDGED)
        # ----------------------------------------------------
        curr_state = incident.get("state")
        if curr_state in (
            IssueLifecycleState.QUEUED.value,
            IssueLifecycleState.SENT.value,
            IssueLifecycleState.ACKNOWLEDGED.value,
        ):
            if rule.is_recovered(val):
                # Recovery threshold satisfied (Hysteresis clear)
                incident_id = incident.get("incident_id", "unknown")
                incident["state"] = IssueLifecycleState.RECOVERED.value
                incident["cleared_at"] = now_utc
                recent_recoveries[key] = {
                    "incident_id": incident_id,
                    "recovered_at": now_utc,
                    "recovered_at_ts": now_ts,
                }
                active_incidents.pop(key, None)
                state_modified = True
                logger.info(
                    f"Issue {key} recovered (metric={val:.1f} <= recovery={rule.recovery_threshold:.1f}). "
                    f"Incident {incident_id} marked RECOVERED."
                )
            else:
                # Still active; update tracking
                incident["consecutive_count"] = incident.get("consecutive_count", 1) + 1
                incident["last_confirmed_at"] = now_utc
                state_modified = True

                # Only re-emit if state is QUEUED and not yet marked emitted
                if curr_state == IssueLifecycleState.QUEUED.value and not incident.get("emitted"):
                    payload = incident.get("payload")
                    if payload and payload not in emitted_issues:
                        emitted_issues.append(payload)
                        incident["emitted"] = True

    if state_modified:
        state["active_incidents"] = active_incidents
        state["recent_recoveries"] = recent_recoveries
        save_issue_state(state, state_file)

    return emitted_issues


# ==========================================
# Delivery State Transition Helpers (F-01, F-02)
# ==========================================

def record_issue_enqueued(
    issue_key: str,
    incident_id: str,
    state_file: str | None = None,
) -> None:
    """
    Record that an issue incident has been successfully enqueued to the outbox.
    Prevents repeated re-emission while outbox delivery is pending or processing.
    """
    state = load_issue_state(state_file)
    incident = state.get("active_incidents", {}).get(issue_key)
    if incident and incident.get("incident_id") == incident_id:
        incident["enqueued"] = True
        if incident.get("state") == IssueLifecycleState.DETECTED.value:
            incident["state"] = IssueLifecycleState.QUEUED.value
        save_issue_state(state, state_file)


def record_issue_sent(
    issue_key: str,
    incident_id: str,
    state_file: str | None = None,
) -> None:
    """
    Record that an issue has been dispatched by the outbox worker.
    """
    state = load_issue_state(state_file)
    incident = state.get("active_incidents", {}).get(issue_key)
    if incident and incident.get("incident_id") == incident_id:
        incident["state"] = IssueLifecycleState.SENT.value
        save_issue_state(state, state_file)


def record_issue_delivered(
    issue_key: str,
    incident_id: str,
    state_file: str | None = None,
) -> None:
    """
    Record that an issue incident has been confirmed delivered/acknowledged by the backend.
    Transitions state to ACKNOWLEDGED without marking the underlying problem recovered.
    """
    state = load_issue_state(state_file)
    incident = state.get("active_incidents", {}).get(issue_key)
    if incident and incident.get("incident_id") == incident_id:
        incident["state"] = IssueLifecycleState.ACKNOWLEDGED.value
        incident["acknowledged_at"] = _utc_now()
        incident["enqueued"] = True
        save_issue_state(state, state_file)
        logger.info(f"Issue {issue_key} incident {incident_id} transitioned to ACKNOWLEDGED.")


# Alias for explicit roadmap nomenclature
record_issue_acknowledged = record_issue_delivered


def get_active_incidents(state_file: str | None = None) -> dict:
    """
    Return all currently active incidents from persistent state.
    """
    state = load_issue_state(state_file)
    return dict(state.get("active_incidents", {}))


def get_active_issues(state_file: str | None = None) -> set[str]:
    """
    Return a set of active issue keys (e.g. {'high_ram'}).
    Provides full backward compatibility for callers expecting a set.
    """
    state = load_issue_state(state_file)
    return set(state.get("active_incidents", {}).keys())


def reset_issue_tracking(state_file: str | None = None) -> None:
    """
    Clear all persistent and in-memory issue tracking.
    Primary utility is test isolation.
    """
    default_state = _get_default_state()
    save_issue_state(default_state, state_file)
    global _ACTIVE_ISSUES
    _ACTIVE_ISSUES.clear()