import { useState, useMemo } from "react";
import "./LiveSystemTable.css";

function WindowsIcon({ size = 16 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="#0078D7">
      <path d="M0 3.449L9.75 2.1v9.451H0m10.949-9.602L24 0v11.4H10.949M0 12.6h9.75v9.451L0 20.699M10.949 12.6H24V24l-12.949-1.8" />
    </svg>
  );
}

function formatUpdateTime(lastSeen) {
  if (!lastSeen) return "—";
  try {
    const d = new Date(lastSeen);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "—";
  }
}

export default function LiveSystemTable({
  computers = [],
  selectedIds = new Set(),
  onToggleSelect,
  onToggleSelectAll,
  searchQuery = "",
  onSearchChange,
  onInspect,
  onRemoteCommand,
  onPowerCommand,
}) {
  const [tableSearch, setTableSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [filterOpen, setFilterOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(5);
  const [openActionMenuId, setOpenActionMenuId] = useState(null);

  // Combine top-header search and local table search
  const effectiveSearch = (searchQuery || tableSearch).toLowerCase().trim();

  // Filter computers
  const filteredComputers = useMemo(() => {
    return computers.filter((c) => {
      // 1. Status filter
      if (statusFilter !== "all") {
        const isOnline = (c.status || "").toLowerCase() === "online";
        if (statusFilter === "online" && !isOnline) return false;
        if (statusFilter === "offline" && isOnline) return false;
      }
      // 2. Search query
      if (effectiveSearch) {
        const h = (c.hostname || `PC-${c.id}`).toLowerCase();
        const ip = (c.ip_address || "").toLowerCase();
        const os = (c.os_name || "").toLowerCase();
        return h.includes(effectiveSearch) || ip.includes(effectiveSearch) || os.includes(effectiveSearch);
      }
      return true;
    });
  }, [computers, statusFilter, effectiveSearch]);

  // Pagination calculations
  const totalCount = filteredComputers.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedComputers = filteredComputers.slice(startIndex, startIndex + pageSize);

  const startRecord = totalCount === 0 ? 0 : startIndex + 1;
  const endRecord = Math.min(startIndex + pageSize, totalCount);

  const allPageSelected =
    paginatedComputers.length > 0 &&
    paginatedComputers.every((c) => selectedIds.has(c.id));

  const somePageSelected =
    paginatedComputers.some((c) => selectedIds.has(c.id)) && !allPageSelected;

  const handleSelectAllChange = () => {
    const pageIds = paginatedComputers.map((c) => c.id);
    onToggleSelectAll?.(pageIds, !allPageSelected);
  };

  // Metric color helper
  const getMetricColor = (val, type = "cpu") => {
    const num = parseFloat(val) || 0;
    if (num >= 85) return "#ef4444"; // red
    if (num >= 70) return "#f97316"; // orange
    if (type === "cpu") return "#3b82f6"; // blue
    if (type === "ram") return "#10b981"; // green
    return "#8b5cf6"; // purple for disk
  };

  return (
    <div className="live-system-table-card" data-testid="live-system-status-table">
      {/* Header with Search and Filter button */}
      <div className="live-table-header">
        <div className="live-table-title-group">
          <div className="live-table-badge-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="3" width="20" height="14" rx="2" />
              <line x1="8" y1="21" x2="16" y2="21" />
              <line x1="12" y1="17" x2="12" y2="21" />
            </svg>
          </div>
          <h3 className="live-table-title">Live System Status</h3>
        </div>

        <div className="live-table-controls">
          {/* Table search input */}
          <div className="live-table-search-box">
            <span className="live-table-search-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </span>
            <input
              type="text"
              placeholder="Search computer..."
              value={tableSearch}
              onChange={(e) => {
                setTableSearch(e.target.value);
                setPage(1);
                if (onSearchChange) onSearchChange(e.target.value);
              }}
              className="live-table-search-input"
            />
          </div>

          {/* Filter button */}
          <div className="live-table-filter-wrapper">
            <button
              type="button"
              className={`live-table-filter-btn ${statusFilter !== "all" ? "active" : ""}`}
              onClick={() => setFilterOpen((prev) => !prev)}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
              </svg>
              Filter
            </button>

            {filterOpen && (
              <div className="live-table-filter-popover">
                <span className="filter-popover-title">Filter by Status</span>
                <label className="filter-option-label">
                  <input
                    type="radio"
                    name="statusFilter"
                    checked={statusFilter === "all"}
                    onChange={() => {
                      setStatusFilter("all");
                      setFilterOpen(false);
                      setPage(1);
                    }}
                  />
                  <span>All Systems ({computers.length})</span>
                </label>
                <label className="filter-option-label">
                  <input
                    type="radio"
                    name="statusFilter"
                    checked={statusFilter === "online"}
                    onChange={() => {
                      setStatusFilter("online");
                      setFilterOpen(false);
                      setPage(1);
                    }}
                  />
                  <span>Online Only</span>
                </label>
                <label className="filter-option-label">
                  <input
                    type="radio"
                    name="statusFilter"
                    checked={statusFilter === "offline"}
                    onChange={() => {
                      setStatusFilter("offline");
                      setFilterOpen(false);
                      setPage(1);
                    }}
                  />
                  <span>Offline Only</span>
                </label>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Table Container */}
      <div className="live-table-scroll">
        <table className="live-status-table">
          <thead>
            <tr>
              <th className="th-checkbox">
                <input
                  type="checkbox"
                  checked={allPageSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = somePageSelected;
                  }}
                  onChange={handleSelectAllChange}
                  aria-label="Select all on this page"
                />
              </th>
              <th>Computer Name</th>
              <th>IP Address</th>
              <th>Status</th>
              <th>CPU</th>
              <th>RAM</th>
              <th>Disk</th>
              <th>Last Update</th>
              <th className="th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedComputers.length > 0 ? (
              paginatedComputers.map((comp) => {
                const isSelected = selectedIds.has(comp.id);
                const isOnline = (comp.status || "").toLowerCase() === "online";
                const hostname = comp.hostname || `PC-${comp.id}`;
                const ip = comp.ip_address || "—";
                const cpuVal = isOnline ? (comp.avg_cpu || comp.cpu || 24) : 0;
                const ramVal = isOnline ? (comp.avg_ram || comp.ram || 45) : 0;
                const diskVal = isOnline ? (comp.avg_disk || comp.disk || 50) : 0;
                const lastUpdateStr = formatUpdateTime(comp.last_seen || comp.updated_at);

                return (
                  <tr key={comp.id} className={isSelected ? "row-selected" : ""}>
                    {/* Checkbox */}
                    <td className="td-checkbox">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleSelect?.(comp.id)}
                        aria-label={`Select ${hostname}`}
                      />
                    </td>

                    {/* Computer Name with OS logo */}
                    <td>
                      <div className="table-computer-cell">
                        <WindowsIcon size={16} />
                        <span className="table-computer-name">{hostname}</span>
                      </div>
                    </td>

                    {/* IP Address */}
                    <td className="table-ip-cell">{ip}</td>

                    {/* Status Badge */}
                    <td>
                      <span className={`status-pill ${isOnline ? "status-online" : "status-offline"}`}>
                        <span className="status-dot" />
                        {isOnline ? "Online" : "Offline"}
                      </span>
                    </td>

                    {/* CPU */}
                    <td>
                      <div className="table-progress-cell">
                        <span className="progress-cell-text">{Math.round(cpuVal)}%</span>
                        <div className="progress-cell-track">
                          <div
                            className="progress-cell-fill"
                            style={{
                              width: `${Math.min(100, cpuVal)}%`,
                              backgroundColor: getMetricColor(cpuVal, "cpu"),
                            }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* RAM */}
                    <td>
                      <div className="table-progress-cell">
                        <span className="progress-cell-text">{Math.round(ramVal)}%</span>
                        <div className="progress-cell-track">
                          <div
                            className="progress-cell-fill"
                            style={{
                              width: `${Math.min(100, ramVal)}%`,
                              backgroundColor: getMetricColor(ramVal, "ram"),
                            }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* Disk */}
                    <td>
                      <div className="table-progress-cell">
                        <span className="progress-cell-text">{Math.round(diskVal)}%</span>
                        <div className="progress-cell-track">
                          <div
                            className="progress-cell-fill"
                            style={{
                              width: `${Math.min(100, diskVal)}%`,
                              backgroundColor: getMetricColor(diskVal, "disk"),
                            }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* Last Update */}
                    <td className="table-time-cell">{lastUpdateStr}</td>

                    {/* Actions */}
                    <td className="td-actions">
                      <div className="table-actions-row">
                        <button
                          type="button"
                          className="action-icon-btn"
                          title="View Details"
                          onClick={() => onInspect?.(comp)}
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          className="action-icon-btn"
                          title="Send Command"
                          onClick={() => onRemoteCommand?.(comp)}
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <polyline points="4 17 10 11 4 5" />
                            <line x1="12" y1="19" x2="20" y2="19" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          className="action-icon-btn"
                          title="Power / Restart"
                          onClick={() => onPowerCommand?.(comp)}
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
                            <line x1="12" y1="2" x2="12" y2="12" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          className="action-icon-btn"
                          title="More Actions"
                          onClick={() =>
                            setOpenActionMenuId(openActionMenuId === comp.id ? null : comp.id)
                          }
                        >
                          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="1" />
                            <circle cx="12" cy="5" r="1" />
                            <circle cx="12" cy="19" r="1" />
                          </svg>
                        </button>
                      </div>

                      {/* Dropdown Menu */}
                      {openActionMenuId === comp.id && (
                        <div className="table-row-dropdown">
                          <button
                            type="button"
                            onClick={() => {
                              setOpenActionMenuId(null);
                              onInspect?.(comp);
                            }}
                          >
                            Computer Telemetry
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setOpenActionMenuId(null);
                              onRemoteCommand?.(comp);
                            }}
                          >
                            Execute Script
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setOpenActionMenuId(null);
                              onPowerCommand?.(comp);
                            }}
                          >
                            Reboot Computer
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="9" className="table-empty-row">
                  No computers match the current filter or search criteria.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="live-table-footer">
        <span className="live-table-showing">
          {`Showing ${startRecord} to ${endRecord} of ${totalCount} computers`}
        </span>

        <div className="live-table-pagination-controls">
          <button
            type="button"
            className="page-btn page-arrow"
            disabled={currentPage <= 1}
            onClick={() => setPage(1)}
            title="First Page"
          >
            «
          </button>
          <button
            type="button"
            className="page-btn page-arrow"
            disabled={currentPage <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            title="Previous Page"
          >
            ‹
          </button>

          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => {
            if (
              totalPages > 6 &&
              p !== 1 &&
              p !== totalPages &&
              Math.abs(p - currentPage) > 1
            ) {
              if (p === 2 || p === totalPages - 1) {
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
                className={`page-btn ${p === currentPage ? "active" : ""}`}
                onClick={() => setPage(p)}
              >
                {p}
              </button>
            );
          })}

          <button
            type="button"
            className="page-btn page-arrow"
            disabled={currentPage >= totalPages}
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            title="Next Page"
          >
            ›
          </button>
          <button
            type="button"
            className="page-btn page-arrow"
            disabled={currentPage >= totalPages}
            onClick={() => setPage(totalPages)}
            title="Last Page"
          >
            »
          </button>

          {/* Page size dropdown */}
          <div className="page-size-wrap">
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="page-size-select"
            >
              <option value={5}>5 / page</option>
              <option value={10}>10 / page</option>
              <option value={20}>20 / page</option>
              <option value={50}>50 / page</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
