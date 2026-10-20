import { useState } from "react";
import Icon from "../../../../components/ui/Icon";
import { SoftwareIcon, WindowsLogoIcon } from "../../utils/softwareUtils";
import "./SoftwareTable.css";

export default function SoftwareTable({
  softwareList = [],
  totalCount = 0,
  page = 1,
  pageSize = 10,
  onPageChange,
  onPageSizeChange,
  sortConfig = { key: "name", direction: "asc" },
  onSortChange,
  tableSearch,
  setTableSearch,
  viewMode = "table",
  onToggleViewMode,
  selectedSoftwareIds = new Set(),
  onToggleSelectAll,
  onToggleSelectItem,
  onClearSelection,
  onInspect,
  onExportCsv,
  onExportItem,
  loading = false,
}) {
  const [activeMenuId, setActiveMenuId] = useState(null);

  // Pagination calculations
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const startItem = totalCount === 0 ? 0 : (page - 1) * pageSize + 1;
  const endItem = Math.min(totalCount, page * pageSize);

  // Checkbox state
  const isAllSelected =
    softwareList.length > 0 &&
    softwareList.every((item) => selectedSoftwareIds.has(item.id));
  const hasSelected = selectedSoftwareIds.size > 0;

  // Render pagination buttons (e.g. 1, 2, 3, 4, 5 ... totalPages)
  const renderPaginationButtons = () => {
    const buttons = [];
    const maxVisiblePages = 5;

    let startPage = Math.max(1, page - 2);
    let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

    if (endPage - startPage + 1 < maxVisiblePages) {
      startPage = Math.max(1, endPage - maxVisiblePages + 1);
    }

    for (let p = startPage; p <= endPage; p++) {
      buttons.push(
        <button
          key={p}
          type="button"
          className={`software-page-btn ${p === page ? "active" : ""}`}
          onClick={() => onPageChange(p)}
        >
          {p}
        </button>
      );
    }

    return (
      <div className="software-pagination-pages">
        <button
          type="button"
          className="software-page-nav-btn"
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
          title="First page"
        >
          «
        </button>
        <button
          type="button"
          className="software-page-nav-btn"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
          title="Previous page"
        >
          ‹
        </button>

        {startPage > 1 && (
          <>
            <button
              type="button"
              className="software-page-btn"
              onClick={() => onPageChange(1)}
            >
              1
            </button>
            {startPage > 2 && <span className="software-page-ellipsis">…</span>}
          </>
        )}

        {buttons}

        {endPage < totalPages && (
          <>
            {endPage < totalPages - 1 && (
              <span className="software-page-ellipsis">…</span>
            )}
            <button
              type="button"
              className="software-page-btn"
              onClick={() => onPageChange(totalPages)}
            >
              {totalPages}
            </button>
          </>
        )}

        <button
          type="button"
          className="software-page-nav-btn"
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages}
          title="Next page"
        >
          ›
        </button>
        <button
          type="button"
          className="software-page-nav-btn"
          onClick={() => onPageChange(totalPages)}
          disabled={page >= totalPages}
          title="Last page"
        >
          »
        </button>
      </div>
    );
  };

  return (
    <div className="software-table-card">
      {/* ========================================================
          Card Toolbar
      ======================================================== */}
      <div className="software-table-toolbar">
        <div className="software-table-title-area">
          <div className="software-table-icon">
            <Icon type="details" size={18} />
          </div>
          <h3 className="software-table-title">
            {`Installed Software (${totalCount})`}
          </h3>
        </div>

        <div className="software-table-actions">
          {/* In-results search */}
          <div className="software-table-search-wrap">
            <input
              type="text"
              placeholder="Search in results..."
              value={tableSearch}
              onChange={(e) => setTableSearch(e.target.value)}
              className="software-table-search-input"
            />
            {tableSearch ? (
              <button
                type="button"
                className="software-table-search-clear"
                onClick={() => setTableSearch("")}
              >
                ✕
              </button>
            ) : (
              <span className="software-table-search-icon">
                <Icon type="search" size={14} />
              </span>
            )}
          </div>

          {/* Export CSV button */}
          <button
            type="button"
            className="software-table-export-btn"
            onClick={() => onExportCsv(hasSelected)}
          >
            <Icon type="download" size={15} />
            <span>{hasSelected ? "Export Selected" : "Export CSV"}</span>
          </button>

          {/* View Mode Toggle */}
          <button
            type="button"
            className={`software-table-view-toggle ${
              viewMode === "table" ? "active" : ""
            }`}
            onClick={onToggleViewMode}
            title={viewMode === "table" ? "Switch to Cards" : "Switch to Table"}
          >
            <Icon type="menu" size={16} />
          </button>
        </div>
      </div>

      {/* ========================================================
          Selection Banner (When items checked)
      ======================================================== */}
      {hasSelected && (
        <div className="software-selection-banner">
          <div className="software-selection-badge">
            <Icon type="check" size={14} />
            <span>{`${selectedSoftwareIds.size} software items selected`}</span>
          </div>
          <div className="software-selection-actions">
            <button
              type="button"
              className="software-selection-btn export"
              onClick={() => onExportCsv(true)}
            >
              Export Selected
            </button>
            <button
              type="button"
              className="software-selection-btn deselect"
              onClick={onClearSelection}
            >
              Deselect All
            </button>
          </div>
        </div>
      )}

      {/* ========================================================
          Table View
      ======================================================== */}
      {viewMode === "table" ? (
        <div className="software-table-responsive">
          <table className="software-data-table">
            <thead>
              <tr>
                <th className="th-checkbox">
                  <input
                    type="checkbox"
                    checked={isAllSelected}
                    onChange={onToggleSelectAll}
                    aria-label="Select all software"
                  />
                </th>
                <th
                  className="th-sortable th-name"
                  onClick={() => onSortChange("name")}
                >
                  <div className="th-content">
                    <span>Software Name</span>
                    <span className="th-sort-indicator">
                      {sortConfig.key === "name"
                        ? sortConfig.direction === "asc"
                          ? "▾"
                          : "▴"
                        : "▾"}
                    </span>
                  </div>
                </th>
                <th
                  className="th-sortable th-version"
                  onClick={() => onSortChange("version")}
                >
                  <div className="th-content">
                    <span>Version</span>
                    <span className="th-sort-indicator">
                      {sortConfig.key === "version"
                        ? sortConfig.direction === "asc"
                          ? "▾"
                          : "▴"
                        : ""}
                    </span>
                  </div>
                </th>
                <th
                  className="th-sortable th-publisher"
                  onClick={() => onSortChange("publisher")}
                >
                  <div className="th-content">
                    <span>Publisher</span>
                    <span className="th-sort-indicator">
                      {sortConfig.key === "publisher"
                        ? sortConfig.direction === "asc"
                          ? "▾"
                          : "▴"
                        : ""}
                    </span>
                  </div>
                </th>
                <th
                  className="th-sortable th-installed"
                  onClick={() => onSortChange("installed_count")}
                >
                  <div className="th-content">
                    <span>Installed On (Computers)</span>
                    <span className="th-sort-indicator">
                      {sortConfig.key === "installed_count"
                        ? sortConfig.direction === "asc"
                          ? "▾"
                          : "▴"
                        : ""}
                    </span>
                  </div>
                </th>
                <th className="th-os">Operating System</th>
                <th className="th-actions">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading && softwareList.length === 0 ? (
                <tr>
                  <td colSpan="7" className="td-empty">
                    <div className="software-loading-spinner-wrap">
                      <Icon type="refresh" size={24} />
                      <span>Loading software records...</span>
                    </div>
                  </td>
                </tr>
              ) : softwareList.length === 0 ? (
                <tr>
                  <td colSpan="7" className="td-empty">
                    <div className="software-empty-state">
                      <Icon type="software" size={32} />
                      <h4>No software items found</h4>
                      <p>
                        No installed applications match the current filter or
                        search criteria.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                softwareList.map((item) => {
                  const isSelected = selectedSoftwareIds.has(item.id);
                  const isMenuOpen = activeMenuId === item.id;
                  const installedRatio =
                    item.installed_count && item.total_computers
                      ? `${item.installed_count} / ${item.total_computers}`
                      : `${item.installed_count || 1} / 5`;

                  return (
                    <tr
                      key={item.id}
                      className={`software-row ${isSelected ? "selected" : ""}`}
                    >
                      {/* Checkbox */}
                      <td className="td-checkbox">
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => onToggleSelectItem(item.id)}
                          aria-label={`Select ${item.name}`}
                        />
                      </td>

                      {/* Name & Brand Icon */}
                      <td className="td-name">
                        <div
                          className="software-name-cell"
                          onClick={() => onInspect(item)}
                          role="button"
                          tabIndex={0}
                        >
                          <div className="software-item-icon">
                            <SoftwareIcon name={item.name} publisher={item.publisher} size={26} />
                          </div>
                          <span className="software-item-name" title={item.name}>
                            {item.name}
                          </span>
                        </div>
                      </td>

                      {/* Version Pill */}
                      <td className="td-version">
                        <code className="software-version-pill">
                          {item.version || "—"}
                        </code>
                      </td>

                      {/* Publisher */}
                      <td className="td-publisher" title={item.publisher || "—"}>
                        {item.publisher || "—"}
                      </td>

                      {/* Installed On Badge */}
                      <td className="td-installed">
                        <button
                          type="button"
                          className="software-installed-badge"
                          onClick={() => onInspect(item)}
                          title="Click to view installed computers"
                        >
                          {installedRatio}
                        </button>
                      </td>

                      {/* OS Badge */}
                      <td className="td-os">
                        <div className="software-os-cell">
                          <WindowsLogoIcon size={14} />
                          <span>{item.os_display || "Windows 10/11"}</span>
                        </div>
                      </td>

                      {/* Actions */}
                      <td className="td-actions">
                        <div className="software-action-buttons">
                          <button
                            type="button"
                            className="software-action-btn view"
                            onClick={() => onInspect(item)}
                            title="View details"
                          >
                            <Icon type="eye" size={15} />
                          </button>

                          <button
                            type="button"
                            className="software-action-btn export"
                            onClick={() => onExportItem(item)}
                            title="Export this software"
                          >
                            <Icon type="download" size={15} />
                          </button>

                          <div className="software-more-wrap">
                            <button
                              type="button"
                              className="software-action-btn more"
                              onClick={() =>
                                setActiveMenuId(isMenuOpen ? null : item.id)
                              }
                              title="More options"
                            >
                              <Icon type="more" size={15} />
                            </button>

                            {isMenuOpen && (
                              <div className="software-menu-popover">
                                <button
                                  type="button"
                                  onClick={() => {
                                    onInspect(item);
                                    setActiveMenuId(null);
                                  }}
                                >
                                  <Icon type="computer" size={13} />
                                  <span>View Installed Computers</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    navigator.clipboard?.writeText(item.name);
                                    setActiveMenuId(null);
                                  }}
                                >
                                  <Icon type="details" size={13} />
                                  <span>Copy Software Name</span>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => {
                                    onExportItem(item);
                                    setActiveMenuId(null);
                                  }}
                                >
                                  <Icon type="download" size={13} />
                                  <span>Export Item CSV</span>
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      ) : (
        /* ========================================================
           Card Grid View
        ======================================================== */
        <div className="software-grid-view">
          {softwareList.map((item) => (
            <div
              key={item.id}
              className={`software-grid-card ${
                selectedSoftwareIds.has(item.id) ? "selected" : ""
              }`}
            >
              <div className="software-grid-card-top">
                <div className="software-grid-card-icon">
                  <SoftwareIcon name={item.name} publisher={item.publisher} size={32} />
                </div>
                <input
                  type="checkbox"
                  checked={selectedSoftwareIds.has(item.id)}
                  onChange={() => onToggleSelectItem(item.id)}
                />
              </div>

              <h4 className="software-grid-card-name" title={item.name}>
                {item.name}
              </h4>
              <span className="software-grid-card-pub">
                {item.publisher || "Unknown publisher"}
              </span>

              <div className="software-grid-card-details">
                <code className="software-version-pill">
                  {item.version || "—"}
                </code>
                <span className="software-installed-badge">
                  {item.installed_count && item.total_computers
                    ? `${item.installed_count} / ${item.total_computers}`
                    : "Installed"}
                </span>
              </div>

              <div className="software-grid-card-footer">
                <div className="software-os-cell">
                  <WindowsLogoIcon size={13} />
                  <span>{item.os_display || "Windows 10/11"}</span>
                </div>
                <button
                  type="button"
                  className="software-grid-view-btn"
                  onClick={() => onInspect(item)}
                >
                  View Details
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ========================================================
          Pagination Footer
      ======================================================== */}
      <div className="software-table-footer">
        <div className="software-table-counts">
          Showing <strong>{startItem}</strong> to <strong>{endItem}</strong> of{" "}
          <strong>{totalCount}</strong> software items
        </div>

        <div className="software-table-pagination-group">
          {renderPaginationButtons()}

          {/* Page Size Selector */}
          <div className="software-page-size-wrap">
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              className="software-page-size-select"
            >
              <option value={10}>10 / page</option>
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
}
