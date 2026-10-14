import { useState } from "react";
import "./RunningProcessesTable.css";

function ProcessRowIcon({ name = "" }) {
  const n = (name || "").toLowerCase();

  if (n.includes("chrome")) {
    return (
      <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" fill="#4285F4" />
        <circle cx="12" cy="12" r="4.5" fill="#ffffff" />
        <circle cx="12" cy="12" r="3.2" fill="#1a73e8" />
        <path d="M12 7.5h7.8A10 10 0 0 0 5.2 5.5l3.8 6.5A4.5 4.5 0 0 1 12 7.5z" fill="#EA4335" />
        <path d="M12 16.5l-3.9-6.5a4.5 4.5 0 0 1-.6-2.5H2a10 10 0 0 0 13.5 13.5l3.9-6.5a4.5 4.5 0 0 1-7.4 2z" fill="#FBBC05" />
        <path d="M12 16.5a4.5 4.5 0 0 1-3.9-2.2l-3.9 6.7A10 10 0 0 0 22 12h-7.7a4.5 4.5 0 0 1-2.3 4.5z" fill="#34A853" />
      </svg>
    );
  }

  if (n.includes("code") || n.includes("visual studio")) {
    return (
      <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none">
        <path d="M17.5 2.5L7 10.5 3 7.5 1.5 8.5v7L3 16.5l4-3 10.5 8 5-2.5V5l-5-2.5z" fill="#0065a9" />
        <path d="M17.5 2.5L8.5 10l9 7.5 4-2V4.5l-4-2z" fill="#007acc" />
        <path d="M21.5 4.5L17.5 2.5v19l4-2V4.5z" fill="#1f9cf0" />
      </svg>
    );
  }

  if (n.includes("msmpeng") || n.includes("defender")) {
    return (
      <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#0078d4" strokeWidth="2">
        <path d="M12 2l7 4v6c0 5-3.5 9.5-7 11-3.5-1.5-7-6-7-11V6l7-4z" fill="#0078d4" fillOpacity="0.2" />
      </svg>
    );
  }

  if (n.includes("explorer")) {
    return (
      <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none">
        <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" fill="#f59e0b" />
        <path d="M3 10h18v7a2 2 0 01-2 2H5a2 2 0 01-2-2v-7z" fill="#fbbf24" />
      </svg>
    );
  }

  if (n.includes("dwm")) {
    return (
      <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#475569" strokeWidth="2">
        <rect x="3" y="4" width="18" height="16" rx="2" fill="#e2e8f0" />
        <line x1="3" y1="9" x2="21" y2="9" />
      </svg>
    );
  }

  if (n.includes("java")) {
    return (
      <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none">
        <path d="M4 14h16c0 3.3-2.7 6-6 6H10c-3.3 0-6-2.7-6-6z" fill="#e76f00" />
        <path d="M10 2c1 2-1 4 0 6M14 2c1 2-1 4 0 6" stroke="#5382a1" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }

  if (n.includes("python")) {
    return (
      <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none">
        <path d="M11.9 2c-3.8 0-3.6 1.6-3.6 1.6l.04 1.7h3.6v.5H5.8S2 5.4 2 9.2s3.3 3.7 3.3 3.7h1v-1.4s-.05-1.7 1.7-1.7h5.8s1.6.03 1.6-1.6V4.4S15.8 2 11.9 2zm-1 1.2c.4 0 .7.3.7.7s-.3.7-.7.7-.7-.3-.7-.7.3-.7.7-.7z" fill="#3776AB" />
        <path d="M12.1 22c3.8 0 3.6-1.6 3.6-1.6l-.04-1.7h-3.6v-.5h6.1s3.8.4 3.8-3.4-3.3-3.7-3.3-3.7h-1v1.4s.05 1.7-1.7 1.7H10.2s-1.6-.03-1.6 1.6v3.8s-.4 2.4 3.5 2.4zm1-1.2c-.4 0-.7-.3-.7-.7s.3-.7.7-.7.7.3.7.7-.3.7-.7.7z" fill="#FFD43B" />
      </svg>
    );
  }

  if (n.includes("onedrive")) {
    return (
      <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none">
        <path d="M17.5 19H7a5 5 0 0 1-.5-9.97 7 7 0 0 1 13.5 2.22A4.5 4.5 0 0 1 17.5 19z" fill="#0078d4" />
      </svg>
    );
  }

  if (n.includes("searchindexer") || n.includes("search")) {
    return (
      <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#0284c7" strokeWidth="2">
        <circle cx="11" cy="11" r="8" fill="#e0f2fe" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
      </svg>
    );
  }

  if (n.includes("svchost")) {
    return (
      <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2">
        <rect x="2" y="3" width="20" height="14" rx="2" fill="#f8fafc" />
        <line x1="8" y1="21" x2="16" y2="21" />
        <line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    );
  }

  // Default app/service icon
  return (
    <svg className="table-proc-icon-svg" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2">
      <rect x="3" y="3" width="18" height="18" rx="3" fill="#f1f5f9" />
      <circle cx="12" cy="12" r="4" fill="#cbd5e1" />
    </svg>
  );
}

function formatStatusPill(statusStr) {
  const s = (statusStr || "running").toLowerCase();
  let dotColor = "#16a34a"; // green
  let label = "Running";

  if (s.includes("suspended") || s.includes("sleep")) {
    dotColor = "#0284c7"; // cyan
    label = "Suspended";
  } else if (s.includes("not responding") || s.includes("hung") || s.includes("error")) {
    dotColor = "#dc2626"; // red
    label = "Not Responding";
  } else if (s.includes("zombie") || s.includes("defunct")) {
    dotColor = "#9333ea"; // purple
    label = "Zombie";
  } else if (s.includes("stop") || s.includes("idle")) {
    dotColor = "#d97706"; // amber
    label = "Idle";
  }

  return (
    <span className="proc-status-pill">
      <span className="proc-status-dot" style={{ backgroundColor: dotColor }} />
      <span className="proc-status-text">{label}</span>
    </span>
  );
}

function formatMemory(proc) {
  if (proc.memory_mb !== null && proc.memory_mb !== undefined && proc.memory_mb > 0) {
    if (proc.memory_mb >= 1024) {
      return `${(proc.memory_mb / 1024.0).toFixed(1)} GB`;
    }
    return `${proc.memory_mb.toFixed(1)} MB`;
  }
  if (proc.memory_percent !== undefined && proc.memory_percent !== null) {
    return `${Number(proc.memory_percent).toFixed(1)}%`;
  }
  return "—";
}

export default function RunningProcessesTable({
  processes = [],
  totalCount = 0,
  page = 1,
  pageSize = 10,
  onPageChange,
  sortConfig,
  onSortChange,
  loading = false,
  error = "",
}) {
  const [activeMenuPid, setActiveMenuPid] = useState(null);
  const [selectedProcessForModal, setSelectedProcessForModal] = useState(null);
  const [copiedPid, setCopiedPid] = useState(null);

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const startEntry = totalCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const endEntry = Math.min(totalCount, page * pageSize);

  const handleCopyPath = (proc) => {
    if (!proc?.executable_path) return;
    navigator.clipboard?.writeText(proc.executable_path);
    setCopiedPid(proc.pid);
    setTimeout(() => {
      setCopiedPid(null);
    }, 2000);
  };

  const toggleActionMenu = (pid, e) => {
    e.stopPropagation();
    setActiveMenuPid((prev) => (prev === pid ? null : pid));
  };

  const handleOpenDetails = (proc) => {
    setSelectedProcessForModal(proc);
    setActiveMenuPid(null);
  };

  // Generate pagination page list with ellipsis
  const getPageNumbers = () => {
    const pages = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i += 1) pages.push(i);
    } else if (page <= 4) {
      pages.push(1, 2, 3, 4, 5, "...", totalPages);
    } else if (page >= totalPages - 3) {
      pages.push(1, "...", totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
    } else {
      pages.push(1, "...", page - 1, page, page + 1, "...", totalPages);
    }
    return pages;
  };

  const handleHeaderClick = (key) => {
    if (!onSortChange) return;
    const isCurrent = sortConfig?.key === key;
    const direction = isCurrent && sortConfig?.direction === "desc" ? "asc" : "desc";
    onSortChange({ key, direction });
  };

  const renderSortIndicator = (key) => {
    if (sortConfig?.key !== key) return null;
    return <span className="sort-indicator">{sortConfig.direction === "asc" ? " ▲" : " ▼"}</span>;
  };

  return (
    <div className="running-processes-table-card">
      {/* Table Card Header */}
      <div className="running-table-header">
        <div className="running-table-title-group">
          <div className="running-table-icon-badge">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="3" y="3" width="7" height="7" rx="1.5" />
              <rect x="14" y="3" width="7" height="7" rx="1.5" />
              <rect x="14" y="14" width="7" height="7" rx="1.5" />
              <rect x="3" y="14" width="7" height="7" rx="1.5" />
            </svg>
          </div>
          <h3 className="running-table-title">
            Running Processes ({totalCount})
          </h3>
        </div>
      </div>

      {/* Table Content */}
      <div className="running-table-responsive-wrapper">
        <table className="running-processes-table">
          <thead>
            <tr>
              <th className="th-num">#</th>
              <th
                className="th-name sortable"
                onClick={() => handleHeaderClick("name")}
                title="Sort by Process Name"
              >
                Process Name {renderSortIndicator("name")}
              </th>
              <th
                className="th-pid sortable"
                onClick={() => handleHeaderClick("pid")}
                title="Sort by PID"
              >
                PID {renderSortIndicator("pid")}
              </th>
              <th
                className="th-status sortable"
                onClick={() => handleHeaderClick("status")}
                title="Sort by Status"
              >
                Status {renderSortIndicator("status")}
              </th>
              <th
                className="th-cpu sortable"
                onClick={() => handleHeaderClick("cpu_percent")}
                title="Sort by CPU Usage"
              >
                CPU Usage {renderSortIndicator("cpu_percent")}
              </th>
              <th
                className="th-mem sortable"
                onClick={() => handleHeaderClick("memory_mb")}
                title="Sort by Memory Usage"
              >
                Memory Usage {renderSortIndicator("memory_mb")}
              </th>
              <th
                className="th-user sortable"
                onClick={() => handleHeaderClick("user")}
                title="Sort by User"
              >
                User {renderSortIndicator("user")}
              </th>
              <th className="th-path">Executable Path</th>
              <th className="th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && processes.length === 0 ? (
              <tr>
                <td colSpan="9" className="running-table-loading-cell">
                  <div className="running-table-state-box">
                    <svg
                      className="table-spin-icon"
                      width="28"
                      height="28"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                    </svg>
                    <span>Loading running processes...</span>
                  </div>
                </td>
              </tr>
            ) : error && processes.length === 0 ? (
              <tr>
                <td colSpan="9" className="running-table-error-cell">
                  <div className="running-table-state-box">
                    <span className="error-icon">⚠️</span>
                    <span className="error-text">{error}</span>
                  </div>
                </td>
              </tr>
            ) : processes.length === 0 ? (
              <tr>
                <td colSpan="9" className="running-table-empty-cell">
                  <div className="running-table-state-box">
                    <span className="empty-icon">🔍</span>
                    <span className="empty-title">No matching processes found</span>
                    <span className="empty-subtitle">
                      Try adjusting your search criteria or clearing active filters.
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              processes.map((proc, idx) => {
                const rowNum = (page - 1) * pageSize + idx + 1;
                const isMenuOpen = activeMenuPid === proc.pid;
                const cpuVal =
                  proc.cpu_percent !== undefined
                    ? `${Number(proc.cpu_percent).toFixed(1)}%`
                    : "0.0%";

                return (
                  <tr key={`${proc.pid}-${proc.name}-${idx}`} className="running-table-row">
                    {/* 1. Row Number */}
                    <td className="td-num">{rowNum}</td>

                    {/* 2. Process Name with icon */}
                    <td className="td-name">
                      <div className="proc-name-cell">
                        <ProcessRowIcon name={proc.name} />
                        <span className="proc-name-text" title={proc.name}>
                          {proc.name}
                        </span>
                      </div>
                    </td>

                    {/* 3. PID */}
                    <td className="td-pid">
                      <span className="proc-pid-text">{proc.pid}</span>
                    </td>

                    {/* 4. Status */}
                    <td className="td-status">{formatStatusPill(proc.status)}</td>

                    {/* 5. CPU Usage */}
                    <td className="td-cpu">
                      <span className="proc-cpu-val">{cpuVal}</span>
                    </td>

                    {/* 6. Memory Usage */}
                    <td className="td-mem">
                      <span className="proc-mem-val">{formatMemory(proc)}</span>
                    </td>

                    {/* 7. User */}
                    <td className="td-user">
                      <span className="proc-user-text" title={proc.user || "System"}>
                        {proc.user || "LabUser"}
                      </span>
                    </td>

                    {/* 8. Executable Path */}
                    <td className="td-path">
                      <span
                        className="proc-path-text"
                        title={proc.executable_path || "Path inaccessible / protected"}
                      >
                        {proc.executable_path || "—"}
                      </span>
                    </td>

                    {/* 9. Actions */}
                    <td className="td-actions">
                      <div className="proc-actions-wrapper">
                        <button
                          type="button"
                          className="proc-action-trigger"
                          onClick={(e) => toggleActionMenu(proc.pid, e)}
                          title="Actions menu"
                          aria-label={`Actions for ${proc.name}`}
                        >
                          ⋮
                        </button>

                        {isMenuOpen && (
                          <div
                            className="proc-actions-dropdown"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <button
                              type="button"
                              className="proc-dropdown-item"
                              onClick={() => handleOpenDetails(proc)}
                            >
                              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <circle cx="12" cy="12" r="10" />
                                <line x1="12" y1="16" x2="12" y2="12" />
                                <line x1="12" y1="8" x2="12.01" y2="8" />
                              </svg>
                              <span>View Details</span>
                            </button>

                            {proc.executable_path && (
                              <button
                                type="button"
                                className="proc-dropdown-item"
                                onClick={() => handleCopyPath(proc)}
                              >
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                  <rect x="9" y="9" width="13" height="13" rx="2" />
                                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                                </svg>
                                <span>{copiedPid === proc.pid ? "Copied!" : "Copy Path"}</span>
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
      <div className="running-table-footer">
        <div className="running-pagination-summary">
          Showing <strong>{startEntry}</strong> to <strong>{endEntry}</strong> of{" "}
          <strong>{totalCount}</strong> entries
        </div>

        <div className="running-pagination-controls">
          <button
            type="button"
            className="pagination-btn prev-btn"
            disabled={page <= 1 || loading}
            onClick={() => onPageChange(page - 1)}
            aria-label="Previous page"
          >
            ‹
          </button>

          {getPageNumbers().map((p, pIdx) => {
            if (p === "...") {
              return (
                <span key={`ellipsis-${pIdx}`} className="pagination-ellipsis">
                  ...
                </span>
              );
            }
            return (
              <button
                key={p}
                type="button"
                className={`pagination-btn page-num-btn ${page === p ? "active" : ""}`}
                disabled={loading}
                onClick={() => onPageChange(p)}
              >
                {p}
              </button>
            );
          })}

          <button
            type="button"
            className="pagination-btn next-btn"
            disabled={page >= totalPages || loading}
            onClick={() => onPageChange(page + 1)}
            aria-label="Next page"
          >
            ›
          </button>
        </div>
      </div>

      {/* Process Details Inspection Modal */}
      {selectedProcessForModal && (
        <div
          className="process-inspect-modal-overlay"
          onClick={() => setSelectedProcessForModal(null)}
        >
          <div
            className="process-inspect-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="proc-inspect-modal-header">
              <div className="proc-inspect-header-left">
                <ProcessRowIcon name={selectedProcessForModal.name} />
                <div>
                  <h4 className="proc-inspect-modal-title">{selectedProcessForModal.name}</h4>
                  <span className="proc-inspect-modal-pid">PID: {selectedProcessForModal.pid}</span>
                </div>
              </div>
              <button
                type="button"
                className="proc-inspect-modal-close"
                onClick={() => setSelectedProcessForModal(null)}
              >
                ×
              </button>
            </div>

            <div className="proc-inspect-modal-body">
              <div className="proc-inspect-detail-row">
                <span className="proc-inspect-label">Status</span>
                <span className="proc-inspect-value">{formatStatusPill(selectedProcessForModal.status)}</span>
              </div>
              <div className="proc-inspect-detail-row">
                <span className="proc-inspect-label">User / Owner</span>
                <span className="proc-inspect-value">{selectedProcessForModal.user || "LabUser"}</span>
              </div>
              <div className="proc-inspect-detail-row">
                <span className="proc-inspect-label">CPU Usage</span>
                <span className="proc-inspect-value">
                  {selectedProcessForModal.cpu_percent !== undefined
                    ? `${selectedProcessForModal.cpu_percent.toFixed(1)}%`
                    : "0.0%"}
                </span>
              </div>
              <div className="proc-inspect-detail-row">
                <span className="proc-inspect-label">Memory Usage</span>
                <span className="proc-inspect-value">{formatMemory(selectedProcessForModal)}</span>
              </div>
              {selectedProcessForModal.start_time && (
                <div className="proc-inspect-detail-row">
                  <span className="proc-inspect-label">Started At</span>
                  <span className="proc-inspect-value">{selectedProcessForModal.start_time}</span>
                </div>
              )}
              <div className="proc-inspect-detail-row full-width">
                <span className="proc-inspect-label">Executable Path</span>
                <div className="proc-inspect-path-box">
                  <code>{selectedProcessForModal.executable_path || "Inaccessible / system protected"}</code>
                  {selectedProcessForModal.executable_path && (
                    <button
                      type="button"
                      className="proc-inspect-copy-btn"
                      onClick={() => handleCopyPath(selectedProcessForModal)}
                    >
                      {copiedPid === selectedProcessForModal.pid ? "Copied!" : "Copy"}
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="proc-inspect-modal-footer">
              <button
                type="button"
                className="proc-modal-close-btn"
                onClick={() => setSelectedProcessForModal(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
