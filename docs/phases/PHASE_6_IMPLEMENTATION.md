# Phase 6 Implementation Report: Issue Management

## 1. Objective
Harden the SLMS Client Agent issue management subsystem to ensure reliable endpoint issue detection, persistent incident lifecycle tracking, decoupled delivery states, stable idempotency, consecutive-cycle debounce, and hysteresis-based recovery. Decouple transient threshold breach detection from persistent administrative issue tickets without modifying outbox schemas or backend notification services.

---

## 2. Problems Addressed (F-01 through F-04)
| ID | Requirement / Problem | Resolution Summary |
| :--- | :--- | :--- |
| **F-01** | Separate issue detection state from delivery state | Replaced volatile in-memory `_ACTIVE_ISSUES` with persistent JSON store `%PROGRAMDATA%\SLMS\data\issue_state.json` written via atomic replacement. Formalized 6-phase state machine: `NO_ACTIVE_INCIDENT`, `DETECTED`, `QUEUED`, `SENT`, `ACKNOWLEDGED`, `RECOVERED`. Delivery failure does not clear detection state; delivery success does not clear active condition. |
| **F-02** | Reliable issue delivery/retry without suppression | Reused Phase 3 `DurableOutbox` with stable idempotency keys `issue_{computer_id}_{issue_key}_{incident_id}`. Enforced deduplication for `PENDING` and `PROCESSING` records. Implemented automatic `DEAD_LETTER` revival (`requeue_dead_letter`) on subsequent evaluations while incident remains active. Integrated outbox `_handle_outbox_delivered` callback to mark `ACKNOWLEDGED`. |
| **F-03** | Explicit issue-rule authority and configuration | Centralized declarative rule catalog (`IssueRuleDefinition`, `get_issue_rules()`) in `client_agent/modules/issues.py`. Preserved baseline RAM (>85%) and Disk (>90%) rules with configurable environment variable overrides. Documented explicit boundary separating client formal `Issue` tickets from backend real-time `Notification` alerts. |
| **F-04** | Debounce + hysteresis | Implemented consecutive-cycle confirmation debounce (`ISSUE_DEBOUNCE_CYCLES = 2` cycles / 40s) preventing false alarms on transient spikes. Implemented hysteresis recovery thresholds (RAM trigger >85% / recovery <=80%; Disk trigger >90% / recovery <=85%) preventing oscillation spam around thresholds. Enforced fresh `incident_id` generation for new incidents post-recovery. Supported configurable cooldown (`ISSUE_COOLDOWN_SECONDS`). |

---

## 3. Architectural Distinction: Client Issues vs. Backend Notifications (F-03)

The audit and implementation establish a strict architectural separation between client-side and backend authorities:

1. **Client Issue Authority (Endpoint Ticket Generation)**:
   - **Mechanism**: The client agent inspects local OS metrics every 20 seconds. When a sustained physical degradation is confirmed across debounce cycles, it submits an `IssueAgentCreate` payload (`POST /api/issues/agent`).
   - **Semantics**: Formal administrative tickets representing persistent machine health problems (e.g. low disk space, leaking RAM).
   - **Lifecycle**: Managed by administrators through ticket triage, status updates (`open` -> `in_progress` -> `resolved`), and resolution notes.
   - **Authority**: The client agent is authoritative for creating and clearing endpoint-level incident tracking.

2. **Backend Notification Authority (Fleet Telemetry Alerts)**:
   - **Mechanism**: The backend (`app/services/alert_service.py`) processes high-frequency time-series telemetry streams (`POST /api/metrics`).
   - **Semantics**: Operator alert banners and dashboard notifications warning of real-time load spikes.
   - **Lifecycle**: Ephemeral alerts displayed in real-time dashboards; dismissed or acknowledged by logged-in users.
   - **Authority**: The backend server is authoritative for fleet-wide real-time metric threshold alerts.

**Non-Interference Guarantee**:
- Client Issues do NOT replace backend Notifications.
- Backend Notifications do NOT replace client Issues.
- Neither authority suppresses or conflicts with the other; both operate in parallel.

---

## 4. Persistent State Architecture & Lifecycle State Machine (F-01)

### 4.1 Persistent Storage Schema
Incident state is persisted in `%PROGRAMDATA%\SLMS\data\issue_state.json` (or `SLMS_DATA_DIR/issue_state.json` in tests and development mode).
Writes are atomic using the established Phase 4/5 pattern: `tempfile.mkstemp()` in target directory followed by `os.replace()`.

```json
{
  "version": 1,
  "updated_at": "2026-09-27T11:00:20.123456+00:00",
  "active_incidents": {
    "high_ram": {
      "issue_key": "high_ram",
      "incident_id": "a1b2c3d4e5f6",
      "state": "ACKNOWLEDGED",
      "consecutive_count": 5,
      "first_detected_at": "2026-09-27T10:58:40.000000+00:00",
      "last_confirmed_at": "2026-09-27T11:00:20.000000+00:00",
      "acknowledged_at": "2026-09-27T10:59:05.123456+00:00",
      "cleared_at": null,
      "enqueued": true,
      "emitted": true,
      "payload": {
        "issue_key": "high_ram",
        "incident_id": "a1b2c3d4e5f6",
        "title": "High Memory Usage",
        "description": "RAM usage is above the 85.0% threshold. Current RAM usage: 88.5%.\n\nDetected at: 2026-09-27T10:59:00.000000+00:00",
        "severity": "high"
      }
    }
  },
  "recent_recoveries": {
    "low_disk": {
      "incident_id": "9f8e7d6c5b4a",
      "recovered_at": "2026-09-27T10:30:00.000000+00:00",
      "recovered_at_ts": 1727433000.0
    }
  }
}
```

### 4.2 State Machine Model
```
NO_ACTIVE_INCIDENT
        |
        | [metric > trigger_threshold] (sample 1)
        v
    DETECTED (confirming debounce, sample count < debounce_cycles)
        |
        | [metric > trigger_threshold] (sample count >= debounce_cycles)
        v
     QUEUED (debounce confirmed, emitted payload, outbox enqueue pending)
        |
        | [outbox delivery worker claims and dispatches]
        v
      SENT (outbox item in PROCESSING status)
        |
        | [backend returns HTTP 201 / HTTP 200 ACK]
        v
  ACKNOWLEDGED (delivery confirmed, hardware condition still sustained)
        |
        | [metric <= recovery_threshold] (hysteresis satisfied)
        v
   RECOVERED (cleared_at recorded, state reset)
        |
        v
NO_ACTIVE_INCIDENT
```

### 4.3 State Decoupling Invariants
1. **Detection Independence**: Outbox network failures, socket timeouts, or HTTP 5xx responses DO NOT transition detection state back to normal. The incident remains active in state `QUEUED` or `SENT`.
2. **Delivery Independence**: Successful backend delivery (`ACKNOWLEDGED`) DOES NOT clear the incident. The incident remains active until local hardware metrics physically drop to or below the recovery threshold.
3. **Restart Resilience**: Active incidents survive agent restarts. On reboot, `issue_state.json` is reloaded; active incidents retain their exact `incident_id` and do not generate duplicate tickets.

---

## 5. Delivery Reliability & Durable Outbox Integration (F-02)

### 5.1 Stable Idempotency Key
Previously, `upload_issues` generated keys using Unix epoch timestamps:
`key = f"issue_{comp_id}_{title_slug}_{int(time.time())}"`
This caused duplicate outbox records upon agent restart or re-evaluation during network partitions.

Phase 6 replaces this with a stable incident identity:
`key = f"issue_{comp_id}_{issue_key}_{incident_id}"`
- `comp_id`: Enrolled computer ID.
- `issue_key`: Deterministic rule identifier (`high_ram`, `low_disk`).
- `incident_id`: Unique hex identifier generated once when debounce is confirmed.

This key is completely stable across:
- Repeated 20-second monitoring cycles
- Agent process and Windows Service restarts
- Network outages and retry backoff cycles
- Outbox worker restarts

### 5.2 Outbox State Handling & Deduplication
When `upload_issues()` evaluates an active incident:
1. **Existing Record is `PENDING` or `PROCESSING`**: `upload_issues` notes that delivery is already queued in the local outbox. It avoids duplicate enqueuing.
2. **Existing Record is `DELIVERED`**: Notes that outbox has already dispatched this incident; invokes `record_issue_delivered()` to ensure local state is `ACKNOWLEDGED`.
3. **Existing Record is `DEAD_LETTER`**: If retries were previously exhausted during an extended server outage, `upload_issues` calls `outbox.requeue_dead_letter(record.id)`. The incident record is revived to `PENDING` status with retry count reset, guaranteeing delivery once connectivity returns.
4. **No Record in Outbox**: Enqueues new record with priority `OutboxPriority.ISSUE = 2` (protected from backpressure pruning).

---

## 6. Centralized Issue Rule Catalog (F-03)

All issue rules are defined declaratively in `client_agent/modules/issues.py` via `IssueRuleDefinition`.

### Active Rule Definitions
1. **`high_ram`**:
   - **Title**: `"High Memory Usage"`
   - **Severity**: `"high"`
   - **Default Trigger**: `> 85.0%`
   - **Default Recovery**: `<= 80.0%`
   - **Extractor**: `_extract_ram_percent` (safe extraction with `None` fallback)
2. **`low_disk`**:
   - **Title**: `"Low Disk Space"`
   - **Severity**: `"critical"`
   - **Default Trigger**: `> 90.0%`
   - **Default Recovery**: `<= 85.0%`
   - **Extractor**: `_extract_disk_percent` (safe extraction with `None` fallback)

---

## 7. Debounce, Hysteresis & Oscillation Prevention (F-04)

### 7.1 Debounce (Consecutive Confirmations)
- Configured via `ISSUE_DEBOUNCE_CYCLES` (default: `2` cycles, corresponding to 40 seconds at normal 20s monitoring interval).
- **Cycle 1**: Trigger threshold breached. Incident is created in state `DETECTED` with `consecutive_count = 1`. No payload is emitted to outbox.
- **Cycle 2**: If metric drops back below trigger threshold, the transient spike is discarded and state returns to `NO_ACTIVE_INCIDENT`.
- **Cycle 2 (Sustained)**: If metric remains above trigger threshold, `consecutive_count` reaches 2 (`>= debounce_cycles`). State transitions to `QUEUED`, payload is built, and issue is emitted for outbox delivery.

### 7.2 Hysteresis (Separate Recovery Thresholds)
- **Problem**: When a metric hovers near the trigger threshold (e.g. RAM fluctuating between 84.8% and 85.2%), single-threshold systems spam rapid create/resolve cycles.
- **Solution**: Once active, an incident DOES NOT recover when dropping below the trigger threshold (85.0%). It only recovers when dropping to or below the recovery threshold (80.0%).
- **Oscillation Suppression**: A computer fluctuating between 82% and 88% maintains a single active incident throughout the oscillation.

### 7.3 New Incident Identity Post-Recovery
- When an incident recovers (metric `<= recovery_threshold`), it transitions to `RECOVERED` and is archived in `recent_recoveries`.
- If the metric subsequently breaches the trigger threshold in the future, a brand new `incident_id` (e.g. `uuid.uuid4().hex[:12]`) is generated.

### 7.4 Cooldown
- Configured via `ISSUE_COOLDOWN_SECONDS` (default: `0` / disabled).
- When configured (`> 0`), prevents re-triggering of the same `issue_key` within the cooldown window following recovery.

---

## 8. Configuration & Environment Variables

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `SLMS_RAM_HIGH_THRESHOLD` | `float` | `85.0` | RAM percentage threshold to trigger High Memory Usage issue |
| `SLMS_RAM_RECOVERY_THRESHOLD` | `float` | `80.0` | RAM percentage threshold to clear High Memory Usage issue |
| `SLMS_DISK_CRITICAL_THRESHOLD` | `float` | `90.0` | Disk percentage threshold to trigger Low Disk Space issue |
| `SLMS_DISK_RECOVERY_THRESHOLD` | `float` | `85.0` | Disk percentage threshold to clear Low Disk Space issue |
| `SLMS_ISSUE_DEBOUNCE_CYCLES` | `int` | `2` | Number of consecutive 20s cycles required to confirm an issue |
| `SLMS_ISSUE_COOLDOWN_SECONDS` | `int` | `0` | Minimum seconds after recovery before a new incident can trigger |

---

## 9. Verification & Test Suite Results

### 9.1 Phase 6 Test Suite (`client_agent/tests/test_phase6_issues.py`)
All 21 comprehensive test cases passed:
- `test_rule_catalog_baseline_rules`: PASS
- `test_rule_catalog_config_overrides`: PASS
- `test_metric_extractors_safe_on_missing_or_failed_data`: PASS
- `test_rule_authority_distinction_documented`: PASS
- `test_transient_spike_suppressed_by_debounce`: PASS
- `test_consecutive_confirmation_satisfies_debounce`: PASS
- `test_hysteresis_preserves_active_incident_above_recovery_threshold`: PASS
- `test_oscillation_around_trigger_does_not_spam_incidents`: PASS
- `test_new_incident_gets_new_incident_id_after_recovery`: PASS
- `test_cooldown_suppresses_immediate_rebreach_if_configured`: PASS
- `test_active_incident_survives_restart`: PASS
- `test_delivery_state_independent_of_detection_state`: PASS
- `test_stable_incident_idempotency_key`: PASS
- `test_pending_or_processing_record_not_duplicated_in_outbox`: PASS
- `test_dead_letter_record_requeued_for_active_incident`: PASS
- `test_outbox_delivered_callback_marks_acknowledged`: PASS
- `test_direct_upload_success_and_failure`: PASS
- `test_corrupted_issue_state_file_handled_safely`: PASS
- `test_atomic_state_persistence`: PASS
- `test_no_secrets_in_issue_state_file`: PASS
- `test_empty_or_missing_metrics_do_not_create_false_issues`: PASS

### 9.2 Regression Test Execution
- **Client Agent Suite**: `195 passed` (174 baseline + 21 Phase 6 tests) in 16.82s. 0 failed.
- **Backend Suite**: `23 passed` in 1.27s. 0 failed.
- **Total Test Count**: `218 passed`, `0 failed`.
- **Alembic Heads**: Exactly `a1b2c3d4e5f6 (head)`. No database migrations added.
- **git diff --check**: Passed with clean formatting.

---

## 10. Preserved Invariants & Strict Boundaries
- **Phase 3 Outbox Subsystem**: Outbox SQLite schema, priority levels, retry backoff algorithms, and pruning order were preserved without modification.
- **Phase 4 Collectors**: Collector execution models and health wrappers (`safe_run`) were preserved.
- **Phase 5 Cadence**: Process collection remains gated at 120s, software scans remain gated at 900s, and metrics/issues remain evaluated every 20s.
- **Scope Compliance**: Phase 7 (WebSocket redesign) and Phase 8 (Runtime/scheduler refactoring) were strictly NOT started.
