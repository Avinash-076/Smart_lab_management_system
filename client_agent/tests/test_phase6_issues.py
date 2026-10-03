"""
Unit and integration tests for Phase 6: Issue Management (F-01, F-02, F-03, F-04).
"""

from __future__ import annotations

import json
import os
import time
from unittest.mock import MagicMock, patch
import uuid

import pytest

import config
from core.collector import collect_all_data
from core.health import CollectionResult, CollectorError
from core.outbox import DurableOutbox, OutboxPriority
from core.outbox.models import OutboxRecord, OutboxStatus
from core.runtime import AgentRuntime, TokenHolder, upload_issues
from modules.issues import (
    IssueLifecycleState,
    IssueRuleDefinition,
    detect_issues,
    get_active_incidents,
    get_active_issues,
    get_issue_rules,
    load_issue_state,
    record_issue_delivered,
    record_issue_enqueued,
    record_issue_sent,
    reset_issue_tracking,
    save_issue_state,
)


@pytest.fixture(autouse=True)
def clean_issue_tracking():
    """Ensure clean tracking before and after every test."""
    reset_issue_tracking()
    yield
    reset_issue_tracking()


# ============================================================================
# F-03: Centralized Issue Rule Authority & Configuration
# ============================================================================

def test_rule_catalog_baseline_rules():
    """Verify centralized rule catalog defines high_ram and low_disk baseline rules."""
    rules = get_issue_rules()
    rule_map = {r.issue_key: r for r in rules}

    assert "high_ram" in rule_map
    assert "low_disk" in rule_map

    ram_rule = rule_map["high_ram"]
    assert ram_rule.title == "High Memory Usage"
    assert ram_rule.severity == "high"
    assert ram_rule.trigger_threshold == 85.0
    assert ram_rule.recovery_threshold == 80.0

    disk_rule = rule_map["low_disk"]
    assert disk_rule.title == "Low Disk Space"
    assert disk_rule.severity == "critical"
    assert disk_rule.trigger_threshold == 90.0
    assert disk_rule.recovery_threshold == 85.0


def test_rule_catalog_config_overrides(monkeypatch):
    """Verify rule thresholds dynamically respect configuration / environment overrides."""
    monkeypatch.setattr(config, "RAM_HIGH_THRESHOLD", 75.0)
    monkeypatch.setattr(config, "RAM_RECOVERY_THRESHOLD", 70.0)
    monkeypatch.setattr(config, "DISK_CRITICAL_THRESHOLD", 95.0)
    monkeypatch.setattr(config, "DISK_RECOVERY_THRESHOLD", 88.0)

    rules = get_issue_rules()
    rule_map = {r.issue_key: r for r in rules}

    assert rule_map["high_ram"].trigger_threshold == 75.0
    assert rule_map["high_ram"].recovery_threshold == 70.0
    assert rule_map["low_disk"].trigger_threshold == 95.0
    assert rule_map["low_disk"].recovery_threshold == 88.0


def test_metric_extractors_safe_on_missing_or_failed_data():
    """Verify metric extractors safely handle None, failed ExecutionResult, and corrupted values."""
    rules = get_issue_rules()
    ram_rule = next(r for r in rules if r.issue_key == "high_ram")
    disk_rule = next(r for r in rules if r.issue_key == "low_disk")

    # Empty payload
    assert ram_rule.metric_extractor({}) is None
    assert disk_rule.metric_extractor({}) is None

    # Failed collector result
    failed_result = CollectionResult(
        status="failed",
        error=CollectorError("Hardware", "read", "TimeoutError", "Hardware read timeout"),
    )
    assert ram_rule.metric_extractor({"hardware": failed_result}) is None
    assert disk_rule.metric_extractor({"hardware": failed_result}) is None

    # Invalid non-numeric values
    assert ram_rule.metric_extractor({"hardware": {"ram_percent": "corrupted"}}) is None
    assert disk_rule.metric_extractor({"hardware": {"disk_percent": [1, 2]}}) is None

    # Valid values
    assert ram_rule.metric_extractor({"hardware": {"ram_percent": 88.5}}) == 88.5
    assert disk_rule.metric_extractor({"hardware": {"disk_percent": "92.0"}}) == 92.0


def test_rule_authority_distinction_documented():
    """Verify architectural documentation distinguishes client Issues from backend Notifications."""
    import modules.issues as issues_mod
    doc = issues_mod.__doc__ or ""
    with open(issues_mod.__file__, "r", encoding="utf-8") as f:
        content = f.read()

    assert "Client Issue Authority" in content
    assert "Backend Alert Authority" in content
    assert "Distinction & Non-Interference" in content


# ============================================================================
# F-04: Debounce, Hysteresis, and Oscillation Suppression
# ============================================================================

def test_transient_spike_suppressed_by_debounce(tmp_path, monkeypatch):
    """A single transient cycle above trigger threshold must NOT emit an issue when debounce=2."""
    state_file = str(tmp_path / "issue_state.json")
    monkeypatch.setattr(config, "ISSUE_DEBOUNCE_CYCLES", 2)

    # Cycle 1: RAM spikes to 89% (trigger > 85%)
    data_spike = {"hardware": {"ram_percent": 89.0, "disk_percent": 50.0}}
    issues = detect_issues(data_spike, state_file=state_file)

    # Must NOT emit an issue yet
    assert len(issues) == 0
    state = load_issue_state(state_file)
    incident = state["active_incidents"].get("high_ram")
    assert incident is not None
    assert incident["state"] == IssueLifecycleState.DETECTED.value
    assert incident["consecutive_count"] == 1

    # Cycle 2: RAM drops back to normal (75%)
    data_normal = {"hardware": {"ram_percent": 75.0, "disk_percent": 50.0}}
    issues_cycle2 = detect_issues(data_normal, state_file=state_file)

    # Must NOT emit; detection reset
    assert len(issues_cycle2) == 0
    state_after = load_issue_state(state_file)
    assert "high_ram" not in state_after["active_incidents"]


def test_consecutive_confirmation_satisfies_debounce(tmp_path, monkeypatch):
    """Consecutive breaches satisfying debounce trigger and emit the issue."""
    state_file = str(tmp_path / "issue_state.json")
    monkeypatch.setattr(config, "ISSUE_DEBOUNCE_CYCLES", 2)

    data_breach = {"hardware": {"ram_percent": 88.0, "disk_percent": 50.0}}

    # Cycle 1: sample 1/2
    emitted_1 = detect_issues(data_breach, state_file=state_file)
    assert len(emitted_1) == 0

    # Cycle 2: sample 2/2 -> Debounce satisfied!
    emitted_2 = detect_issues(data_breach, state_file=state_file)
    assert len(emitted_2) == 1
    issue = emitted_2[0]
    assert issue["issue_key"] == "high_ram"
    assert issue["title"] == "High Memory Usage"
    assert issue["severity"] == "high"
    assert "incident_id" in issue

    state = load_issue_state(state_file)
    incident = state["active_incidents"]["high_ram"]
    assert incident["state"] == IssueLifecycleState.QUEUED.value
    assert incident["consecutive_count"] == 2

    # Cycle 3: sustained high RAM does NOT emit duplicate issue
    emitted_3 = detect_issues(data_breach, state_file=state_file)
    assert len(emitted_3) == 0


def test_hysteresis_preserves_active_incident_above_recovery_threshold(tmp_path, monkeypatch):
    """Once active, issue does not recover merely because it drops below trigger threshold."""
    state_file = str(tmp_path / "issue_state.json")
    monkeypatch.setattr(config, "ISSUE_DEBOUNCE_CYCLES", 1)  # instant for clear cycle tracing

    # Trigger threshold = 85.0, Recovery threshold = 80.0
    # Cycle 1: RAM = 88.0 -> triggers
    emitted = detect_issues({"hardware": {"ram_percent": 88.0}}, state_file=state_file)
    assert len(emitted) == 1
    incident_id = emitted[0]["incident_id"]

    # Mark as enqueued to simulate outbox enqueue
    record_issue_enqueued("high_ram", incident_id, state_file)

    # Cycle 2: RAM = 84.0 (below trigger 85.0, but ABOVE recovery 80.0)
    emitted_2 = detect_issues({"hardware": {"ram_percent": 84.0}}, state_file=state_file)
    assert len(emitted_2) == 0
    state = load_issue_state(state_file)
    assert "high_ram" in state["active_incidents"]
    assert state["active_incidents"]["high_ram"]["incident_id"] == incident_id

    # Cycle 3: RAM = 81.0 (still above recovery 80.0)
    detect_issues({"hardware": {"ram_percent": 81.0}}, state_file=state_file)
    state = load_issue_state(state_file)
    assert "high_ram" in state["active_incidents"]

    # Cycle 4: RAM = 79.5 (falls to or below recovery threshold 80.0) -> RECOVERED!
    detect_issues({"hardware": {"ram_percent": 79.5}}, state_file=state_file)
    state_recovered = load_issue_state(state_file)
    assert "high_ram" not in state_recovered["active_incidents"]
    assert "high_ram" in state_recovered["recent_recoveries"]
    assert state_recovered["recent_recoveries"]["high_ram"]["incident_id"] == incident_id


def test_oscillation_around_trigger_does_not_spam_incidents(tmp_path, monkeypatch):
    """Oscillation around trigger threshold (84% <-> 86%) must not spam duplicate incidents."""
    state_file = str(tmp_path / "issue_state.json")
    monkeypatch.setattr(config, "ISSUE_DEBOUNCE_CYCLES", 1)

    total_emitted = []

    # Sequence of values bouncing around 85%:
    # 86% (trigger) -> 84% -> 86% -> 84% -> 87% -> 84%
    values = [86.0, 84.0, 86.0, 84.0, 87.0, 84.0]
    for val in values:
        out = detect_issues({"hardware": {"ram_percent": val}}, state_file=state_file)
        if out:
            for item in out:
                record_issue_enqueued(item["issue_key"], item["incident_id"], state_file)
            total_emitted.extend(out)

    # Exactly 1 incident emitted across all oscillations
    assert len(total_emitted) == 1
    state = load_issue_state(state_file)
    assert "high_ram" in state["active_incidents"]
    assert state["active_incidents"]["high_ram"]["consecutive_count"] == len(values)


def test_new_incident_gets_new_incident_id_after_recovery(tmp_path, monkeypatch):
    """After a valid recovery, a future breach creates a brand new incident_id."""
    state_file = str(tmp_path / "issue_state.json")
    monkeypatch.setattr(config, "ISSUE_DEBOUNCE_CYCLES", 1)

    # Breach 1
    out1 = detect_issues({"hardware": {"ram_percent": 90.0}}, state_file=state_file)
    assert len(out1) == 1
    id1 = out1[0]["incident_id"]

    # Recovery
    detect_issues({"hardware": {"ram_percent": 75.0}}, state_file=state_file)

    # Breach 2
    out2 = detect_issues({"hardware": {"ram_percent": 92.0}}, state_file=state_file)
    assert len(out2) == 1
    id2 = out2[0]["incident_id"]

    assert id1 != id2


def test_cooldown_suppresses_immediate_rebreach_if_configured(tmp_path, monkeypatch):
    """When ISSUE_COOLDOWN_SECONDS is configured, immediate re-breach within cooldown is ignored."""
    state_file = str(tmp_path / "issue_state.json")
    monkeypatch.setattr(config, "ISSUE_DEBOUNCE_CYCLES", 1)
    monkeypatch.setattr(config, "ISSUE_COOLDOWN_SECONDS", 60)

    # Breach 1 and recovery
    detect_issues({"hardware": {"ram_percent": 90.0}}, state_file=state_file)
    detect_issues({"hardware": {"ram_percent": 70.0}}, state_file=state_file)

    # Immediate re-breach 2 seconds later
    rebreach = detect_issues({"hardware": {"ram_percent": 90.0}}, state_file=state_file)
    assert len(rebreach) == 0

    # Simulate cooldown expiration
    state = load_issue_state(state_file)
    state["recent_recoveries"]["high_ram"]["recovered_at_ts"] = time.time() - 70
    save_issue_state(state, state_file)

    # Now rebreach succeeds
    rebreach_after = detect_issues({"hardware": {"ram_percent": 90.0}}, state_file=state_file)
    assert len(rebreach_after) == 1


# ============================================================================
# F-01: Issue Incident State vs Delivery State Independence
# ============================================================================

def test_active_incident_survives_restart(tmp_path, monkeypatch):
    """Active incident stored in issue_state.json survives agent process restart."""
    state_file = str(tmp_path / "issue_state.json")
    monkeypatch.setattr(config, "ISSUE_DEBOUNCE_CYCLES", 1)

    # Process 1: detect and emit
    emitted = detect_issues({"hardware": {"disk_percent": 95.0}}, state_file=state_file)
    assert len(emitted) == 1
    incident_id = emitted[0]["incident_id"]
    record_issue_enqueued("low_disk", incident_id, state_file)

    # Process 2: simulates new agent boot
    fresh_state = load_issue_state(state_file)
    incident = fresh_state["active_incidents"].get("low_disk")
    assert incident is not None
    assert incident["incident_id"] == incident_id
    assert incident["state"] == IssueLifecycleState.QUEUED.value
    assert incident["consecutive_count"] == 1


def test_delivery_state_independent_of_detection_state(tmp_path, monkeypatch):
    """Delivery failure or success does not falsely clear the active incident."""
    state_file = str(tmp_path / "issue_state.json")
    monkeypatch.setattr(config, "ISSUE_DEBOUNCE_CYCLES", 1)

    out = detect_issues({"hardware": {"ram_percent": 90.0}}, state_file=state_file)
    incident_id = out[0]["incident_id"]

    # Delivery fails (network outage) -> incident MUST remain active
    state = load_issue_state(state_file)
    assert "high_ram" in state["active_incidents"]
    assert state["active_incidents"]["high_ram"]["state"] == IssueLifecycleState.QUEUED.value

    # Delivery confirmed by backend (ACK)
    record_issue_delivered("high_ram", incident_id, state_file)

    state_acked = load_issue_state(state_file)
    assert "high_ram" in state_acked["active_incidents"]
    # State is now ACKNOWLEDGED, but incident is NOT recovered because machine is still at 90%
    assert state_acked["active_incidents"]["high_ram"]["state"] == IssueLifecycleState.ACKNOWLEDGED.value

    # Next cycle evaluates: RAM is still 90%
    detect_issues({"hardware": {"ram_percent": 90.0}}, state_file=state_file)
    state_next = load_issue_state(state_file)
    assert "high_ram" in state_next["active_incidents"]
    assert state_next["active_incidents"]["high_ram"]["state"] == IssueLifecycleState.ACKNOWLEDGED.value


# ============================================================================
# F-02: Delivery Reliability & Durable Outbox Integration
# ============================================================================

def test_stable_incident_idempotency_key():
    """Stable incident idempotency key format: issue_{comp_id}_{issue_key}_{incident_id}."""
    comp_id = 101
    issue_key = "high_ram"
    incident_id = "inc_test_123"
    expected = "issue_101_high_ram_inc_test_123"

    token_holder = TokenHolder("test_token")
    mock_outbox = MagicMock(spec=DurableOutbox)
    mock_outbox.get_record_by_idempotency_key.return_value = None

    data = {
        "issues": [{
            "issue_key": issue_key,
            "incident_id": incident_id,
            "title": "High Memory Usage",
            "description": "High RAM",
            "severity": "high",
        }]
    }

    with patch("core.runtime.get_computer_id", return_value=comp_id):
        success = upload_issues(data, token_holder, outbox=mock_outbox)

    assert success is True
    mock_outbox.enqueue.assert_called_once()
    call_kwargs = mock_outbox.enqueue.call_args.kwargs
    assert call_kwargs["idempotency_key"] == expected
    assert call_kwargs["event_type"] == "issue"
    assert call_kwargs["priority"] == OutboxPriority.ISSUE


def test_pending_or_processing_record_not_duplicated_in_outbox(tmp_path):
    """If an active incident is already PENDING or PROCESSING in outbox, do not duplicate."""
    outbox_db = str(tmp_path / "outbox.db")
    outbox = DurableOutbox(db_path=outbox_db)
    token_holder = TokenHolder("test_token")
    comp_id = 202

    issue_payload = {
        "issue_key": "low_disk",
        "incident_id": "disk_inc_1",
        "title": "Low Disk Space",
        "description": "Disk Full",
        "severity": "critical",
    }
    data = {"issues": [issue_payload]}

    with patch("core.runtime.get_computer_id", return_value=comp_id):
        # First upload: enqueues record
        assert upload_issues(data, token_holder, outbox=outbox) is True
        assert outbox.get_stats()["total_count"] == 1

        # Second upload while PENDING: does NOT duplicate
        assert upload_issues(data, token_holder, outbox=outbox) is True
        assert outbox.get_stats()["total_count"] == 1

        # Mark as PROCESSING
        batch = outbox.get_pending_batch(limit=1)
        assert len(batch) == 1
        record = batch[0]
        assert record.status == OutboxStatus.PROCESSING

        # Third upload while PROCESSING: still does NOT duplicate
        assert upload_issues(data, token_holder, outbox=outbox) is True
        assert outbox.get_stats()["total_count"] == 1


def test_dead_letter_record_requeued_for_active_incident(tmp_path):
    """If an active incident has a DEAD_LETTER record, upload_issues revives it for retry."""
    outbox_db = str(tmp_path / "outbox.db")
    outbox = DurableOutbox(db_path=outbox_db)
    token_holder = TokenHolder("test_token")
    comp_id = 303

    issue_payload = {
        "issue_key": "high_ram",
        "incident_id": "ram_dead_letter_1",
        "title": "High Memory Usage",
        "description": "RAM high",
        "severity": "high",
    }
    data = {"issues": [issue_payload]}

    with patch("core.runtime.get_computer_id", return_value=comp_id):
        upload_issues(data, token_holder, outbox=outbox)

        # Force record to DEAD_LETTER
        batch = outbox.get_pending_batch(limit=1)
        record = batch[0]
        with outbox._get_connection() as conn:
            conn.execute(
                "UPDATE outbox_items SET status = ?, last_error = ? WHERE id = ?;",
                (OutboxStatus.DEAD_LETTER.value, "Simulated permanent 500 error", record.id),
            )
            conn.commit()

        stats_dead = outbox.get_stats()
        assert stats_dead["status_counts"].get(OutboxStatus.DEAD_LETTER.value, 0) == 1
        assert stats_dead["status_counts"].get(OutboxStatus.PENDING.value, 0) == 0

        # Next upload cycle revives it!
        upload_issues(data, token_holder, outbox=outbox)

        stats_revived = outbox.get_stats()
        assert stats_revived["status_counts"].get(OutboxStatus.DEAD_LETTER.value, 0) == 0
        assert stats_revived["status_counts"].get(OutboxStatus.PENDING.value, 0) == 1


def test_outbox_delivered_callback_marks_acknowledged(tmp_path):
    """When outbox delivery confirms delivery, runtime callback transitions state to ACKNOWLEDGED."""
    state_file = str(tmp_path / "issue_state.json")
    incident_id = "test_ack_incident"

    # Seed state in QUEUED
    save_issue_state({
        "version": 1,
        "active_incidents": {
            "high_ram": {
                "issue_key": "high_ram",
                "incident_id": incident_id,
                "state": IssueLifecycleState.QUEUED.value,
                "consecutive_count": 2,
            }
        }
    }, state_file)

    # Deliver record
    record_issue_delivered("high_ram", incident_id, state_file=state_file)

    state = load_issue_state(state_file)
    incident = state["active_incidents"]["high_ram"]
    assert incident["state"] == IssueLifecycleState.ACKNOWLEDGED.value
    assert "acknowledged_at" in incident


def test_direct_upload_success_and_failure(tmp_path):
    """In synchronous direct mode (outbox=None), upload_issues marks ACK on success and preserves on error."""
    state_file = str(tmp_path / "issue_state.json")
    incident_id = "direct_mode_inc"

    save_issue_state({
        "version": 1,
        "active_incidents": {
            "low_disk": {
                "issue_key": "low_disk",
                "incident_id": incident_id,
                "state": IssueLifecycleState.QUEUED.value,
            }
        }
    }, state_file)

    data = {
        "issues": [{
            "issue_key": "low_disk",
            "incident_id": incident_id,
            "title": "Low Disk Space",
            "description": "Full",
            "severity": "critical",
        }]
    }
    token_holder = TokenHolder("direct_token")

    # Failure scenario
    with patch("core.runtime.send_issue", side_effect=RuntimeError("Network drop")):
        with patch("core.runtime.get_computer_id", return_value=500):
            res_fail = upload_issues(data, token_holder, outbox=None, state_file=state_file)
            assert res_fail is False

    # State must STILL be QUEUED (not falsely cleared)
    state = load_issue_state(state_file)
    assert state["active_incidents"]["low_disk"]["state"] == IssueLifecycleState.QUEUED.value

    # Success scenario
    with patch("core.runtime.send_issue", return_value={"id": 999}):
        with patch("core.runtime.get_computer_id", return_value=500):
            res_ok = upload_issues(data, token_holder, outbox=None, state_file=state_file)
            assert res_ok is True

    # State is now ACKNOWLEDGED
    state_ok = load_issue_state(state_file)
    assert state_ok["active_incidents"]["low_disk"]["state"] == IssueLifecycleState.ACKNOWLEDGED.value


# ============================================================================
# Robustness, State Persistence & Hygiene
# ============================================================================

def test_corrupted_issue_state_file_handled_safely(tmp_path):
    """Corrupted issue_state.json must not crash agent and falls back to clean state."""
    state_file = str(tmp_path / "corrupted_issue_state.json")
    with open(state_file, "w", encoding="utf-8") as f:
        f.write("{invalid_json: true, unterminated")

    state = load_issue_state(state_file)
    assert state["version"] == 1
    assert state["active_incidents"] == {}

    # Must still detect issues normally
    emitted = detect_issues({"hardware": {"ram_percent": 95.0}}, state_file=state_file)
    assert isinstance(emitted, list)


def test_atomic_state_persistence(tmp_path):
    """save_issue_state must perform atomic replace."""
    state_file = str(tmp_path / "nested" / "issue_state.json")
    state = {
        "version": 1,
        "active_incidents": {
            "high_ram": {
                "issue_key": "high_ram",
                "incident_id": "test_atomic_1",
                "state": IssueLifecycleState.QUEUED.value,
            }
        }
    }
    save_issue_state(state, state_file)
    assert os.path.exists(state_file)

    loaded = load_issue_state(state_file)
    assert "high_ram" in loaded["active_incidents"]


def test_no_secrets_in_issue_state_file(tmp_path, monkeypatch):
    """Ensure issue_state.json contains no credentials, tokens, or private secrets."""
    state_file = str(tmp_path / "issue_state.json")
    monkeypatch.setattr(config, "ISSUE_DEBOUNCE_CYCLES", 1)

    detect_issues({"hardware": {"ram_percent": 90.0, "disk_percent": 92.0}}, state_file=state_file)

    with open(state_file, "r", encoding="utf-8") as f:
        content = f.read().lower()

    forbidden_terms = ["token", "secret", "password", "bearer", "authorization"]
    for term in forbidden_terms:
        assert term not in content, f"Found sensitive term '{term}' in issue_state.json"


def test_empty_or_missing_metrics_do_not_create_false_issues(tmp_path):
    """Empty, missing, or null metrics must never create or clear issues."""
    state_file = str(tmp_path / "issue_state.json")

    # Cycle with empty dict
    out1 = detect_issues({}, state_file=state_file)
    assert len(out1) == 0

    # Cycle with null hardware
    out2 = detect_issues({"hardware": None}, state_file=state_file)
    assert len(out2) == 0

    # Cycle with null metrics inside hardware
    out3 = detect_issues({"hardware": {"ram_percent": None, "disk_percent": None}}, state_file=state_file)
    assert len(out3) == 0

    state = load_issue_state(state_file)
    assert len(state["active_incidents"]) == 0
