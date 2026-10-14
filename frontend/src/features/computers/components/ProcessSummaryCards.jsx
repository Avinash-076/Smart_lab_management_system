import "./ProcessSummaryCards.css";

function formatScanTime(timestamp) {
  if (!timestamp) return "Never";
  try {
    const d = new Date(timestamp);
    if (isNaN(d.getTime())) return timestamp;
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    const timeStr = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (isToday) {
      return `Today, ${timeStr}`;
    }
    const yesterday = new Date(now);
    yesterday.setDate(now.getDate() - 1);
    const isYesterday = yesterday.toDateString() === d.toDateString();
    if (isYesterday) {
      return `Yesterday, ${timeStr}`;
    }
    return `${d.toLocaleDateString([], { month: "short", day: "numeric" })}, ${timeStr}`;
  } catch {
    return timestamp;
  }
}

export default function ProcessSummaryCards({
  summary,
  loading = false,
  onScanNow = null,
  scanning = false,
}) {
  const totalRunning = summary?.total_running ?? 0;
  const cpuPercent =
    summary?.total_cpu_percent !== undefined && summary?.total_cpu_percent !== null
      ? summary.total_cpu_percent
      : null;

  const totalMemMb = summary?.total_memory_mb ?? 0;
  const totalMemPct = summary?.total_memory_percent ?? 0;
  const memDisplay =
    summary && totalMemMb > 0
      ? totalMemMb >= 1024
        ? `${(totalMemMb / 1024.0).toFixed(1)} GB (${Math.round(totalMemPct)}%)`
        : `${Math.round(totalMemMb)} MB (${Math.round(totalMemPct)}%)`
      : loading
      ? "—"
      : "0 MB (0%)";

  const lastScan = summary?.last_scan;
  const lastScanText = formatScanTime(lastScan);

  return (
    <div className="process-summary-grid">
      {/* 1. Running Processes */}
      <div className="process-metric-card metric-running-procs">
        <div className="process-metric-header">
          <div className="process-metric-icon-box icon-box-blue">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </div>
          <div className="process-metric-text-group">
            <span className="process-metric-label">Running Processes</span>
            <span className="process-metric-value">
              {loading && totalRunning === 0 ? "—" : totalRunning}
            </span>
          </div>
        </div>
        <div className="process-metric-footer">
          <span className="process-metric-trend trend-positive">
            <span className="trend-arrow">↑</span> 12%
          </span>
          <span className="process-metric-subtext">vs previous scan</span>
        </div>
      </div>

      {/* 2. CPU Usage */}
      <div className="process-metric-card metric-cpu-usage">
        <div className="process-metric-header">
          <div className="process-metric-icon-box icon-box-green">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="4" y="4" width="16" height="16" rx="2" />
              <rect x="9" y="9" width="6" height="6" />
              <line x1="9" y1="1" x2="9" y2="4" />
              <line x1="15" y1="1" x2="15" y2="4" />
              <line x1="9" y1="20" x2="9" y2="23" />
              <line x1="15" y1="20" x2="15" y2="23" />
              <line x1="20" y1="9" x2="23" y2="9" />
              <line x1="20" y1="14" x2="23" y2="14" />
              <line x1="1" y1="9" x2="4" y2="9" />
              <line x1="1" y1="14" x2="4" y2="14" />
            </svg>
          </div>
          <div className="process-metric-text-group">
            <span className="process-metric-label">CPU Usage</span>
            <span className="process-metric-value">
              {loading && cpuPercent === null ? "—" : `${cpuPercent ?? 0}%`}
            </span>
          </div>
        </div>
        <div className="process-metric-footer">
          <span className="process-metric-trend trend-positive">
            <span className="trend-arrow">↓</span> 15%
          </span>
          <span className="process-metric-subtext">vs previous scan</span>
        </div>
      </div>

      {/* 3. Memory Usage */}
      <div className="process-metric-card metric-memory-usage">
        <div className="process-metric-header">
          <div className="process-metric-icon-box icon-box-purple">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="2" y="5" width="20" height="14" rx="2" />
              <line x1="6" y1="9" x2="6" y2="15" />
              <line x1="10" y1="9" x2="10" y2="15" />
              <line x1="14" y1="9" x2="14" y2="15" />
              <line x1="18" y1="9" x2="18" y2="15" />
            </svg>
          </div>
          <div className="process-metric-text-group">
            <span className="process-metric-label">Memory Usage</span>
            <span className="process-metric-value">{memDisplay}</span>
          </div>
        </div>
        <div className="process-metric-footer">
          <span className="process-metric-trend trend-positive">
            <span className="trend-arrow">↓</span> 8%
          </span>
          <span className="process-metric-subtext">vs previous scan</span>
        </div>
      </div>

      {/* 4. Last Scan & Scan Now */}
      <div className="process-metric-card metric-last-scan">
        <div className="process-metric-header">
          <div className="process-metric-icon-box icon-box-amber">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div className="process-metric-text-group">
            <span className="process-metric-label">Last Scan</span>
            <span className="process-metric-value metric-value-scan-time">
              {loading && !lastScan ? "—" : lastScanText}
            </span>
          </div>
        </div>
        <div className="process-metric-footer process-scan-action-row">
          {onScanNow ? (
            <button
              type="button"
              className="process-scan-now-btn"
              onClick={onScanNow}
              disabled={scanning}
              title="Refresh process inventory"
            >
              <svg
                className={`scan-btn-icon ${scanning ? "spin" : ""}`}
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
              </svg>
              <span>{scanning ? "Scanning..." : "Scan Now"}</span>
            </button>
          ) : (
            <span className="process-metric-subtext">Automated background collection</span>
          )}
        </div>
      </div>
    </div>
  );
}
