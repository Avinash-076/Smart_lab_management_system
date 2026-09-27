# Phase 4 Implementation Report: Collector Correctness

## 1. Objective
The objective of Phase 4 is to make the SLMS Client Agent collectors data-correct and restart-safe. Prior to this phase, collector failures were silently converted to misleading zero values, CPU collection blocked the monitoring thread for one full second, network identity resolution was duplicated and prone to selecting virtual or mismatched adapters, software scanning suffered from a cache-invalidation bug on empty inventories, and application usage tracking was vulnerable to PID reuse collisions, lost state on restarts, and false-stop events on transient process query glitches.

This implementation resolves problems D-01 through D-12 without redesigning the runtime, WebSocket, or durable outbox architectures, and without starting any Phase 5+ work.

---

## 2. Problems Addressed

| Item | Problem Code | Description | Resolution |
| :--- | :--- | :--- | :--- |
| **D-01** | CONFIRMED DEFECT | Collection failure becomes zero | Structured `CollectionResult` and `CollectorError` prevent failure masking; `build_metric_payload` and upload helpers reject failed hardware data rather than reporting fabricated 0% metrics. |
| **D-02** | ARCHITECTURAL GAP | Collector errors lose structured context | `safe_run` captures structured context: collector name, operation, exception type, error message, and timestamp without exposing secrets. |
| **D-03** | CONFIRMED DEFECT | Network identity can be wrong | Consolidated canonical identity resolver in `modules/network.py` inspects interface status (UP), filters loopbacks, rejects APIPA (169.254.x.x), and prioritizes physical adapters over virtual. |
| **D-04** | CONFIRMED DEFECT | Network identity logic duplicated | Duplicated IP and MAC resolution logic removed from `system_info.py`; all modules delegate to `modules/network.py::get_canonical_network_identity`. |
| **D-05** | CONFIRMED DEFECT | MAC address may identify wrong adapter | Eliminated independent `uuid.getnode()` calls. MAC address is extracted from the exact same adapter that provides the chosen IP address. Never fabricates 127.0.0.1 or 00:00:00:00:00:00. |
| **D-06** | NON-NEGOTIABLE CONTRACT | Network byte counters cumulative | Preserved `bytes_sent` and `bytes_received` as cumulative counters from `psutil.net_io_counters()`. No silent conversion to rates. |
| **D-07** | CONFIRMED DEFECT | Software cache empty-result bug | `SoftwareCache` with explicit state distinguishes valid empty inventory (`[]`) from cache missing, expired, corrupted, or failed. Valid empty inventory is reused until TTL expires. |
| **D-08** | CONFIRMED DEFECT | CPU collection blocks for 1 second | Replaced blocking `psutil.cpu_percent(interval=1)` with non-blocking sampling `psutil.cpu_percent(interval=None)`. Primed at module import; execution time dropped from >1.0s to <0.01s. |
| **D-09** | CONFIRMED DEFECT | Usage tracking uses (PID, name) identity | Implemented stable process identity based on `(pid, create_time)` using `psutil.Process.create_time()`. Resolves PID reuse collision defects. |
| **D-10** | CONFIRMED DEFECT | Usage state is memory-only | Active usage tracking sessions are persisted atomically to `%PROGRAMDATA%\SLMS\data\usage_state.json`. Surviving processes resume tracking across restart without resetting session durations or generating stop events. |
| **D-11** | CONFIRMED DEFECT | False usage-stop events on transient drops | Distinguishes confirmed OS termination (`not psutil.pid_exists(pid)`) from transient access or enumeration errors. Applied grace period (`MAX_GRACE_CYCLES=2`) before terminating sessions. Global enumeration drop protects active sessions. |
| **D-12** | PRODUCT POLICY | Usage filtering policy | Excluded obvious OS kernel and idle pseudo-processes (PID <= 4, System Idle Process, System, Registry, Memory Compression) from student application usage tracking. |

---

## 3. Existing Behavior Found
During pre-implementation inspection of the client agent codebase, the following bugs were verified:
1. **Silent Metric Fabrication (`server/sender.py`)**: `build_metric_payload` used `.get("cpu_usage", 0)`, `.get("ram_percent", 0)`, and `.get("bytes_sent", 0)`. If hardware or network collection failed, the agent reported CPU=0%, RAM=0%, and network traffic=0, misleading lab administrators into believing computers were healthy and idle.
2. **Coarse Error Swallowing (`core/health.py`)**: `safe_run()` simply logged `f"{module_name} failed: {e}"` and returned `None`. Callers had no mechanism to inspect the exception type or failure timestamp.
3. **Mismatched Network Identity (`modules/network.py` & `modules/system_info.py`)**: Both modules looped over `psutil.net_if_addrs()` and selected the first non-`127.` IPv4, often picking unplugged adapters with APIPA `169.254.x.x` addresses. Both called `uuid.getnode()` independently, resulting in MAC addresses from virtual adapters (e.g. Hyper-V `vEthernet`) paired with IP addresses from completely different interfaces.
4. **Blocking CPU Sampling (`modules/hardware.py`)**: `psutil.cpu_percent(interval=1)` halted the entire agent monitoring thread for 1,000 milliseconds every 20-second cycle.
5. **Software Cache Wipe on Empty List (`core/collector.py`)**: The code checked `if _cached_software and now - _last_software_scan < SOFTWARE_SCAN_INTERVAL`. When software scanning returned an empty list (`[]`), `bool([])` evaluated to `False`, forcing an expensive registry rescan every monitoring cycle (every 20s instead of every 10m).
6. **Usage Session PID Collisions and Volatility (`modules/usage.py`)**: Tracked processes were keyed by `(pid, name.casefold())`. When Windows reassigned a PID to a different process with the same name, sessions merged incorrectly. Furthermore, all active sessions lived only in the global `_ACTIVE_SESSIONS` dictionary; restarting the agent wiped all active sessions, causing lost duration and broken session reporting. Single-cycle query misses immediately emitted termination events.

---

## 4. Files Changed
- `client_agent/core/health.py`: Introduced `CollectionResult` and `CollectorError` abstractions; updated `safe_run()` to return structured results.
- `client_agent/core/collector.py`: Introduced `SoftwareCache` with explicit state tracking to resolve empty-result rescanning (D-07).
- `client_agent/core/exporter.py`: Added default serializer to `json.dump()` to serialize `CollectionResult` instances cleanly.
- `client_agent/core/runtime.py`: Updated upload functions (`upload_metrics`, `upload_software`, `upload_processes`, `upload_usage`, `upload_issues`) and `display_console_data` to unwrap `CollectionResult` and skip uploads on collector failure.
- `client_agent/server/sender.py`: Hardened `build_metric_payload()` and REST senders to reject failed collections, prevent zero fabrication, and support `None` for unavailable network metrics.
- `client_agent/modules/hardware.py`: Implemented non-blocking CPU collection using `psutil.cpu_percent(interval=None)` with module-level initialization (D-08).
- `client_agent/modules/network.py`: Consolidated canonical network identity resolution; eliminated independent `uuid.getnode()`; preserved cumulative network byte counters (D-03, D-04, D-05, D-06).
- `client_agent/modules/system_info.py`: Delegated `get_lan_ip()` and `get_mac_address()` to `modules.network.get_canonical_network_identity()` (D-04).
- `client_agent/modules/usage.py`: Hardened usage tracking with `(PID, create_time)` identity, atomic disk persistence in `DATA_DIR/usage_state.json`, false-stop protection with grace cycles, and exclusion of OS kernel pseudo-processes (D-09, D-10, D-11, D-12).
- `client_agent/main.py`: Updated upload helpers and console display to unwrap `CollectionResult` and skip metric uploads when hardware collector fails.

---

## 5. Files Created
- `client_agent/tests/test_phase4_collectors.py`: 41 comprehensive automated unit and integration tests covering D-01 through D-12.
- `docs/phases/PHASE_4_IMPLEMENTATION.md`: This implementation report.

---

## 6. Files Deleted
No files were deleted in Phase 4.

---

## 7. CollectionResult Design (D-01 + D-02)

### Structure
```python
@dataclass
class CollectorError:
    collector_name: str
    operation: str
    error_type: str
    message: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]: ...

@dataclass
class CollectionResult:
    status: str  # "success", "failed", "empty"
    data: Any = None
    error: Optional[CollectorError] = None
    collected_at: float = field(default_factory=time.time)
```

### Semantics
- **SUCCESS (`status="success"`)**: Valid data collected. Genuine numeric zero (e.g. `0.0%` CPU or `0` bytes sent) is preserved as data with success status.
- **EMPTY (`status="empty"`)**: Valid collection completed with empty payload (e.g. `[]` software or `None` optional metrics). Distinguishable from numeric zero and collection failures.
- **FAILURE (`status="failed"`)**: Data is `None`. `error` contains structured `CollectorError` metadata.
- **Zero Fabrication Prevention**: `build_metric_payload()` raises `ValueError` if hardware collection failed, and `upload_metrics()` logs a warning and returns `False`. The agent will never transmit fabricated 0% metrics to the backend or outbox.

---

## 8. Network Identity Design (D-03 + D-04 + D-05)

### Canonical Resolution
`modules/network.py::get_canonical_network_identity(addrs=None, stats=None)` is the single authoritative source of machine network identity:
1. **Operational Filtering**: Discards interfaces that are DOWN (`stat.isup is False`).
2. **Loopback Exclusion**: Discards loopback interfaces (`127.x.x.x` and loopback naming).
3. **Routable IPv4 Validation**: Validates IPv4 via `ipaddress.IPv4Address`. Discards link-local APIPA (`169.254.x.x`), `0.0.0.0`, and multicast/reserved blocks.
4. **Physical Adapter Prioritization**:
   - Physical Ethernet adapters: +50 score bonus
   - Physical Wi-Fi adapters: +40 score bonus
   - Virtual / Container / VPN adapters (`vEthernet`, `Hyper-V`, `VMware`, `VirtualBox`, `WSL`, `docker`, `tailscale`): -60 penalty
5. **Atomic IP/MAC Pairing**: Extracts the MAC address from the exact same interface entry in `net_if_addrs()`. Normalizes MAC to standard uppercase colon-separated format (`XX:XX:XX:XX:XX:XX`).
6. **No Fake Identity**: If no suitable interface is available, returns `status="failed"` with `ip_address=None` and `mac_address=None`. Never fabricates `127.0.0.1` or `00:00:00:00:00:00`.
7. **De-duplication**: `modules/system_info.py` imports and delegates directly to `get_canonical_network_identity()`.

---

## 9. CPU Sampling Design (D-08)
- Removed `psutil.cpu_percent(interval=1)`.
- Initialized sampling at module import via `psutil.cpu_percent(interval=None)`.
- Subsequent invocations read elapsed CPU times immediately via `psutil.cpu_percent(interval=None)` without blocking the execution thread.
- Execution time of `get_hardware_info()` verified at `< 0.01s` (well below the `< 0.5s` test threshold).

---

## 10. Software Cache Semantics (D-07)
The `SoftwareCache` class manages inventory caching with explicit state:
- `is_present`: `True` if a valid scan result exists (including `[]`).
- `get(now)`: Returns cached list if valid and `now - last_scan_time < ttl`; returns `None` if missing, expired, or corrupted.
- `set(items, now)`: Sets cached items and marks valid. Corrupted input (non-list) causes cache invalidation.
- `invalidate()`: Resets cache to uninitialized state.
- **Failure Resilience**: If `get_installed_software()` raises an exception during rescan, the cache is not overwritten with `[]` or marked valid.

---

## 11. Process Identity Design (D-09)
- Active usage tracking processes are keyed by `(pid: int, create_time: float)`.
- Creation time is obtained from `psutil.Process.create_time()`.
- If a PID is recycled by the OS with a different creation time, the old process is immediately recognized as terminated, and the new process is registered as a distinct session.
- Process renames on the same running process do not trigger false termination or duplicate sessions.

---

## 12. Usage Persistence Design (D-10)
- Active session state is persisted to disk at `paths.DATA_DIR / "usage_state.json"` (under `%PROGRAMDATA%\SLMS\data` in production).
- Writes are performed atomically via temporary file creation and atomic file rename (`os.replace`).
- **Restart Recovery**:
  1. On agent startup, `load_usage_state()` reads persisted sessions.
  2. For each session, queries OS via `psutil.pid_exists(pid)` and verifies `create_time`.
  3. If the process is still running with matching creation time, it resumes active tracking with its original `started_at` timestamp.
  4. If the process is confirmed terminated while the agent was down, it is emitted as a completed session with `ended_at = last_seen_at`.

---

## 13. False-Stop Protection (D-11)
- **Confirmed Termination**: When `not psutil.pid_exists(pid)` is true, the OS has confirmed the process is gone. The session terminates immediately.
- **Grace Periods for Transient Lag**: If a process is absent from `process_iter` but `pid_exists(pid)` is true (e.g. transient query lag or `AccessDenied`), the session increments a `consecutive_misses` counter. The session remains open until `consecutive_misses > MAX_GRACE_CYCLES` (2 cycles).
- **Reappearance**: If a process reappears during the grace window, `consecutive_misses` is reset to 0 and tracking continues uninterrupted.
- **Global Enumeration Drop Protection**: If `process_iter` returns 0 running processes while more than 5 active sessions exist, the cycle is treated as a transient collection glitch; no sessions are closed.

---

## 14. Usage Filtering Policy (D-12)
In accordance with established product requirements, obvious system kernel and idle pseudo-processes are excluded from student application usage tracking:
- `pid <= 4`: PID 0 ("System Idle Process") and PID 4 ("System")
- Known kernel pseudo-process names: `"system idle process"`, `"system"`, `"registry"`, `"memory compression"`
Regular applications (e.g. IDEs, browsers, compilers, editors) continue to be tracked normally.

---

## 15. Compatibility Considerations
- `build_metric_payload` maintains backward compatibility with flat dictionaries while accepting structured `CollectionResult` objects.
- The `SystemMetric` payload schema remains identical: `cpu_usage`, `ram_usage`, `disk_usage`, `network_sent`, `network_received`, `idempotency_key`.
- `network_sent` and `network_received` allow `None` in the backend Pydantic schema (`MetricUpload`), ensuring failed network metrics do not trigger validation errors.
- Outbox integration from Phase 3 is completely preserved; telemetry events, issues, and usage sessions continue flowing through the durable outbox without schema changes.

---

## 16. Tests Added
A dedicated test suite was added in `client_agent/tests/test_phase4_collectors.py` with 41 test cases:
- `TestStructuredResultsD01D02` (7 tests): genuine zeros, empty collections, failure handling, payload rejection, network `None` preservation, dict interface.
- `TestCanonicalNetworkIdentityD03D04D05` (12 tests): MAC normalization, IPv4 validation, loopback exclusion, Ethernet priority, inactive adapter skipping, virtual adapter deprioritization, atomic IP/MAC pairing, failure handling, IPv6-only skipping, missing MAC handling, malformed data, and `system_info` delegation.
- `TestNetworkCountersD06` (2 tests): cumulative counter pass-through and payload preservation.
- `TestSoftwareCacheD07` (6 tests): cached hits, valid empty inventory hits, missing cache rescan, expired cache rescan, corrupted cache healing, and failure isolation.
- `TestNonBlockingCpuCollectionD08` (3 tests): non-blocking execution (<0.5s), sampling priming, and error handling.
- `TestProcessIdentityD09` (3 tests): PID + create_time matching, PID reuse differentiation, and process renaming.
- `TestUsagePersistenceAndRestartRecoveryD10` (2 tests): atomic save/load across restart and offline termination recovery.
- `TestFalseStopProtectionD11` (4 tests): confirmed termination, transient drop grace cycles, global enumeration drop protection, and PID reuse reconciliation.
- `TestUsageFilteringD12` (2 tests): kernel/pseudo-process exclusion and student application inclusion.

---

## 17. Full Regression Result
```
Client Tests:
pytest client_agent/tests -v
Result: 134 passed, 0 failed in 11.83s

Backend Tests:
pytest backend/tests -v
Result: 23 passed, 0 failed in 1.16s

Total Regression Suite: 157 passed, 0 failed.
```

---

## 18. Known Limitations
- Network interface speed bonus depends on `psutil.net_if_stats().speed`. On virtualized network adapters or some wireless drivers, Windows may report `speed=0`, which is handled safely via base priority scoring.
- When an application terminates while the client machine is completely powered off or during abrupt OS crash, the session duration is bounded by the last recorded `last_seen_at` timestamp.
- Process creation time precision depends on the Windows NT kernel timestamp granularity (typically 10-15.6 ms).

---

## 19. Phase 5+ Scope Statement
**Phase 5+ HAS NOT BEEN STARTED.**
No Phase 5 optimizations, advanced process filtering allowlists/denylists, dynamic scheduler redesigns, or Phase 6+ issue management hysteresis have been implemented.
