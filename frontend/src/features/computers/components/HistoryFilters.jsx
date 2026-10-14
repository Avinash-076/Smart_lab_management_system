import "./HistoryFilters.css";

function formatPresetLabel(preset) {
  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  switch (preset) {
    case "today":
      return `Today (${dateStr})`;
    case "yesterday":
      return "Yesterday";
    case "7d":
      return "Last 7 Days";
    case "30d":
      return "Last 30 Days";
    case "all":
      return "All Time";
    case "custom":
      return "Custom Range";
    default:
      return "Today";
  }
}

function HistoryFilters({
  timeRange,
  setTimeRange,
  selectedUser,
  setSelectedUser,
  selectedApp,
  setSelectedApp,
  customStart,
  setCustomStart,
  customEnd,
  setCustomEnd,
  availableUsers = [],
  availableApps = [],
  onApply,
  onExport,
  isExporting = false,
  isLoading = false,
}) {

  return (
    <div className="history-filters-toolbar">
      <div className="history-filters-left">
        {/* Time Range Filter */}
        <div className="history-filter-item">
          <label className="history-filter-label" htmlFor="history-time-range">
            Time Range
          </label>
          <div className="history-select-wrapper">
            <svg
              className="history-filter-icon"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#64748b"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <select
              id="history-time-range"
              className="history-select"
              value={timeRange}
              onChange={(e) => setTimeRange(e.target.value)}
              disabled={isLoading}
            >
              <option value="today">{formatPresetLabel("today")}</option>
              <option value="yesterday">Yesterday</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="all">All Time</option>
              <option value="custom">Custom Range</option>
            </select>
            <svg
              className="history-select-chevron"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#64748b"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>

        {/* Custom Date Pickers (only shown if timeRange === 'custom') */}
        {timeRange === "custom" && (
          <div className="history-filter-item custom-date-group">
            <label className="history-filter-label">Custom Dates</label>
            <div className="custom-date-inputs">
              <input
                type="date"
                className="history-date-input"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                title="Start Date"
              />
              <span className="custom-date-sep">to</span>
              <input
                type="date"
                className="history-date-input"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                title="End Date"
              />
            </div>
          </div>
        )}

        {/* User Filter */}
        <div className="history-filter-item">
          <label className="history-filter-label" htmlFor="history-user-filter">
            User
          </label>
          <div className="history-select-wrapper">
            <select
              id="history-user-filter"
              className="history-select"
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              disabled={isLoading}
            >
              <option value="all">All Users</option>
              {availableUsers.map((u) => (
                <option key={u} value={u}>
                  {u}
                </option>
              ))}
            </select>
            <svg
              className="history-select-chevron"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#64748b"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>

        {/* Application Filter */}
        <div className="history-filter-item">
          <label className="history-filter-label" htmlFor="history-app-filter">
            Application
          </label>
          <div className="history-select-wrapper">
            <select
              id="history-app-filter"
              className="history-select"
              value={selectedApp}
              onChange={(e) => setSelectedApp(e.target.value)}
              disabled={isLoading}
            >
              <option value="all">All Applications</option>
              {availableApps.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
            <svg
              className="history-select-chevron"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#64748b"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>
        </div>

        {/* Apply Button */}
        <div className="history-filter-item apply-btn-container">
          <label className="history-filter-label" style={{ visibility: "hidden" }}>
            Action
          </label>
          <button
            type="button"
            className="history-apply-btn"
            onClick={onApply}
            disabled={isLoading}
          >
            Apply
          </button>
        </div>
      </div>

      {/* Export Button */}
      <div className="history-filters-right">
        <div className="history-export-wrapper">
          <button
            type="button"
            className="history-export-btn"
            onClick={() => onExport("csv")}
            disabled={isExporting}
            title="Export application history as CSV"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            <span>{isExporting ? "Exporting..." : "Export"}</span>
            <svg
              className="export-chevron"
              width="13"
              height="13"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
export default HistoryFilters;
