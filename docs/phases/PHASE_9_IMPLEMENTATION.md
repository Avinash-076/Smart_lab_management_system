# Phase 9 Implementation Report: Logging, Data Isolation, and Privacy Hardening

## 1. Overview & Objectives

Phase 9 completes the logging and privacy milestones for the SLMS Client Agent as outlined in the project roadmap, addressing issues **I-01 through I-07**:
- **I-01 (Log Rotation)**: Transition from unbounded standard `FileHandler` to `SafeRotatingFileHandler` with 5 MB per file threshold.
- **I-02 (Log Retention)**: Bound rotated logs to 5 backups (`client.log.1` ... `client.log.5`), preventing unbounded disk growth.
- **I-03 (Windows Service Data Directory)**: Restructure the local storage hierarchy under `%ProgramData%\SLMS\` into dedicated `logs\`, `data\`, and `cache\` domains, isolating outbox and state files under `data\`.
- **I-04 (Diagnostic Export Default)**: Maintain diagnostic export strictly disabled by default (`SLMS_EXPORT_JSON=0`).
- **I-05 (Atomic JSON Writes)**: Enforce crash-resilient atomic writes in `core/exporter.py` (`tempfile` + `flush` + `os.fsync` + `os.replace`).
- **I-06 (Diagnostic Retention)**: Restrict diagnostic exports to **ONE current snapshot** (`data/diagnostic/client_data.json`), removing legacy historical timestamped files.
- **I-07 (Generated Telemetry & Repository Hygiene)**: Untrack historical workstation telemetry from git and establish comprehensive `.gitignore` rules for all runtime artifacts.


---

## 2. Directory Layout Architecture

The target production layout under `%ProgramData%\SLMS\` is structured as follows:

```
C:\ProgramData\SLMS\
├── logs\
│   ├── client.log                      # Active log (max 5 MB)
│   ├── client.log.1                    # Rotated backup 1
│   └── client.log.5                    # Rotated backups (up to backupCount=5)
├── data\
│   ├── outbox\
│   │   ├── outbox.db                   # DurableOutbox SQLite database
│   │   ├── outbox.db-wal               # SQLite WAL journal
│   │   └── outbox.db-shm               # SQLite shared memory
│   ├── software_state.json             # Delivered software fingerprint
│   ├── usage_state.json                # Active process usage sessions
│   ├── issue_state.json                # Issue debounce & hysteresis state
│   └── diagnostic\                     # Only populated when SLMS_EXPORT_JSON=1
│       └── client_data.json            # Atomically written single current snapshot
├── cache\                              # Ephemeral data and query caches
└── config\
    └── service_credentials.enc         # DPAPI-encrypted machine enrollment vault
```

### Path Resolution
- **Production Mode**: Resolves to `%ProgramData%\SLMS` via `paths.get_data_dir()`.
- **Testing & Isolated Overrides**: Overridden via `SLMS_DATA_DIR` environment variable.
- **Development Mode**: `SLMS_DEV_MODE=1` falls back to base path for local development, while ensuring `.gitignore` prevents committing generated artifacts.
- **Explicit Initialization**: Module import no longer has directory creation side-effects. The explicit helper `paths.ensure_directories_exist()` is invoked on runtime startup and service initialization.

---

## 3. Log Rotation & Retention (I-01, I-02)

### Implementation
- `client_agent/core/logger.py` implements `SafeRotatingFileHandler(RotatingFileHandler)`.
- **Configurable Thresholds**:
  - `LOG_MAX_BYTES = 5 * 1024 * 1024` (5 MB, configurable via `SLMS_LOG_MAX_BYTES`)
  - `LOG_BACKUP_COUNT = 5` (5 files, configurable via `SLMS_LOG_BACKUP_COUNT`)
  - Encoding: `utf-8`
  - Logger Name: `"SLMS"`
  - Format: `%(asctime)s | %(levelname)s | %(message)s`
- **Windows File Locking Resiliency**:
  - Catches `PermissionError` or `OSError` in `doRollover()` if another process or thread temporarily holds the file handle during rotation, emitting a warning to `sys.stderr` and continuing appending rather than crashing the agent.
- **Bounded Storage Footprint**:
  - Active log (5 MB) + 5 backups (25 MB) = **Maximum ~30 MB upper bound**.

---

## 4. Diagnostic Export & Atomic Writes (I-04, I-05, I-06)

### Default State (I-04)
- Diagnostic export is strictly **OFF by default** in both interactive CLI and Windows Service modes (`SLMS_EXPORT_JSON=0` -> `config.EXPORT_JSON = False`).

### Atomic Write Pattern (I-05)
- `client_agent/core/exporter.py` implements atomic replacement:
  1. Creates temporary file `tempfile.NamedTemporaryFile("w", dir=OUTPUT_FOLDER, prefix=".tmp_diagnostic_", suffix=".json", delete=False, encoding="utf-8")`.
  2. Serializes data via `json.dump()`.
  3. Flushes user-space buffers with `tf.flush()`.
  4. Forces disk sync via `os.fsync(tf.fileno())`.
  5. Closes the temporary file handle.
  6. Atomically replaces destination snapshot via `os.replace(temp_path, target_filepath)`.
  7. Cleans up temporary file in `finally:` if an exception occurs, preserving the previous valid snapshot file intact.

### Single Snapshot Retention (I-06)
- **Policy**: Exactly **ONE current diagnostic snapshot** (`client_data.json`).
- Does not create accumulating timestamped files (`client_data_YYYYMMDD_HHMMSS.json`).
- `clean_legacy_diagnostic_files()` automatically purges any obsolete timestamped diagnostic files in the diagnostic directory.

---

## 5. Repository Hygiene & Telemetry Removal (I-07)

1. **Untracked Historical Workstation Telemetry**:
   - `client_agent/output/client_data.json` (committed in `4d04c979`) contained real system hostname, IP, MAC address, and installed software.
   - Removed from git tracking via `git rm client_agent/output/client_data.json`.
2. **Updated `.gitignore` and `client_agent/.gitignore`**:
   - Explicitly ignores:
     - `logs/`, `client_agent/logs/`, `*.log`, `*.log.*`
     - `output/`, `client_agent/output/`
     - `cache/`, `client_agent/cache/`
     - `client_agent/data/*` (preserving `data/agent.json`)
     - `software_state.json`, `usage_state.json`, `issue_state.json`, `client_data.json`
     - `service_credentials.enc`, `agent_credential.json`

---

## 6. Windows ACL Hardening Strategy

- **Function**: `service.service.configure_service_folder_permissions()`
- **Access Model**:
  - Administrators: Full Control `(OI)(CI)(F)`
  - SYSTEM: Full Control `(OI)(CI)(F)`
  - SLMS Service Account (`LocalService` or custom): Modify `(OI)(CI)(M)`
  - Credential Vault (`service_credentials.enc`): Read `(R)` for Service Account, with stricter inheritance removal.
- **No Silent Exception Suppression (Correction 2)**:
  - Checks subprocess return codes and logs explicit warnings or errors on failure with exact stderr/stdout output.
  - Development mode (`SLMS_DEV_MODE=1`) skips production folder ACL modification to avoid altering local developer repository permissions.
  - Phase 11 will integrate full MSI installer elevation provisioning.

---

## 7. Privacy Data Inventory & Verification

- **Process / Student Usernames**: Zero usernames collected. Phase 1 removal of process usernames (`system_info.py`, `processes.py`, `usage.py`) remains 100% verified.
- **Authentication Secrets**: JWT tokens and enrollment credentials exist only in DPAPI-encrypted storage or memory. No token material is printed to logs or diagnostic JSON.

---

---

## 8. Outbox Database Migration Mechanism (Phase 8 -> Phase 9)

- **Legacy Location**: `%ProgramData%\SLMS\outbox\outbox.db` (and `-wal`, `-shm`)
- **Phase 9 Authoritative Location**: `%ProgramData%\SLMS\data\outbox\outbox.db`
- **Migration Architecture**:
  - Implemented in `client_agent.core.outbox.migration.migrate_legacy_outbox()`.
  - Invoked during startup in `OutboxManager.__init__()` and `setup_service_environment()` **before** `DurableOutbox` is opened.
  - **No Module Import Side-effects**: Migration is explicit, not triggered by importing `paths.py`.
  - **Idempotency**: Running migration multiple times is completely idempotent. Once migrated, legacy folder is removed.
  - **Conflict Safety**: If both old and new outbox databases exist, migration safely halts, logs a critical error, and raises `RuntimeError` requiring administrator consolidation. It **never** blindly overwrites or silently merges SQLite databases.
  - **Lock Safety**: Probes `is_database_locked()` via SQLite exclusive transaction probe AND Windows OS file handle probes on the database and sidecar files (`-wal`, `-shm`) before attempting moves.
  - **WAL Preservation**: Issues `PRAGMA wal_checkpoint(TRUNCATE)` before atomically moving the database and sidecar files.
  - **Development Mode Isolation**: Development mode (`SLMS_DEV_MODE=1`) operates against local `BASE_PATH`, completely isolated from production `%ProgramData%`.

---

## 9. Verification & Test Results

### Phase 9 Test Suite (`test_phase9_logging_privacy.py`)
25 tests covering:
- `test_log_handler_is_rotating`: PASS
- `test_log_rotation_on_threshold`: PASS
- `test_log_backup_count_is_bounded`: PASS
- `test_windows_service_data_directory_layout`: PASS
- `test_state_files_are_under_data`: PASS
- `test_diagnostic_directory_is_under_data`: PASS
- `test_ensure_directories_exist`: PASS
- `test_diagnostic_export_off_by_default`: PASS
- `test_explicit_diagnostic_export_opt_in`: PASS
- `test_atomic_json_replacement`: PASS
- `test_failed_json_serialization_preserves_previous_file`: PASS
- `test_temporary_json_file_is_cleaned_up`: PASS
- `test_diagnostic_retention_is_one_snapshot`: PASS
- `test_tracked_client_data_json_is_removed`: PASS
- `test_runtime_state_patterns_in_gitignore`: PASS
- `test_durable_outbox_integration_with_new_data_path`: PASS
- `test_acl_helper_behavior_without_elevation`: PASS
- `test_migration_old_outbox_only_migrated_to_new_path` (14a): PASS
- `test_migration_no_old_outbox_normal_startup` (14b): PASS
- `test_migration_new_outbox_already_exists_no_overwrite` (14c): PASS
- `test_migration_both_old_and_new_exist_safe_refusal` (14d): PASS
- `test_migration_is_idempotent` (14e): PASS
- `test_migration_occurs_before_outbox_initialization` (14f): PASS
- `test_development_mode_does_not_migrate_production_data` (14g): PASS
- `test_migration_fails_safely_when_old_db_locked_in_use`: PASS

### Complete Regression Results
- **Phase 9 Test Suite**: 25 passed, 0 failed
- **Client Agent Test Suite**: 263 passed (238 baseline + 25 Phase 9), 0 failed
- **Backend Test Suite**: 23 passed, 0 failed
- **Total Test Cases**: 286 passed, 0 failed
- **Alembic Database State**: `a1b2c3d4e5f6` (Head, 0 migrations)
- **Compileall**: 0 errors
- **Git Diff Check**: 0 whitespace / conflict issues
- **Static Checker (Pyright)**: 0 errors across all modified Phase 9 files
