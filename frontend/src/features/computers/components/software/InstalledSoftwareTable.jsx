import { useState } from "react";
import "./InstalledSoftwareTable.css";

function SoftwareAppIcon({ name = "" }) {
  const n = (name || "").toLowerCase();

  if (n.includes("chrome")) {
    return (
      <svg className="table-app-icon-svg" viewBox="0 0 24 24" fill="none">
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
      <svg className="table-app-icon-svg" viewBox="0 0 24 24" fill="none">
        <path d="M17.5 2.5L7 10.5 3 7.5 1.5 8.5v7L3 16.5l4-3 10.5 8 5-2.5V5l-5-2.5z" fill="#0065a9" />
        <path d="M17.5 2.5L8.5 10l9 7.5 4-2V4.5l-4-2z" fill="#007acc" />
        <path d="M21.5 4.5L17.5 2.5v19l4-2V4.5z" fill="#1f9cf0" />
      </svg>
    );
  }

  if (n.includes("edge")) {
    return (
      <svg className="table-app-icon-svg" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" fill="#0078d7" />
        <path d="M12 4a8 8 0 0 1 7.4 5 5 5 0 0 0-4.4-2c-3 0-5 2-5 5s2 5 5 5c2 0 3.5-.8 4.4-2A8 8 0 1 1 12 4z" fill="#00c7fd" />
      </svg>
    );
  }

  if (n.includes("vlc")) {
    return (
      <svg className="table-app-icon-svg" viewBox="0 0 24 24" fill="none">
        <polygon points="12,2 5,20 19,20" fill="#f58220" />
        <polygon points="12,2 8,13 16,13" fill="#ffffff" />
        <polygon points="12,7 9,16 15,16" fill="#f58220" />
        <rect x="3" y="19.5" width="18" height="2.5" rx="1" fill="#e06200" />
      </svg>
    );
  }

  if (n.includes("7-zip") || n.includes("7zip")) {
    return (
      <svg className="table-app-icon-svg" viewBox="0 0 24 24" fill="none">
        <rect x="2" y="3" width="20" height="18" rx="3" fill="#000000" />
        <rect x="4" y="5" width="16" height="14" rx="2" fill="#22c55e" />
        <text x="12" y="15" textAnchor="middle" fill="#ffffff" fontSize="10" fontWeight="900" fontFamily="sans-serif">
          7z
        </text>
      </svg>
    );
  }

  if (n.includes("notepad")) {
    return (
      <svg className="table-app-icon-svg" viewBox="0 0 24 24" fill="none">
        <rect x="4" y="2" width="16" height="20" rx="3" fill="#90caf9" />
        <path d="M7 6h10M7 10h10M7 14h6" stroke="#1565c0" strokeWidth="2" strokeLinecap="round" />
        <path d="M15 15l4 4-2 2-4-4z" fill="#4caf50" />
      </svg>
    );
  }

  if (n.includes("java") || n.includes("jdk") || n.includes("jre")) {
    return (
      <svg className="table-app-icon-svg" viewBox="0 0 24 24" fill="none">
        <path d="M4 14h16c0 3.3-2.7 6-6 6H10c-3.3 0-6-2.7-6-6z" fill="#e76f00" />
        <path d="M10 2c1 2-1 4 0 6M14 2c1 2-1 4 0 6" stroke="#5382a1" strokeWidth="2" strokeLinecap="round" />
      </svg>
    );
  }

  if (n.includes("python")) {
    return (
      <svg className="table-app-icon-svg" viewBox="0 0 24 24" fill="none">
        <path d="M11.9 2c-3.8 0-3.6 1.6-3.6 1.6l.04 1.7h3.6v.5H5.8S2 5.4 2 9.2s3.3 3.7 3.3 3.7h1v-1.4s-.05-1.7 1.7-1.7h5.8s1.6.03 1.6-1.6V4.4S15.8 2 11.9 2zm-1 1.2c.4 0 .7.3.7.7s-.3.7-.7.7-.7-.3-.7-.7.3-.7.7-.7z" fill="#3776AB" />
        <path d="M12.1 22c3.8 0 3.6-1.6 3.6-1.6l-.04-1.7h-3.6v-.5h6.1s3.8.4 3.8-3.4-3.3-3.7-3.3-3.7h-1v1.4s.05 1.7-1.7 1.7H10.2s-1.6-.03-1.6 1.6v3.8s-.4 2.4 3.5 2.4zm1-1.2c-.4 0-.7-.3-.7-.7s.3-.7.7-.7.7.3.7.7-.3.7-.7.7z" fill="#FFD43B" />
      </svg>
    );
  }

  if (n.includes("git")) {
    return (
      <svg className="table-app-icon-svg" viewBox="0 0 24 24" fill="none">
        <path d="M2.6 10.6l8.8-8.8a1.9 1.9 0 0 1 2.7 0l7.3 7.3a1.9 1.9 0 0 1 0 2.7l-8.8 8.8a1.9 1.9 0 0 1-2.7 0L2.6 13.3a1.9 1.9 0 0 1 0-2.7z" fill="#F05032" />
        <circle cx="10" cy="14" r="1.8" fill="#ffffff" />
        <circle cx="14" cy="10" r="1.8" fill="#ffffff" />
        <circle cx="8" cy="9" r="1.8" fill="#ffffff" />
        <line x1="8" y1="9" x2="10" y2="14" stroke="#ffffff" strokeWidth="1.5" />
      </svg>
    );
  }

  if (n.includes("winrar") || n.includes("rar")) {
    return (
      <svg className="table-app-icon-svg" viewBox="0 0 24 24" fill="none">
        <rect x="3" y="3" width="18" height="18" rx="3" fill="#6a1b9a" />
        <rect x="5" y="6" width="14" height="3" fill="#00897b" />
        <rect x="5" y="10" width="14" height="3" fill="#1e88e5" />
        <rect x="5" y="14" width="14" height="3" fill="#f4511e" />
        <rect x="11" y="4" width="2" height="15" fill="#ffd54f" />
      </svg>
    );
  }

  // Fallback desktop application icon
  return (
    <div className="table-app-fallback-icon">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="3" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="9" y1="21" x2="9" y2="9" />
      </svg>
    </div>
  );
}

function formatInstallDate(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "2-digit",
    });
  } catch {
    return dateStr;
  }
}

export default function InstalledSoftwareTable({
  softwareList = [],
  totalCount = 0,
  page = 1,
  pageSize = 10,
  onPageChange,
  sortConfig = { key: "name", direction: "asc" },
  onSortChange,
  loading = false,
}) {
  const [selectedItemForModal, setSelectedItemForModal] = useState(null);
  const [activeMenuId, setActiveMenuId] = useState(null);
  const [copiedPathId, setCopiedPathId] = useState(null);

  const startEntry = totalCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const endEntry = Math.min(totalCount, page * pageSize);
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));

  const handleCopyPath = (item) => {
    if (!item?.install_location) return;
    navigator.clipboard.writeText(item.install_location);
    setCopiedPathId(item.id);
    setTimeout(() => setCopiedPathId(null), 2000);
    setActiveMenuId(null);
  };

  const handleToggleSort = (key) => {
    if (onSortChange) {
      const isCurrentKey = sortConfig.key === key;
      const newDirection = isCurrentKey && sortConfig.direction === "asc" ? "desc" : "asc";
      onSortChange({ key, direction: newDirection });
    }
  };

  // Generate pagination buttons array with ellipsis
  const getPageNumbers = () => {
    const pages = [];
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (page > 3) pages.push("...");
      const start = Math.max(2, page - 1);
      const end = Math.min(totalPages - 1, page + 1);
      for (let i = start; i <= end; i++) {
        if (!pages.includes(i)) pages.push(i);
      }
      if (page < totalPages - 2) pages.push("...");
      if (!pages.includes(totalPages)) pages.push(totalPages);
    }
    return pages;
  };

  return (
    <div className="table-card installed-software-card">
      {/* Table Card Header */}
      <div className="installed-table-header">
        <div className="installed-table-title-group">
          <div className="installed-table-icon-badge">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="2" />
              <line x1="3" y1="9" x2="21" y2="9" />
              <line x1="9" y1="21" x2="9" y2="9" />
            </svg>
          </div>
          <h3 className="installed-table-title">
            Installed Software <span className="installed-table-counter">({totalCount})</span>
          </h3>
        </div>
      </div>

      {/* Main Table */}
      <div className="installed-table-scroll">
        <table className="installed-software-table">
          <thead>
            <tr>
              <th className="th-number">#</th>
              <th className="th-app-name" onClick={() => handleToggleSort("name")}>
                <div className="th-sortable-label">
                  <span>Application Name</span>
                  <span className="th-sort-indicator">
                    {sortConfig.key === "name" ? (sortConfig.direction === "asc" ? "↑" : "↓") : "↕"}
                  </span>
                </div>
              </th>
              <th className="th-publisher" onClick={() => handleToggleSort("publisher")}>
                <div className="th-sortable-label">
                  <span>Publisher</span>
                  <span className="th-sort-indicator">
                    {sortConfig.key === "publisher" ? (sortConfig.direction === "asc" ? "↑" : "↓") : ""}
                  </span>
                </div>
              </th>
              <th className="th-version">Version</th>
              <th className="th-date" onClick={() => handleToggleSort("install_date")}>
                <div className="th-sortable-label">
                  <span>Installation Date</span>
                  <span className="th-sort-indicator">
                    {sortConfig.key === "install_date" ? (sortConfig.direction === "asc" ? "↑" : "↓") : ""}
                  </span>
                </div>
              </th>
              <th className="th-path">Installation Path</th>
              <th className="th-arch">Architecture</th>
              <th className="th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && softwareList.length === 0 ? (
              <tr>
                <td colSpan="8" className="table-state-cell">
                  <div className="table-loading-state">
                    <div className="table-loading-spinner" />
                    <p>Loading installed software inventory...</p>
                  </div>
                </td>
              </tr>
            ) : softwareList.length === 0 ? (
              <tr>
                <td colSpan="8" className="table-state-cell">
                  <div className="table-empty-state">
                    <p>No software records found matching your filters.</p>
                  </div>
                </td>
              </tr>
            ) : (
              softwareList.map((item, idx) => {
                const rowNumber = (page - 1) * pageSize + idx + 1;
                const isMenuOpen = activeMenuId === item.id;
                const installPath = item.install_location || "—";
                const arch = item.architecture || "—";

                return (
                  <tr key={item.id || idx} className="installed-software-row">
                    <td className="td-number">{rowNumber}</td>
                    <td className="td-app-name">
                      <div className="app-name-cell">
                        <SoftwareAppIcon name={item.name} />
                        <span className="app-title" title={item.name}>
                          {item.name || "—"}
                        </span>
                      </div>
                    </td>
                    <td className="td-publisher" title={item.publisher || ""}>
                      {item.publisher || "—"}
                    </td>
                    <td className="td-version">
                      <span className="version-tag">{item.version || "—"}</span>
                    </td>
                    <td className="td-date">
                      {formatInstallDate(item.install_date)}
                    </td>
                    <td className="td-path">
                      <div className="path-text-cell" title={installPath}>
                        {installPath}
                      </div>
                    </td>
                    <td className="td-arch">
                      <span className={`arch-pill ${arch === "64-bit" ? "arch-64" : arch === "32-bit" ? "arch-32" : ""}`}>
                        {arch}
                      </span>
                    </td>
                    <td className="td-actions">
                      <div className="row-action-wrapper">
                        <button
                          type="button"
                          className="row-action-trigger"
                          onClick={() => setActiveMenuId(isMenuOpen ? null : item.id)}
                          aria-label="Software options"
                        >
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="1" />
                            <circle cx="12" cy="5" r="1" />
                            <circle cx="12" cy="19" r="1" />
                          </svg>
                        </button>

                        {isMenuOpen && (
                          <div className="row-action-popover" onMouseLeave={() => setActiveMenuId(null)}>
                            <button
                              type="button"
                              className="popover-action-item"
                              onClick={() => {
                                setSelectedItemForModal(item);
                                setActiveMenuId(null);
                              }}
                            >
                              <span>Inspect Details</span>
                            </button>
                            {item.install_location && (
                              <button
                                type="button"
                                className="popover-action-item"
                                onClick={() => handleCopyPath(item)}
                              >
                                <span>{copiedPathId === item.id ? "Path Copied!" : "Copy Install Path"}</span>
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

      {/* Table Pagination Footer */}
      <div className="installed-table-footer">
        <div className="installed-pagination-summary">
          Showing <strong>{startEntry}</strong> to <strong>{endEntry}</strong> of{" "}
          <strong>{totalCount}</strong> entries
        </div>

        <div className="installed-pagination-controls">
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

      {/* Details Inspection Modal */}
      {selectedItemForModal && (
        <div
          className="software-inspect-modal-overlay"
          onClick={() => setSelectedItemForModal(null)}
        >
          <div
            className="software-inspect-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="inspect-modal-header">
              <div className="inspect-header-left">
                <SoftwareAppIcon name={selectedItemForModal.name} />
                <div>
                  <h4 className="inspect-modal-title">{selectedItemForModal.name}</h4>
                  <span className="inspect-modal-publisher">{selectedItemForModal.publisher || "Unknown Publisher"}</span>
                </div>
              </div>
              <button
                type="button"
                className="inspect-modal-close"
                onClick={() => setSelectedItemForModal(null)}
              >
                ×
              </button>
            </div>

            <div className="inspect-modal-body">
              <div className="inspect-detail-row">
                <span className="inspect-label">Version</span>
                <span className="inspect-value">{selectedItemForModal.version || "—"}</span>
              </div>
              <div className="inspect-detail-row">
                <span className="inspect-label">Architecture</span>
                <span className="inspect-value">{selectedItemForModal.architecture || "—"}</span>
              </div>
              <div className="inspect-detail-row">
                <span className="inspect-label">Installation Date</span>
                <span className="inspect-value">{formatInstallDate(selectedItemForModal.install_date)}</span>
              </div>
              <div className="inspect-detail-row full-width">
                <span className="inspect-label">Installation Path</span>
                <div className="inspect-path-box">
                  <code>{selectedItemForModal.install_location || "Not recorded by registry"}</code>
                  {selectedItemForModal.install_location && (
                    <button
                      type="button"
                      className="inspect-copy-btn"
                      onClick={() => handleCopyPath(selectedItemForModal)}
                    >
                      {copiedPathId === selectedItemForModal.id ? "Copied" : "Copy"}
                    </button>
                  )}
                </div>
              </div>
            </div>

            <div className="inspect-modal-footer">
              <button
                type="button"
                className="inspect-btn-close"
                onClick={() => setSelectedItemForModal(null)}
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
