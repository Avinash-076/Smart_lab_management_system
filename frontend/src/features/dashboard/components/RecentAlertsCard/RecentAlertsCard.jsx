import "./RecentAlertsCard.css";

function formatAlertTime(dateStr) {
  if (!dateStr) return "Just now";
  try {
    const d = new Date(dateStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return dateStr;
  }
}

export default function RecentAlertsCard({
  alerts = [],
  onViewAll,
}) {
  return (
    <div className="recent-alerts-card" data-testid="recent-alerts-card">
      {/* Header */}
      <div className="recent-alerts-header">
        <div className="recent-alerts-title-group">
          <div className="recent-alerts-badge-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
          </div>
          <h3 className="recent-alerts-title">Recent Alerts</h3>
        </div>
        <button
          type="button"
          className="recent-alerts-view-all"
          onClick={onViewAll}
        >
          View All
        </button>
      </div>

      {/* Alerts List */}
      <div className="recent-alerts-list">
        {alerts.length > 0 ? (
          alerts.slice(0, 5).map((item) => {
            const hostname =
              item.computer_hostname ||
              (item.computer_id ? `PC-${item.computer_id}` : "SYSTEM");
            const isCritical =
              item.severity === "critical" || (item.category || "").includes("critical");
            const isWarning =
              item.severity === "warning" || (item.category || "").includes("disk");
            const isOffline =
              (item.message || "").toLowerCase().includes("offline") ||
              (item.category || "").toLowerCase().includes("status");

            let badgeClass = "badge-blue";
            let iconSvg = (
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
            );

            if (isOffline) {
              badgeClass = "badge-red";
              iconSvg = (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="15" y1="9" x2="9" y2="15" />
                  <line x1="9" y1="9" x2="15" y2="15" />
                </svg>
              );
            } else if (isCritical) {
              badgeClass = "badge-red";
              iconSvg = (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <line x1="8" y1="21" x2="16" y2="21" />
                  <line x1="12" y1="17" x2="12" y2="21" />
                </svg>
              );
            } else if (isWarning) {
              badgeClass = "badge-orange";
              iconSvg = (
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              );
            }

            return (
              <div key={item.id} className="recent-alert-item">
                <div className={`recent-alert-icon-wrap ${badgeClass}`}>
                  {iconSvg}
                </div>
                <div className="recent-alert-info">
                  <span className="recent-alert-name" title={`${hostname} - ${item.message || "Alert"}`}>
                    {hostname} - {item.category ? `${item.category.toUpperCase()} Alert` : "Alert"}
                  </span>
                  <span className="recent-alert-desc" title={item.message}>
                    {item.message || "System activity recorded"}
                  </span>
                </div>
                <span className="recent-alert-time">
                  {formatAlertTime(item.created_at)}
                </span>
              </div>
            );
          })
        ) : (
          <div className="recent-alerts-empty">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="1.5">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <span>All systems healthy</span>
            <small>No recent active alerts recorded</small>
          </div>
        )}
      </div>
    </div>
  );
}
