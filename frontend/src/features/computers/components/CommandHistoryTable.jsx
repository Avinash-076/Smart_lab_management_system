import { useState } from "react";
import "./CommandHistoryTable.css";

function formatTimestamp(ts) {
  if (!ts) return "—";
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  } catch {
    return ts;
  }
}

function getCommandIcon(type) {
  switch (type?.toLowerCase()) {
    case "message":
      return (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      );
    case "lock":
      return (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      );
    case "restart":
      return (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="23 4 23 10 17 10" />
          <polyline points="1 20 1 14 7 14" />
          <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
        </svg>
      );
    case "shutdown":
      return (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
          <line x1="12" y1="2" x2="12" y2="12" />
        </svg>
      );
    default:
      return (
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2.2">
          <polyline points="4 17 10 11 4 5" />
          <line x1="12" y1="19" x2="20" y2="19" />
        </svg>
      );
  }
}

function getCommandDisplayName(type) {
  switch (type?.toLowerCase()) {
    case "message":
      return "Send Message";
    case "lock":
      return "Lock Workstation";
    case "restart":
      return "Restart Computer";
    case "shutdown":
      return "Shutdown Computer";
    default:
      return type || "Unknown";
  }
}

export default function CommandHistoryTable({
  commands = [],
  totalCount = 0,
  page = 1,
  pageSize = 10,
  onPageChange,
  loading = false,
  selectedCommandId = null,
  onSelectCommand,
  onCancelCommand = null,
  onReissueCommand = null,
}) {
  const [activeMenuId, setActiveMenuId] = useState(null);

  const totalPages = Math.ceil(totalCount / pageSize) || 1;
  const startItem = totalCount > 0 ? (page - 1) * pageSize + 1 : 0;
  const endItem = Math.min(page * pageSize, totalCount);

  const getPageNumbers = () => {
    const pages = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (page > 3) pages.push("...");
      const start = Math.max(2, page - 1);
      const end = Math.min(totalPages - 1, page + 1);
      for (let i = start; i <= end; i++) pages.push(i);
      if (page < totalPages - 2) pages.push("...");
      pages.push(totalPages);
    }
    return pages;
  };

  const toggleMenu = (e, cmdId) => {
    e.stopPropagation();
    setActiveMenuId((prev) => (prev === cmdId ? null : cmdId));
  };

  return (
    <div className="cmd-table-container">
      <div className="cmd-table-scroll-wrapper">
        <table className="cmd-history-table">
          <thead>
            <tr>
              <th className="col-num">#</th>
              <th className="col-time">Executed At</th>
              <th className="col-action">Command / Action</th>
              <th className="col-user">Executed By</th>
              <th className="col-status">Status</th>
              <th className="col-duration">Duration</th>
              <th className="col-details">Details</th>
              <th className="col-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && commands.length === 0 ? (
              <tr>
                <td colSpan={8} className="cmd-table-empty">
                  <div className="cmd-skeleton-row">
                    <span className="cmd-table-spinner" />
                    <span>Loading command history...</span>
                  </div>
                </td>
              </tr>
            ) : commands.length === 0 ? (
              <tr>
                <td colSpan={8} className="cmd-table-empty">
                  <p>No remote commands found matching your criteria.</p>
                </td>
              </tr>
            ) : (
              commands.map((cmd, idx) => {
                const isSelected = selectedCommandId === cmd.id;
                const isSuccess = cmd.status === "executed" || cmd.result?.success;
                const isFailed = cmd.status === "failed" || (cmd.result && !cmd.result.success);
                const isPending = cmd.status === "pending";
                const isDelivered = cmd.status === "delivered";

                const statusClass = isSuccess
                  ? "success"
                  : isFailed
                  ? "failed"
                  : isPending
                  ? "pending"
                  : isDelivered
                  ? "delivered"
                  : "cancelled";

                const statusLabel = isSuccess
                  ? "Success"
                  : isFailed
                  ? "Failed"
                  : isPending
                  ? "Pending"
                  : isDelivered
                  ? "Delivered"
                  : "Cancelled";

                const executedAt = formatTimestamp(
                  cmd.result?.completed_at || cmd.created_at
                );

                const executedBy =
                  cmd.issued_by_username || (cmd.issued_by ? `User #${cmd.issued_by}` : "Admin");

                const duration =
                  cmd.duration_seconds !== null && cmd.duration_seconds !== undefined
                    ? `${cmd.duration_seconds}s`
                    : cmd.result?.completed_at && cmd.created_at
                    ? `${Math.max(0, Math.round(((new Date(cmd.result.completed_at) - new Date(cmd.created_at)) / 1000) * 10) / 10)}s`
                    : "—";

                const rowNumber = (page - 1) * pageSize + idx + 1;

                return (
                  <tr
                    key={cmd.id}
                    className={`cmd-table-row ${isSelected ? "selected" : ""}`}
                    onClick={() => onSelectCommand && onSelectCommand(cmd)}
                  >
                    <td className="col-num">{rowNumber}</td>

                    <td className="col-time font-time">{executedAt}</td>

                    <td className="col-action">
                      <div className="cmd-action-cell">
                        <span className="cmd-type-icon">{getCommandIcon(cmd.command_type)}</span>
                        <span className="cmd-type-name">
                          {getCommandDisplayName(cmd.command_type)}
                        </span>
                      </div>
                    </td>

                    <td className="col-user">
                      <div className="cmd-user-cell">
                        <svg
                          width="14"
                          height="14"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="#64748b"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                          <circle cx="12" cy="7" r="4" />
                        </svg>
                        <span>{executedBy}</span>
                      </div>
                    </td>

                    <td className="col-status">
                      <span className={`cmd-status-badge badge-${statusClass}`}>
                        <span className="status-dot" />
                        {statusLabel}
                      </span>
                    </td>

                    <td className="col-duration">{duration}</td>

                    <td className="col-details">
                      <button
                        type="button"
                        className="cmd-view-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectCommand && onSelectCommand(cmd);
                        }}
                      >
                        View
                      </button>
                    </td>

                    <td className="col-actions">
                      <div className="cmd-menu-wrapper">
                        <button
                          type="button"
                          className="cmd-kebab-btn"
                          onClick={(e) => toggleMenu(e, cmd.id)}
                          title="Actions menu"
                        >
                          ⋮
                        </button>

                        {activeMenuId === cmd.id && (
                          <div className="cmd-dropdown-menu">
                            <button
                              type="button"
                              className="dropdown-item"
                              onClick={(e) => {
                                e.stopPropagation();
                                setActiveMenuId(null);
                                onSelectCommand && onSelectCommand(cmd);
                              }}
                            >
                              View Details
                            </button>

                            {onReissueCommand && (
                              <button
                                type="button"
                                className="dropdown-item"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(null);
                                  onReissueCommand(cmd);
                                }}
                              >
                                Re-issue Command
                              </button>
                            )}

                            {isPending && onCancelCommand && (
                              <button
                                type="button"
                                className="dropdown-item danger"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setActiveMenuId(null);
                                  onCancelCommand(cmd.id);
                                }}
                              >
                                Cancel Command
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="cmd-pagination-bar">
        <span className="pagination-info">
          Showing {startItem} to {endItem} of {totalCount} entries
        </span>

        {totalPages > 1 && (
          <div className="pagination-controls">
            <button
              type="button"
              className="pagination-btn arrow"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
              title="Previous page"
            >
              ‹
            </button>

            {getPageNumbers().map((p, idx) =>
              p === "..." ? (
                <span key={`ellipsis-${idx}`} className="pagination-ellipsis">
                  ...
                </span>
              ) : (
                <button
                  key={p}
                  type="button"
                  className={`pagination-btn ${p === page ? "active" : ""}`}
                  onClick={() => onPageChange(p)}
                >
                  {p}
                </button>
              )
            )}

            <button
              type="button"
              className="pagination-btn arrow"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              title="Next page"
            >
              ›
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
