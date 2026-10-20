import "./QuickActionsCard.css";

export default function QuickActionsCard({
  selectedCount = 0,
  onActionClick,
  onRefreshAll,
  refreshing = false,
}) {
  const actions = [
    {
      id: "restart",
      label: "Restart",
      bg: "#2563eb",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
          <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
        </svg>
      ),
    },
    {
      id: "shutdown",
      label: "Shutdown",
      bg: "#dc2626",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
          <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
          <line x1="12" y1="2" x2="12" y2="12" />
        </svg>
      ),
    },
    {
      id: "lock",
      label: "Lock",
      bg: "#d97706",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      ),
    },
    {
      id: "message",
      label: "Send Message",
      bg: "#16a34a",
      icon: (
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          <line x1="8" y1="9" x2="16" y2="9" />
          <line x1="8" y1="13" x2="14" y2="13" />
        </svg>
      ),
    },
  ];

  return (
    <div className="quick-actions-card" data-testid="quick-actions-card">
      {/* Header */}
      <div className="quick-actions-header">
        <div className="quick-actions-title-group">
          <div className="quick-actions-badge-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </div>
          <h3 className="quick-actions-title">Quick Actions</h3>
        </div>
        {selectedCount > 0 && (
          <span className="quick-actions-selected-pill">
            {`${selectedCount} selected`}
          </span>
        )}
      </div>

      {/* 2x2 Grid of Solid Action Tiles */}
      <div className="quick-actions-grid">
        {actions.map((act) => (
          <button
            key={act.id}
            type="button"
            className="quick-action-tile"
            style={{ backgroundColor: act.bg }}
            onClick={() => onActionClick(act.id)}
            title={`${act.label} selected computer(s)`}
          >
            <span className="quick-action-icon">{act.icon}</span>
            <span className="quick-action-label">{act.label}</span>
          </button>
        ))}
      </div>

      {/* Full Width Button: Refresh All Systems */}
      <button
        type="button"
        className="quick-action-refresh-btn"
        onClick={onRefreshAll}
        disabled={refreshing}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          className={refreshing ? "spin-icon" : ""}
        >
          <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
        </svg>
        {refreshing ? "Refreshing Systems..." : "Refresh All Systems"}
      </button>
    </div>
  );
}
