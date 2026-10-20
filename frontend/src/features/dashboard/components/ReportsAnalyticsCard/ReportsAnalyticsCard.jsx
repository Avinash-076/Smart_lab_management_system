import "./ReportsAnalyticsCard.css";

export default function ReportsAnalyticsCard({ onNavigate }) {
  const tiles = [
    {
      id: "performance",
      label: "Performance Report",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
          <line x1="18" y1="20" x2="18" y2="10" />
          <line x1="12" y1="20" x2="12" y2="4" />
          <line x1="6" y1="20" x2="6" y2="14" />
        </svg>
      ),
      action: () => onNavigate?.("reports"),
    },
    {
      id: "health",
      label: "System Health Report",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
      ),
      action: () => onNavigate?.("reports"),
    },
    {
      id: "software",
      label: "Software Inventory",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
          <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
          <line x1="12" y1="22.08" x2="12" y2="12" />
        </svg>
      ),
      action: () => onNavigate?.("software"),
    },
    {
      id: "activity",
      label: "Activity Report",
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      ),
      action: () => onNavigate?.("audit"),
    },
  ];

  return (
    <div className="reports-analytics-card" data-testid="reports-analytics-card">
      {/* Header */}
      <div className="reports-analytics-header">
        <div className="reports-analytics-title-group">
          <div className="reports-analytics-badge-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
          </div>
          <h3 className="reports-analytics-title">Reports &amp; Analytics</h3>
        </div>
      </div>

      {/* 2x2 Action Tiles */}
      <div className="reports-analytics-grid">
        {tiles.map((t) => (
          <button
            key={t.id}
            type="button"
            className="reports-tile-btn"
            onClick={t.action}
            title={`Open ${t.label}`}
          >
            <div className="reports-tile-icon-wrap">{t.icon}</div>
            <span className="reports-tile-label">{t.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
