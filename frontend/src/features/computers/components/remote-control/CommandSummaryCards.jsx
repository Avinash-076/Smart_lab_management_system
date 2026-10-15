import "./CommandSummaryCards.css";

function formatExecutionTime(timestamp) {
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

export default function CommandSummaryCards({
  summary,
  loading = false,
  onRunCommand = null,
}) {
  const total = summary?.total_commands ?? 0;
  const successful = summary?.successful_commands ?? 0;
  const failed = summary?.failed_commands ?? 0;
  const successRate =
    summary?.success_rate_percent ??
    (total > 0 ? Math.round((successful / total) * 100) : 0);
  const failureRate =
    summary?.failure_rate_percent ??
    (total > 0 ? Math.round((failed / total) * 100) : 0);
  const lastExecText = formatExecutionTime(summary?.last_execution_at);

  return (
    <div className="command-summary-grid">
      {/* 1. Total Commands */}
      <div className="command-metric-card metric-total-cmds">
        <div className="command-metric-header">
          <div className="command-metric-icon-box icon-box-blue">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="4 17 10 11 4 5" />
              <line x1="12" y1="19" x2="20" y2="19" />
            </svg>
          </div>
          <div className="command-metric-text-group">
            <span className="command-metric-label">Total Commands</span>
            <span className="command-metric-value">
              {loading && !summary ? "—" : total}
            </span>
          </div>
        </div>
        <div className="command-metric-footer">
          <span className="command-metric-badge badge-green">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
            12%
          </span>
          <span className="command-metric-subtext">vs previous 7 days</span>
        </div>
      </div>

      {/* 2. Successful */}
      <div className="command-metric-card metric-successful-cmds">
        <div className="command-metric-header">
          <div className="command-metric-icon-box icon-box-green">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <div className="command-metric-text-group">
            <span className="command-metric-label">Successful</span>
            <span className="command-metric-value">
              {loading && !summary ? (
                "—"
              ) : (
                <>
                  {successful}
                  <span className="command-metric-unit">
                    {total > 0 ? ` (${Math.round(successRate)}%)` : " (0%)"}
                  </span>
                </>
              )}
            </span>
          </div>
        </div>
        <div className="command-metric-footer">
          <span className="command-metric-badge badge-green">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="19" x2="12" y2="5" />
              <polyline points="5 12 12 5 19 12" />
            </svg>
            15%
          </span>
          <span className="command-metric-subtext">vs previous 7 days</span>
        </div>
      </div>

      {/* 3. Failed */}
      <div className="command-metric-card metric-failed-cmds">
        <div className="command-metric-header">
          <div className="command-metric-icon-box icon-box-red">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </div>
          <div className="command-metric-text-group">
            <span className="command-metric-label">Failed</span>
            <span className="command-metric-value">
              {loading && !summary ? (
                "—"
              ) : (
                <>
                  {failed}
                  <span className="command-metric-unit">
                    {total > 0 ? ` (${Math.round(failureRate)}%)` : " (0%)"}
                  </span>
                </>
              )}
            </span>
          </div>
        </div>
        <div className="command-metric-footer">
          <span className="command-metric-badge badge-red">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="5" x2="12" y2="19" />
              <polyline points="19 12 12 19 5 12" />
            </svg>
            20%
          </span>
          <span className="command-metric-subtext">vs previous 7 days</span>
        </div>
      </div>

      {/* 4. Last Execution */}
      <div className="command-metric-card metric-last-exec">
        <div className="command-metric-header">
          <div className="command-metric-icon-box icon-box-orange">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div className="command-metric-text-group">
            <span className="command-metric-label">Last Execution</span>
            <span className="command-metric-value command-metric-value-time">
              {loading && !summary ? "—" : lastExecText}
            </span>
          </div>
        </div>
        <div className="command-metric-action">
          <button
            type="button"
            className="command-run-btn"
            onClick={onRunCommand}
            title="Focus command execution section"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            Run Command
          </button>
        </div>
      </div>
    </div>
  );
}
