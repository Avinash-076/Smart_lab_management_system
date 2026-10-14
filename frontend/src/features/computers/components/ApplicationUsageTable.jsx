import "./ApplicationUsageTable.css";

/* Helper SVG App Icons matching the reference design */
function AppIcon({ appName = "", procName = "" }) {
  const name = (appName + " " + procName).toLowerCase();

  if (name.includes("chrome")) {
    return (
      <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" fill="#EA4335" />
        <path d="M12 2a10 10 0 0 1 8.66 5L12 12V2z" fill="#EA4335" />
        <path d="M20.66 7A10 10 0 0 1 12 22l4.33-7.5 4.33-7.5z" fill="#FBBC05" />
        <path d="M12 22A10 10 0 0 1 3.34 7l8.66 5v10z" fill="#34A853" />
        <circle cx="12" cy="12" r="4.5" fill="#FFFFFF" />
        <circle cx="12" cy="12" r="3.5" fill="#4285F4" />
      </svg>
    );
  }

  if (name.includes("code") || name.includes("visual studio")) {
    return (
      <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
        <rect width="24" height="24" rx="5" fill="#007ACC" />
        <path
          d="M17.5 3.5l-8 7.5 8 7.5 2.5-1.5V5l-2.5-1.5zM7.5 7.5l-4 3.5 4 3.5 1.5-1.5-2-2 2-2-1.5-1.5z"
          fill="#FFFFFF"
        />
      </svg>
    );
  }

  if (name.includes("edge") || name.includes("msedge")) {
    return (
      <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="10" fill="#0078D7" />
        <path
          d="M12 4a8 8 0 0 0-8 8c0 4.41 3.59 8 8 8 2.5 0 4.7-1.15 6.13-2.95-.5.15-1.04.25-1.63.25-3.31 0-6-2.69-6-6 0-.8.16-1.55.45-2.24C9.76 9.35 10.82 9.5 12 9.5c2.76 0 5-2.24 5-5 0-.17-.01-.34-.03-.5z"
          fill="#50E6FF"
        />
      </svg>
    );
  }

  if (name.includes("explorer")) {
    return (
      <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
        <path
          d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z"
          fill="#FFA000"
        />
        <path
          d="M20 8H4v10c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V8z"
          fill="#FFCA28"
        />
      </svg>
    );
  }

  if (name.includes("word") || name.includes("winword")) {
    return (
      <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
        <rect width="24" height="24" rx="4" fill="#185ABD" />
        <text
          x="12"
          y="17"
          fill="#FFFFFF"
          fontSize="13"
          fontWeight="bold"
          textAnchor="middle"
          fontFamily="sans-serif"
        >
          W
        </text>
      </svg>
    );
  }

  if (name.includes("powerpnt") || name.includes("powerpoint")) {
    return (
      <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
        <rect width="24" height="24" rx="4" fill="#C43E1C" />
        <text
          x="12"
          y="17"
          fill="#FFFFFF"
          fontSize="13"
          fontWeight="bold"
          textAnchor="middle"
          fontFamily="sans-serif"
        >
          P
        </text>
      </svg>
    );
  }

  if (name.includes("notepad")) {
    return (
      <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
        <rect x="4" y="2" width="16" height="20" rx="3" fill="#0284C7" />
        <line x1="8" y1="7" x2="16" y2="7" stroke="#FFFFFF" strokeWidth="1.5" />
        <line x1="8" y1="11" x2="16" y2="11" stroke="#FFFFFF" strokeWidth="1.5" />
        <line x1="8" y1="15" x2="13" y2="15" stroke="#FFFFFF" strokeWidth="1.5" />
      </svg>
    );
  }

  if (name.includes("terminal") || name.includes("wt.exe") || name.includes("cmd") || name.includes("powershell")) {
    return (
      <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
        <rect width="24" height="24" rx="4" fill="#1E293B" />
        <path
          d="M6 8l4 4-4 4M12 16h6"
          stroke="#4ADE80"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </svg>
    );
  }

  if (name.includes("onedrive")) {
    return (
      <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
        <path
          d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"
          fill="#0078D4"
        />
      </svg>
    );
  }

  if (name.includes("setting")) {
    return (
      <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
        <rect width="24" height="24" rx="5" fill="#475569" />
        <circle cx="12" cy="12" r="3" fill="#FFFFFF" />
        <path
          d="M19.4 13a7.8 7.8 0 0 0 0-2l2.1-1.6a.5.5 0 0 0 .1-.6l-2-3.5a.5.5 0 0 0-.6-.2l-2.5 1a7.9 7.9 0 0 0-1.7-1l-.4-2.6a.5.5 0 0 0-.5-.4h-4a.5.5 0 0 0-.5.4l-.4 2.6a7.9 7.9 0 0 0-1.7 1l-2.5-1a.5.5 0 0 0-.6.2l-2 3.5a.5.5 0 0 0 .1.6L4.6 11a7.8 7.8 0 0 0 0 2l-2.1 1.6a.5.5 0 0 0-.1.6l2 3.5a.5.5 0 0 0 .6.2l2.5-1a7.9 7.9 0 0 0 1.7 1l.4 2.6a.5.5 0 0 0 .5.4h4a.5.5 0 0 0 .5-.4l.4-2.6a7.9 7.9 0 0 0 1.7-1l2.5 1a.5.5 0 0 0 .6-.2l2-3.5a.5.5 0 0 0-.1-.6l-2.1-1.6z"
          fill="#FFFFFF"
        />
      </svg>
    );
  }

  // Fallback Modern App Icon
  return (
    <svg className="app-brand-icon" width="20" height="20" viewBox="0 0 24 24">
      <rect width="24" height="24" rx="5" fill="#E2E8F0" />
      <rect x="5" y="6" width="14" height="12" rx="2" fill="#64748B" />
      <line x1="5" y1="10" x2="19" y2="10" stroke="#FFFFFF" strokeWidth="1" />
      <circle cx="7" cy="8" r="0.75" fill="#EF4444" />
      <circle cx="9" cy="8" r="0.75" fill="#F59E0B" />
      <circle cx="11" cy="8" r="0.75" fill="#10B981" />
    </svg>
  );
}


function formatDateTime(dtStr) {
  if (!dtStr) return "—";
  try {
    const d = new Date(dtStr);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return dtStr;
  }
}

function formatDuration(seconds) {
  if (typeof seconds !== "number" || seconds <= 0) return "—";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m`;
  }
  return `${secs}s`;
}

function ApplicationUsageTable({
  sessions = [],
  totalEntries = 0,
  page = 1,
  pageSize = 10,
  onPageChange,
  isLoading = false,
  error = "",
}) {
  const totalPages = Math.ceil(totalEntries / pageSize) || 1;
  const startEntry = totalEntries === 0 ? 0 : (page - 1) * pageSize + 1;
  const endEntry = Math.min(page * pageSize, totalEntries);

  // Generate page numbers to display: e.g. 1, 2, 3, 4, 5
  const pageNumbers = [];
  const maxButtons = 5;
  let startP = Math.max(1, page - 2);
  let endP = Math.min(totalPages, startP + maxButtons - 1);
  if (endP - startP + 1 < maxButtons) {
    startP = Math.max(1, endP - maxButtons + 1);
  }

  for (let i = startP; i <= endP; i++) {
    pageNumbers.push(i);
  }

  return (
    <div className="history-card usage-table-card">
      <div className="history-card-header">
        <div className="history-card-title-group">
          <div className="history-card-icon-box">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#1877f2"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
          </div>
          <h3 className="history-card-title">Application Usage History</h3>
        </div>
      </div>

      <div className="history-table-wrapper">
        {isLoading ? (
          <div className="history-table-state">
            <div className="history-spinner" />
            <p>Loading application history...</p>
          </div>
        ) : error ? (
          <div className="history-table-state error">
            <p>{error}</p>
          </div>
        ) : sessions.length === 0 ? (
          <div className="history-table-state">
            <p>No application history matching the selected filters.</p>
          </div>
        ) : (
          <table className="usage-data-table">
            <thead>
              <tr>
                <th style={{ width: "40px" }}>#</th>
                <th>Application Name</th>
                <th>Process Name</th>
                <th>User</th>
                <th>Start Time</th>
                <th>End Time</th>
                <th style={{ textAlign: "right" }}>Duration</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session, index) => {
                const rowNum = (page - 1) * pageSize + index + 1;
                const proc = session.process_name || session.application_name || "—";
                const appName = session.application_name || proc;
                const userVal = session.user || "—";
                const isRunning = !session.end_time;

                return (
                  <tr key={session.id || `${session.start_time}-${index}`}>
                    <td className="row-num-cell">{rowNum}</td>
                    <td className="app-name-cell">
                      <div className="app-info-cluster">
                        <AppIcon appName={appName} procName={proc} />
                        <span className="app-title">{appName}</span>
                      </div>
                    </td>
                    <td className="proc-name-cell">
                      <span className="proc-badge">{proc}</span>
                    </td>
                    <td className="user-cell">{userVal}</td>
                    <td className="time-cell">{formatDateTime(session.start_time)}</td>
                    <td className="time-cell">
                      {isRunning ? (
                        <span className="running-tag">Active</span>
                      ) : (
                        formatDateTime(session.end_time)
                      )}
                    </td>
                    <td className="duration-cell" style={{ textAlign: "right" }}>
                      {formatDuration(session.duration_seconds)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Footer */}
      {!isLoading && !error && totalEntries > 0 && (
        <div className="usage-table-footer">
          <div className="entries-count-text">
            Showing {startEntry} to {endEntry} of {totalEntries} entries
          </div>

          <div className="pagination-controls">
            <button
              type="button"
              className="page-nav-btn"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              title="Previous page"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="15 18 9 12 15 6" />
              </svg>
            </button>

            {pageNumbers.map((p) => (
              <button
                key={p}
                type="button"
                className={`page-num-btn ${p === page ? "active" : ""}`}
                onClick={() => onPageChange(p)}
              >
                {p}
              </button>
            ))}

            <button
              type="button"
              className="page-nav-btn"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              title="Next page"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="9 18 15 12 9 6" />
              </svg>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ApplicationUsageTable;
