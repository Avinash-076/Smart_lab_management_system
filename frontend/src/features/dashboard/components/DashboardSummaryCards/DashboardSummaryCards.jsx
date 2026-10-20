import "./DashboardSummaryCards.css";

function Sparkline({ color = "#3b82f6" }) {
  // 6 subtle vertical bars representing sparkline activity
  const heights = [35, 55, 45, 75, 60, 90];
  return (
    <div className="dashboard-summary-sparkline" aria-hidden="true">
      {heights.map((h, i) => (
        <span
          key={i}
          className="dashboard-spark-bar"
          style={{
            height: `${h}%`,
            backgroundColor: color,
            opacity: 0.35 + (i / heights.length) * 0.65,
          }}
        />
      ))}
    </div>
  );
}

export default function DashboardSummaryCards({
  totalComputers = 0,
  onlineComputers = 0,
  offlineComputers = 0,
  highRamCount = 0,
  lowDiskCount = 0,
  activeAlertsCount = 0,
}) {
  const onlinePct =
    totalComputers > 0
      ? ((onlineComputers / totalComputers) * 100).toFixed(1)
      : "0.0";
  const offlinePct =
    totalComputers > 0
      ? ((offlineComputers / totalComputers) * 100).toFixed(1)
      : "0.0";

  const cards = [
    {
      id: "total",
      label: "Total Computers",
      value: totalComputers,
      subtitle: "All systems in lab",
      accent: "#2563eb",
      bgLight: "#eff6ff",
      sparkColor: "#3b82f6",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
      ),
    },
    {
      id: "online",
      label: "Online Computers",
      value: onlineComputers,
      subtitle: `${onlinePct}% online`,
      accent: "#10b981",
      bgLight: "#ecfdf5",
      sparkColor: "#10b981",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      ),
    },
    {
      id: "offline",
      label: "Offline Computers",
      value: offlineComputers,
      subtitle: `${offlinePct}% offline`,
      accent: "#ef4444",
      bgLight: "#fef2f2",
      sparkColor: "#ef4444",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
          <line x1="12" y1="7" x2="12" y2="10" strokeWidth="2.5" />
          <circle cx="12" cy="13" r="0.75" fill="currentColor" />
        </svg>
      ),
    },
    {
      id: "ram",
      label: "High RAM Systems",
      value: highRamCount,
      subtitle: "> 85% RAM usage",
      accent: "#f97316",
      bgLight: "#fff7ed",
      sparkColor: "#f97316",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
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
      ),
    },
    {
      id: "disk",
      label: "Low Disk Systems",
      value: lowDiskCount,
      subtitle: "< 10% disk space",
      accent: "#8b5cf6",
      bgLight: "#f5f3ff",
      sparkColor: "#8b5cf6",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <ellipse cx="12" cy="5" rx="9" ry="3" />
          <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
          <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        </svg>
      ),
    },
    {
      id: "alerts",
      label: "Active Alerts",
      value: activeAlertsCount,
      subtitle: "Needs attention",
      accent: "#f59e0b",
      bgLight: "#fffbeb",
      sparkColor: "#f59e0b",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
      ),
    },
  ];

  return (
    <div className="dashboard-summary-grid" data-testid="dashboard-summary-cards">
      {cards.map((card) => (
        <div key={card.id} className="dashboard-summary-card">
          <div className="dashboard-summary-card-top">
            <div
              className="dashboard-summary-icon"
              style={{ backgroundColor: card.bgLight, color: card.accent }}
            >
              {card.icon}
            </div>
          </div>

          <div className="dashboard-summary-body">
            <span className="dashboard-summary-label">{card.label}</span>
            <div className="dashboard-summary-row">
              <span className="dashboard-summary-value">{card.value}</span>
              <Sparkline color={card.sparkColor} />
            </div>
            <span className="dashboard-summary-subtitle">{card.subtitle}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
