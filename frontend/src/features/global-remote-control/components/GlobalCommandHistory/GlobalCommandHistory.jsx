import { useState } from "react";
import Icon from "../../../../components/ui/Icon";
import { parseApiDate } from "../../../computers/utils/computerUtils";
import GlobalCommandDetailModal from "./GlobalCommandDetailModal";
import "./GlobalCommandHistory.css";

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
      <span className="dot blue" /> Pending
    </span>
  );
}

export default function GlobalCommandHistory({
  commands = [],
  totalCount = 0,
  page = 1,
  pageSize = 10,
  onPageChange,
  filters = {},
  onFilterChange,
  onExportCsv,
  loading = false,
  isExporting = false,
}) {
  const [selectedCommand, setSelectedCommand] = useState(null);

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  return (
    <div className="global-history-card" data-testid="global-history-section">
      {/* Header and Filter Controls */}
      <div className="history-header">
        <div className="history-header-left">
          <div className="history-header-icon">
            <Icon name="history" size={20} />
          </div>
          <div>
            <h2 className="history-title">Global Command History</h2>
            <p className="history-sub">
              View and filter command history across all computers
            </p>
          </div>
        </div>

        <div className="history-header-right">
          {/* Date range filter */}
          <select
            className="history-filter-select"
            value={filters.dateRange || "last_7_days"}
            onChange={(e) => onFilterChange({ ...filters, dateRange: e.target.value })}
            aria-label="Filter by date range"
          >
            <option value="today">Today</option>
            <option value="last_24_hours">Last 24 hours</option>
            <option value="last_7_days">Last 7 days</option>
            <option value="last_30_days">Last 30 days</option>
            <option value="all">All time</option>
          </select>

          {/* Command type filter */}
          <select
            className="history-filter-select"
            value={filters.commandType || "all"}
            onChange={(e) => onFilterChange({ ...filters, commandType: e.target.value })}
            aria-label="Filter by command type"
          >
            <option value="all">All Commands</option>
            <option value="message">Send Message</option>
            <option value="lock">Lock Workstation</option>
            <option value="restart">Restart Computer</option>
            <option value="shutdown">Shutdown Computer</option>
          </select>

          {/* Status filter */}
          <select
            className="history-filter-select"
            value={filters.status || "all"}
            onChange={(e) => onFilterChange({ ...filters, status: e.target.value })}
            aria-label="Filter by status"
          >
            <option value="all">All Status</option>
            <option value="executed">Success</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>

          {/* Search box */}
          <div className="history-search-box">
            <Icon name="search" size={14} />
            <input
              type="text"
              placeholder="Search..."
              value={filters.search || ""}
              onChange={(e) => onFilterChange({ ...filters, search: e.target.value })}
              aria-label="Search command history"
            />
          </div>

          {/* Export CSV Button */}
          <button
            type="button"
            className="export-csv-btn"
            onClick={onExportCsv}
            disabled={isExporting}
            aria-label="Export history to CSV"
          >
            <Icon name="download" size={15} />
            <span>{isExporting ? "Exporting..." : "Export CSV"}</span>
          </button>
        </div>
      </div>

      {/* History Table */}
      <div className="history-table-responsive">
        <table className="history-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Time</th>
              <th>Command</th>
              <th>Target Computer</th>
              <th>Issued By</th>
              <th>Status</th>
              <th>Duration</th>
              <th>Result</th>
              <th className="th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={9} className="history-empty-cell">
                  Loading command history...
                </td>
              </tr>
            ) : commands.length === 0 ? (
              <tr>
                <td colSpan={9} className="history-empty-cell">
                  No commands match your filter criteria.
                </td>
              </tr>
            ) : (
              commands.map((cmd) => {
                const meta = getCommandMeta(cmd.command_type);
                const targetName =
                  cmd.computer_hostname ||
                  (cmd.computer_id ? `PC-${cmd.computer_id}` : "Unknown");
                const issuedBy =
                  cmd.issued_by_username ||
                  (cmd.issued_by ? `User #${cmd.issued_by}` : "Admin User");
                const duration =
                  cmd.duration_seconds !== null && cmd.duration_seconds !== undefined
                    ? `${cmd.duration_seconds.toFixed(1)}s`
                    : "—";

                const resultSummary =
                  cmd.result?.message ||
                  (cmd.status === "executed"
                    ? "Command executed"
                    : cmd.status === "failed"
                    ? "Failed to execute"
                    : "Command sent");

                return (
                  <tr key={cmd.id}>
                    <td className="td-mono td-id">#{cmd.id}</td>
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
                    <td className="td-issuer">{issuedBy}</td>
                    <td>{getStatusBadge(cmd.status, cmd.result)}</td>
                    <td className="td-duration">{duration}</td>
                    <td className="td-result" title={resultSummary}>
                      {resultSummary}
                    </td>
                    <td className="td-actions">
                      <button
                        type="button"
                        className="history-action-btn"
                        onClick={() => setSelectedCommand(cmd)}
                        title="View details"
                        aria-label={`View details for command #${cmd.id}`}
                      >
                        <Icon name="eye" size={15} />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="history-footer">
        <div className="history-footer-info">
          Showing {totalCount > 0 ? (page - 1) * pageSize + 1 : 0} to{" "}
          {Math.min(page * pageSize, totalCount)} of {totalCount} commands
        </div>

        <div className="pagination-buttons">
          <button
            type="button"
            className="page-btn prev"
            disabled={page <= 1 || loading}
            onClick={() => onPageChange(page - 1)}
            aria-label="Previous page"
          >
            &lt;
          </button>

          {Array.from({ length: totalPages }, (_, idx) => idx + 1).map((p) => {
            if (
              totalPages > 7 &&
              p > 2 &&
              p < totalPages - 1 &&
              Math.abs(p - page) > 1
            ) {
              if (p === 3 || p === totalPages - 2) {
                return (
                  <span key={p} className="page-ellipsis">
                    ...
                  </span>
                );
              }
              return null;
            }

            return (
              <button
                key={p}
                type="button"
                className={`page-btn ${p === page ? "active" : ""}`}
                onClick={() => onPageChange(p)}
                disabled={loading}
              >
                {p}
              </button>
            );
          })}

          <button
            type="button"
            className="page-btn next"
            disabled={page >= totalPages || loading}
            onClick={() => onPageChange(page + 1)}
            aria-label="Next page"
          >
            &gt;
          </button>
        </div>
      </div>

      {/* Detail Modal */}
      {selectedCommand && (
        <GlobalCommandDetailModal
          command={selectedCommand}
          onClose={() => setSelectedCommand(null)}
        />
      )}
    </div>
  );
}
