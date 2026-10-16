import Icon from "../../../../components/ui/Icon";
import { parseApiDate } from "../../../computers/utils/computerUtils";
import "./ExecutionMonitor.css";

function formatTimestamp(ts) {
  if (!ts) return "—";
  try {
    const d = parseApiDate(ts) || new Date(ts);
    if (!d || isNaN(d.getTime())) return ts;
    return d.toLocaleString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

function getCommandMeta(type) {
  switch (type?.toLowerCase()) {
    case "message":
      return { label: "Send Message", icon: "message", color: "blue" };
    case "lock":
      return { label: "Lock Workstation", icon: "lock", color: "amber" };
    case "restart":
      return { label: "Restart Computer", icon: "restart", color: "red" };
    case "shutdown":
      return { label: "Shutdown Computer", icon: "shutdown", color: "purple" };
    default:
      return { label: type || "Command", icon: "play", color: "blue" };
  }
}

function getStatusBadge(status, result) {
  const s = status?.toLowerCase();
  const isSuccess = s === "executed" || s === "success" || result?.success === true;
  const isFailed = s === "failed" || (result && result.success === false);
  const isCancelled = s === "cancelled";

  if (isSuccess) {
    return (
      <span className="status-badge success">
        <span className="dot green" /> Success
      </span>
    );
  }
  if (isFailed) {
    return (
      <span className="status-badge failed">
        <span className="dot red" /> Failed
      </span>
    );
  }
  if (isCancelled) {
    return (
      <span className="status-badge cancelled">
        <span className="dot gray" /> Cancelled
      </span>
    );
  }
  return (
    <span className="status-badge pending">
      <span className="dot blue" /> {s === "delivered" ? "Delivered" : "Pending"}
    </span>
  );
}

export default function ExecutionMonitor({
  commands = [],
  loading = false,
  autoRefresh = true,
  onToggleAutoRefresh,
  onViewDetails,
  onNavigateToComputer,
}) {
  return (
    <div className="execution-monitor-card" data-testid="execution-monitor-section">
      {/* Card Header */}
      <div className="monitor-header">
        <div className="monitor-header-left">
          <div className="monitor-header-icon">
            <Icon name="list" size={20} />
          </div>
          <div>
            <h2 className="monitor-title">Command Execution Monitor</h2>
            <p className="monitor-sub">
              Real-time status of recently executed commands
            </p>
          </div>
        </div>

        <div className="monitor-header-right">
          <label className="auto-refresh-toggle">
            <span className="auto-refresh-label">Auto refresh (10s)</span>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => onToggleAutoRefresh(e.target.checked)}
              aria-label="Toggle auto refresh"
            />
            <span className="toggle-slider" />
          </label>
        </div>
      </div>

      {/* Table */}
      <div className="monitor-table-responsive">
        <table className="monitor-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Command</th>
              <th>Target Computer</th>
              <th>Status</th>
              <th>Message</th>
              <th>Duration</th>
              <th className="th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && commands.length === 0 ? (
              <tr>
                <td colSpan={7} className="monitor-empty-cell">
                  Loading recent executions...
                </td>
              </tr>
            ) : commands.length === 0 ? (
              <tr>
                <td colSpan={7} className="monitor-empty-cell">
                  No recent command executions found.
                </td>
              </tr>
            ) : (
              commands.map((cmd) => {
                const meta = getCommandMeta(cmd.command_type);
                const targetName =
                  cmd.computer_hostname ||
                  (cmd.computer_id ? `PC-${cmd.computer_id}` : "Unknown");
                const duration =
                  cmd.duration_seconds !== null && cmd.duration_seconds !== undefined
                    ? `${cmd.duration_seconds.toFixed(1)}s`
                    : "—";

                const messageText =
                  cmd.result?.message ||
                  cmd.result?.error ||
                  (cmd.status === "failed" ? "Execution failed" : "Command sent, waiting for execution");

                return (
                  <tr key={cmd.id}>
                    <td className="td-time">{formatTimestamp(cmd.created_at)}</td>
                    <td>
                      <div className="cmd-type-cell">
                        <span className={`cmd-type-icon ${meta.color}`}>
                          <Icon name={meta.icon} size={15} />
                        </span>
                        <span className="cmd-type-label">{meta.label}</span>
                      </div>
                    </td>
                    <td className="td-target">
                      <strong>{targetName}</strong>
                    </td>
                    <td>{getStatusBadge(cmd.status, cmd.result)}</td>
                    <td className="td-message" title={messageText}>
                      {messageText}
                    </td>
                    <td className="td-duration">{duration}</td>
                    <td className="td-actions">
                      <button
                        type="button"
                        className="monitor-action-btn"
                        onClick={() => onViewDetails(cmd)}
                        title="View command details"
                        aria-label={`View details for command #${cmd.id}`}
                      >
                        <Icon name="eye" size={15} />
                      </button>
                      {cmd.computer_id && (
                        <button
                          type="button"
                          className="monitor-action-btn"
                          onClick={() => onNavigateToComputer(cmd.computer_id)}
                          title="Navigate to computer"
                          aria-label={`Go to computer ${targetName}`}
                        >
                          <Icon name="external-link" size={15} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
