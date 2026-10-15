import { useState, useMemo } from "react";
import Icon from "../../../../components/ui/Icon";
import "./TargetComputerTable.css";

function formatRelativeTime(dateString) {
  if (!dateString) return "Never";
  try {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return "—";
    const now = new Date();
    const diffSec = Math.floor((now - date) / 1000);

    if (diffSec < 45) return "Just now";
    if (diffSec < 90) return "1 minute ago";
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)} minutes ago`;
    if (diffSec < 7200) return "1 hour ago";
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)} hours ago`;
    if (diffSec < 172800) return "1 day ago";
    return `${Math.floor(diffSec / 86400)} days ago`;
  } catch {
    return dateString;
  }
}

export default function TargetComputerTable({
  computers = [],
  selectedIds = new Set(),
  onToggleSelect,
  onSelectAllVisible,
  loading = false,
}) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [labFilter, setLabFilter] = useState("all");
  const [locationFilter, setLocationFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(5);

  // Extract distinct labs and locations if present in data
  const availableLabs = useMemo(() => {
    const labs = new Set();
    computers.forEach((c) => {
      if (c.lab_name) labs.add(c.lab_name);
      else if (c.lab) labs.add(c.lab);
      else if (c.group_name) labs.add(c.group_name);
    });
    return Array.from(labs).sort();
  }, [computers]);

  const availableLocations = useMemo(() => {
    const locs = new Set();
    computers.forEach((c) => {
      if (c.location) locs.add(c.location);
      else if (c.room) locs.add(c.room);
    });
    return Array.from(locs).sort();
  }, [computers]);

  // Filter computers
  const filteredComputers = useMemo(() => {
    return computers.filter((comp) => {
      // Search filter (name, hostname, IP)
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const name = (comp.name || comp.hostname || "").toLowerCase();
        const host = (comp.hostname || "").toLowerCase();
        const ip = (comp.ip_address || "").toLowerCase();
        if (!name.includes(query) && !host.includes(query) && !ip.includes(query)) {
          return false;
        }
      }

      // Status filter
      if (statusFilter !== "all") {
        if (comp.status?.toLowerCase() !== statusFilter.toLowerCase()) {
          return false;
        }
      }

      // Lab filter
      if (labFilter !== "all") {
        const compLab = comp.lab_name || comp.lab || comp.group_name || "";
        if (compLab !== labFilter) return false;
      }

      // Location filter
      if (locationFilter !== "all") {
        const compLoc = comp.location || comp.room || "";
        if (compLoc !== locationFilter) return false;
      }

      return true;
    });
  }, [computers, searchTerm, statusFilter, labFilter, locationFilter]);

  // Pagination
  const totalItems = filteredComputers.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / rowsPerPage));
  const validPage = Math.min(currentPage, totalPages);

  const paginatedComputers = useMemo(() => {
    const startIdx = (validPage - 1) * rowsPerPage;
    return filteredComputers.slice(startIdx, startIdx + rowsPerPage);
  }, [filteredComputers, validPage, rowsPerPage]);

  // Check if all visible computers on this page are selected
  const allVisibleSelected =
    paginatedComputers.length > 0 &&
    paginatedComputers.every((c) => selectedIds.has(c.id));

  const someVisibleSelected =
    paginatedComputers.some((c) => selectedIds.has(c.id)) && !allVisibleSelected;

  const handleMasterCheckboxChange = () => {
    if (allVisibleSelected) {
      // Deselect all on current page
      const pageIds = paginatedComputers.map((c) => c.id);
      onSelectAllVisible(pageIds, false);
    } else {
      // Select all on current page
      const pageIds = paginatedComputers.map((c) => c.id);
      onSelectAllVisible(pageIds, true);
    }
  };

  const handleResetFilters = () => {
    setSearchTerm("");
    setStatusFilter("all");
    setLabFilter("all");
    setLocationFilter("all");
    setCurrentPage(1);
  };

  const startIdx = totalItems > 0 ? (validPage - 1) * rowsPerPage + 1 : 0;
  const endIdx = Math.min(validPage * rowsPerPage, totalItems);

  return (
    <div className="target-computer-card" data-testid="target-computer-section">
      {/* Card Header & Filter Bar */}
      <div className="target-table-header">
        <div className="target-header-left">
          <div className="target-header-icon">
            <Icon name="computer" size={20} />
          </div>
          <div>
            <h2 className="target-header-title">Select Target Computers</h2>
            <p className="target-header-sub">
              Choose one or more computers to execute commands
            </p>
          </div>
        </div>

        <div className="target-filters-right">
          {/* Search Input */}
          <div className="target-search-box">
            <Icon name="search" size={16} />
            <input
              type="text"
              placeholder="Search by name, hostname or IP..."
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setCurrentPage(1);
              }}
              aria-label="Search computers"
            />
          </div>

          {/* Status Dropdown */}
          <select
            className="target-select-filter"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setCurrentPage(1);
            }}
            aria-label="Filter by status"
          >
            <option value="all">All Status</option>
            <option value="online">Online</option>
            <option value="offline">Offline</option>
          </select>

          {/* Lab Dropdown */}
          <select
            className="target-select-filter"
            value={labFilter}
            onChange={(e) => {
              setLabFilter(e.target.value);
              setCurrentPage(1);
            }}
            aria-label="Filter by lab"
          >
            <option value="all">All Labs</option>
            {availableLabs.map((lab) => (
              <option key={lab} value={lab}>
                {lab}
              </option>
            ))}
          </select>

          {/* Location Dropdown */}
          <select
            className="target-select-filter"
            value={locationFilter}
            onChange={(e) => {
              setLocationFilter(e.target.value);
              setCurrentPage(1);
            }}
            aria-label="Filter by location"
          >
            <option value="all">All Locations</option>
            {availableLocations.map((loc) => (
              <option key={loc} value={loc}>
                {loc}
              </option>
            ))}
          </select>

          {/* Reset Button */}
          <button
            type="button"
            className="target-reset-btn"
            onClick={handleResetFilters}
            title="Reset filters"
          >
            <Icon name="refresh" size={14} />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {/* Table Content */}
      <div className="target-table-responsive">
        <table className="target-table">
          <thead>
            <tr>
              <th className="th-checkbox">
                <input
                  type="checkbox"
                  checked={allVisibleSelected}
                  ref={(input) => {
                    if (input) input.indeterminate = someVisibleSelected;
                  }}
                  onChange={handleMasterCheckboxChange}
                  aria-label="Select all computers on page"
                />
              </th>
              <th>Computer Name</th>
              <th>Hostname</th>
              <th>IP Address</th>
              <th>Lab</th>
              <th>Location</th>
              <th>Status</th>
              <th>Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="table-loading-cell">
                  Loading computers...
                </td>
              </tr>
            ) : paginatedComputers.length === 0 ? (
              <tr>
                <td colSpan={8} className="table-empty-cell">
                  No computers match your search or filter criteria.
                </td>
              </tr>
            ) : (
              paginatedComputers.map((comp) => {
                const isSelected = selectedIds.has(comp.id);
                const isOnline = comp.status?.toLowerCase() === "online";
                const displayName =
                  comp.name || comp.hostname?.toUpperCase() || `PC-${comp.id}`;
                const labName =
                  comp.lab_name || comp.lab || comp.group_name || "—";
                const locationName = comp.location || comp.room || "—";

                return (
                  <tr
                    key={comp.id}
                    className={isSelected ? "row-selected" : ""}
                    onClick={(e) => {
                      // Don't double trigger if clicking directly on checkbox
                      if (e.target.tagName !== "INPUT") {
                        onToggleSelect(comp.id);
                      }
                    }}
                  >
                    <td className="td-checkbox">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleSelect(comp.id)}
                        aria-label={`Select ${displayName}`}
                      />
                    </td>
                    <td className="td-name">
                      <strong>{displayName}</strong>
                    </td>
                    <td className="td-mono">{comp.hostname || "—"}</td>
                    <td className="td-mono">{comp.ip_address || "—"}</td>
                    <td>{labName}</td>
                    <td>{locationName}</td>
                    <td>
                      <span
                        className={`status-pill ${
                          isOnline ? "online" : "offline"
                        }`}
                      >
                        <span className="status-dot" />
                        {isOnline ? "Online" : "Offline"}
                      </span>
                    </td>
                    <td className="td-muted">
                      {formatRelativeTime(comp.last_seen)}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Table Footer with Pagination */}
      <div className="target-table-footer">
        <div className="target-footer-info">
          Showing {startIdx} to {endIdx} of {totalItems} computers
          {selectedIds.size > 0 && (
            <span className="selected-count-badge">
              ({selectedIds.size} selected)
            </span>
          )}
        </div>

        <div className="target-pagination-controls">
          <div className="rows-per-page-selector">
            <span>Rows per page:</span>
            <select
              value={rowsPerPage}
              onChange={(e) => {
                setRowsPerPage(Number(e.target.value));
                setCurrentPage(1);
              }}
              aria-label="Rows per page"
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>

          <div className="pagination-buttons">
            <button
              type="button"
              className="page-btn prev"
              disabled={validPage <= 1}
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              aria-label="Previous page"
            >
              &lt;
            </button>

            {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => {
              // Show pages around current
              if (
                totalPages > 7 &&
                p > 3 &&
                p < totalPages - 2 &&
                Math.abs(p - validPage) > 1
              ) {
                if (p === 4 || p === totalPages - 3) {
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
                  className={`page-btn ${p === validPage ? "active" : ""}`}
                  onClick={() => setCurrentPage(p)}
                >
                  {p}
                </button>
              );
            })}

            <button
              type="button"
              className="page-btn next"
              disabled={validPage >= totalPages}
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              aria-label="Next page"
            >
              &gt;
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
