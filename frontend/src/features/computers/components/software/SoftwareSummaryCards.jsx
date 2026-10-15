import Icon from "../../../../components/ui/Icon";
import "./SoftwareSummaryCards.css";

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
    const isYesterday = new Date(now.setDate(now.getDate() - 1)).toDateString() === d.toDateString();
    if (isYesterday) {
      return `Yesterday, ${timeStr}`;
    }
    return `${d.toLocaleDateString([], { month: "short", day: "numeric" })}, ${timeStr}`;
  } catch {
    return timestamp;
  }
}

export default function SoftwareSummaryCards({
  summary,
  loading = false,
  onScanNow,
  scanning = false,
}) {
  const total = summary?.total_installed ?? 0;
  const recentlyInstalled = summary?.recently_installed ?? 0;
  const potentiallyOutdated = summary?.potentially_outdated !== null && summary?.potentially_outdated !== undefined
    ? summary.potentially_outdated
    : null;
  const lastScan = summary?.last_scan;
  const lastScanText = formatScanTime(lastScan);

  return (
    <div className="software-summary-grid">
      {/* 1. Total Installed Applications */}
      <div className="software-metric-card metric-total-apps">
        <div className="software-metric-header">
          <div className="software-metric-icon-box icon-box-blue">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="1.5" />
              <rect x="14" y="3" width="7" height="7" rx="1.5" />
              <rect x="14" y="14" width="7" height="7" rx="1.5" />
              <rect x="3" y="14" width="7" height="7" rx="1.5" />
            </svg>
          </div>
          <div className="software-metric-text-group">
            <span className="software-metric-label">Total Installed Applications</span>
            <span className="software-metric-value">{loading && total === 0 ? "—" : total}</span>
          </div>
        </div>
        <div className="software-metric-footer">
          <span className="software-metric-trend trend-neutral">
            <span className="trend-arrow">↑</span> 0%
          </span>
          <span className="software-metric-subtext">vs previous scan</span>
        </div>
      </div>

      {/* 2. Recently Installed */}
      <div className="software-metric-card metric-recent-apps">
        <div className="software-metric-header">
          <div className="software-metric-icon-box icon-box-green">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="9" />
              <line x1="12" y1="8" x2="12" y2="16" />
              <line x1="8" y1="12" x2="16" y2="12" />
            </svg>
          </div>
          <div className="software-metric-text-group">
            <span className="software-metric-label">Recently Installed <small>(Last 7 days)</small></span>
            <span className="software-metric-value">{loading && recentlyInstalled === 0 ? "—" : recentlyInstalled}</span>
          </div>
        </div>
        <div className="software-metric-footer">
          <span className="software-metric-trend trend-up">
            <span className="trend-arrow">↑</span> {recentlyInstalled > 0 ? `${recentlyInstalled}` : "0"}
          </span>
          <span className="software-metric-subtext">within 7 days</span>
        </div>
      </div>

      {/* 3. Potentially Outdated */}
      <div className="software-metric-card metric-outdated-apps">
        <div className="software-metric-header">
          <div className="software-metric-icon-box icon-box-amber">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <div className="software-metric-text-group">
            <span className="software-metric-label">Potentially Outdated</span>
            <span className="software-metric-value">
              {potentiallyOutdated !== null ? potentiallyOutdated : "—"}
            </span>
          </div>
        </div>
        <div className="software-metric-footer">
          {potentiallyOutdated !== null ? (
            <>
              <span className="software-metric-trend trend-amber">
                <span className="trend-arrow">↑</span> 0%
              </span>
              <span className="software-metric-subtext">vs previous scan</span>
            </>
          ) : (
            <span className="software-metric-subtext subtext-unavailable">Catalog feed unlinked</span>
          )}
        </div>
      </div>

      {/* 4. Last Scan */}
      <div className="software-metric-card metric-last-scan">
        <div className="software-metric-header">
          <div className="software-metric-icon-box icon-box-purple">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          </div>
          <div className="software-metric-text-group">
            <span className="software-metric-label">Last Scan</span>
            <span className="software-metric-value metric-value-scan-time" title={lastScan || ""}>
              {lastScanText}
            </span>
          </div>
        </div>
        <div className="software-metric-footer software-scan-action-row">
          <button
            type="button"
            className="software-scan-now-btn"
            onClick={onScanNow}
            disabled={scanning || loading}
            title="Request immediate software inventory update"
          >
            <Icon type="refresh" size={13} className={scanning ? "software-spin-icon" : ""} />
            <span>{scanning ? "Scanning..." : "Scan Now"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
