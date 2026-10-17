import { parseApiDate } from "../../utils/computerUtils";
import "./RecentCommandActivity.css";

function formatActivityTitle(cmd) {
  const type = cmd.command_type?.toLowerCase();
  const isFailed = cmd.status === "failed" || (cmd.result && !cmd.result.success);
  const isSuccess = !isFailed && (cmd.status === "executed" || cmd.result?.success);

  if (type === "message") {
    return isSuccess
      ? "Message command executed"
      : isFailed
      ? "Message command failed"
      : "Message command dispatched";
  }
  if (type === "lock") {
    return isSuccess
      ? "Lock command executed"
      : isFailed
      ? "Lock command failed"
      : "Lock command dispatched";
  }
  if (type === "restart") {
    return isSuccess
      ? "System restarted"
      : isFailed
      ? "Restart command failed"
      : "System restart scheduled";
  }
  if (type === "shutdown") {
    return isSuccess
      ? "System shut down"
      : isFailed
      ? "Shutdown command executed" // or failed
      : "System shutdown scheduled";
  }
  return `${cmd.command_type || "Command"} executed`;
}

function formatActivityTime(timestamp) {
  if (!timestamp) return "—";
  try {
    const d = parseApiDate(timestamp) || new Date(timestamp);
    if (!d || isNaN(d.getTime())) return timestamp;
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

export default function RecentCommandActivity({
  activities = [],
  loading = false,
  onSelectActivity = null,
}) {
  return (
    <div className="recent-activity-card">
      <div className="recent-activity-header">
        <div className="recent-activity-icon">
          <svg
            width="18"
            height="18"
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
        <h3 className="recent-activity-title">Recent Activity (Last 24 Hours)</h3>
      </div>

      <div className="recent-activity-body">
        {loading && activities.length === 0 ? (
          <div className="recent-activity-empty">
            <span className="activity-spinner" />
            <p>Loading recent activity...</p>
          </div>
        ) : activities.length === 0 ? (
          <div className="recent-activity-empty">
            <p>No command activity recorded in the last 24 hours.</p>
          </div>
        ) : (
          <ul className="activity-list">
            {activities.slice(0, 5).map((act) => {
              const isFailed = act.status === "failed" || (act.result && !act.result.success);
              const isSuccess = !isFailed && (act.status === "executed" || act.result?.success);
              const isDelivered = act.status === "delivered";
              const isPending = act.status === "pending";

              const statusClass = isSuccess
                ? "success"
                : isFailed
                ? "failed"
                : isDelivered
                ? "delivered"
                : isPending
                ? "pending"
                : "cancelled";

              const statusLabel = isSuccess
                ? "Success"
                : isFailed
                ? "Failed"
                : isDelivered
                ? "Delivered"
                : isPending
                ? "Pending"
                : "Cancelled";

              const timeDisplay = formatActivityTime(
                act.result?.completed_at || act.created_at
              );

              return (
                <li
                  key={act.id}
                  className="activity-item"
                  onClick={() => onSelectActivity && onSelectActivity(act)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="activity-left">
                    <span className={`activity-status-dot dot-${statusClass}`} />
                    <div className="activity-details">
                      <span className="activity-name">{formatActivityTitle(act)}</span>
                      <span className="activity-time">{timeDisplay}</span>
                    </div>
                  </div>

                  <span className={`activity-pill pill-${statusClass}`}>
                    {statusLabel}
                  </span>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
