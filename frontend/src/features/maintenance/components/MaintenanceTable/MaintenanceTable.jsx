import { useState, useEffect, useRef } from "react";
import Icon from "../../../../components/ui/Icon";
import {
  formatDate,
  getMaintenanceStatusConfig,
  getMaintenanceTypeConfig,
  getPaginationItems,
} from "../../utils/maintenanceUtils";
import "./MaintenanceTable.css";

function MaintenanceTable({
  records = [],
  selectedRecord = null,
  onSelectRecord,
  computerMap = {},
  onStatusChange,
  onOpenDetails,
  onOpenComplete,
  onEdit,
  onDelete,
  loading = false,
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [openMenuId, setOpenMenuId] = useState(null);
  const menuRef = useRef(null);

  // Close context menu on outside click
  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpenMenuId(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const totalCount = records.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);
  const startIndex = (safeCurrentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalCount);
  const paginatedRecords = records.slice(startIndex, endIndex);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const paginationItems = getPaginationItems(safeCurrentPage, totalPages);

  return (
    <div className="maint-table-card" data-testid="maintenance-table-card">
      {/* Header */}
      <div className="maint-table-header">
        <div className="maint-table-header-left">
          <div className="maint-table-header-icon">
            <Icon type="maintenance" size={18} />
          </div>
          <div>
            <h2 className="maint-table-header-title">Maintenance Records</h2>
            <p className="maint-table-header-subtitle">
              Scheduled tasks, preventive servicing, repairs, and audit logs.
            </p>
          </div>
        </div>
        <div className="maint-table-header-right">
          <span className="maint-table-count-badge">
            {records.length} {records.length === 1 ? "record" : "records"}
          </span>
        </div>
      </div>

      {/* Table Scroll Wrapper */}
      <div className="maint-table-wrapper">
        <table className="maint-data-table">
          <thead>
            <tr>
              <th className="maint-th-id">ID</th>
              <th className="maint-th-computer">Computer / Target</th>
              <th className="maint-th-task">Maintenance Task</th>
              <th className="maint-th-date">Scheduled Date</th>
              <th className="maint-th-tech">Technician</th>
              <th className="maint-th-status">Status</th>
              <th className="maint-th-actions">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="maint-table-empty">
                  <div className="maint-table-loading-spinner" />
                  <p>Loading maintenance records...</p>
                </td>
              </tr>
            ) : paginatedRecords.length === 0 ? (
              <tr>
                <td colSpan={7} className="maint-table-empty">
                  <div className="maint-table-empty-icon">🔧</div>
                  <strong>No maintenance records found</strong>
                  <p style={{ marginTop: "4px", fontSize: "12px", color: "#64748b" }}>
                    Try adjusting your search criteria or schedule a new maintenance task.
                  </p>
                </td>
              </tr>
            ) : (
              paginatedRecords.map((record) => {
                const comp = computerMap[record.computer_id];
                const hostname =
                  comp?.hostname ||
                  record.computer_name ||
                  `Computer #${record.computer_id || "N/A"}`;
                const ipAddress = comp?.ip_address || comp?.ip;
                const statusCfg = getMaintenanceStatusConfig(record.status);
                const typeCfg = getMaintenanceTypeConfig(record.maintenance_type);
                const isSelected = selectedRecord?.id === record.id;

                return (
                  <tr
                    key={record.id}
                    className={`maint-table-row ${isSelected ? "selected" : ""}`}
                    onClick={() => onSelectRecord && onSelectRecord(record)}
                  >
                    {/* ID */}
                    <td className="maint-td-id">
                      <span className="maint-id-tag">#{record.id}</span>
                    </td>

                    {/* Computer Target */}
                    <td className="maint-td-computer">
                      <div className="maint-computer-cell">
                        <div className="maint-comp-avatar">
                          <Icon type="computer" size={14} />
                        </div>
                        <div className="maint-comp-info">
                          <span className="maint-comp-hostname" title={hostname}>
                            {hostname}
                          </span>
                          {ipAddress && (
                            <span className="maint-comp-ip">{ipAddress}</span>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Task Title & Type */}
                    <td className="maint-td-task">
                      <div className="maint-task-cell">
                        <div className="maint-task-title-row">
                          <span
                            className="maint-type-pill"
                            style={{
                              backgroundColor: typeCfg.bg,
                              color: typeCfg.color,
                              borderColor: typeCfg.border,
                            }}
                          >
                            {typeCfg.label}
                          </span>
                          <span className="maint-task-title" title={record.title}>
                            {record.title || "Routine Maintenance"}
                          </span>
                        </div>
                        {record.description && (
                          <p className="maint-task-desc" title={record.description}>
                            {record.description}
                          </p>
                        )}
                      </div>
                    </td>

                    {/* Scheduled Date */}
                    <td className="maint-td-date">
                      <div className="maint-date-cell">
                        <span className="maint-date-icon">
                          <Icon type="calendar" size={13} />
                        </span>
                        <span>{formatDate(record.scheduled_at || record.scheduled_date)}</span>
                      </div>
                    </td>

                    {/* Technician */}
                    <td className="maint-td-tech">
                      <span className="maint-tech-badge">
                        {record.technician_name || record.technician || "Unassigned"}
                      </span>
                    </td>

                    {/* Status */}
                    <td className="maint-td-status">
                      <span
                        className="maint-status-pill"
                        style={{
                          backgroundColor: statusCfg.bg,
                          color: statusCfg.color,
                          borderColor: statusCfg.border,
                        }}
                      >
                        <span
                          className="maint-status-dot"
                          style={{ backgroundColor: statusCfg.color }}
                        />
                        {statusCfg.label}
                      </span>
                    </td>

                    {/* Actions */}
                    <td
                      className="maint-td-actions"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="maint-actions-group">
                        {/* View Details */}
                        <button
                          type="button"
                          className="maint-action-btn view"
                          onClick={() => onOpenDetails && onOpenDetails(record)}
                          title="View Details"
                          aria-label={`View details for record #${record.id}`}
                        >
                          <Icon type="eye" size={14} />
                        </button>

                        {/* Lifecycle Action */}
                        {(record.status === "scheduled" || record.status === "Scheduled") && onStatusChange && (
                          <button
                            type="button"
                            className="maint-action-btn start"
                            onClick={() => onStatusChange(record.id, "in_progress")}
                            title="Start Maintenance"
                            aria-label={`Start maintenance #${record.id}`}
                          >
                            <Icon type="play" size={13} />
                          </button>
                        )}

                        {(record.status === "in_progress" || record.status === "In Progress") && onOpenComplete && (
                          <button
                            type="button"
                            className="maint-action-btn complete"
                            onClick={() => onOpenComplete(record)}
                            title="Mark Completed"
                            aria-label={`Complete maintenance #${record.id}`}
                          >
                            <Icon type="check" size={13} />
                          </button>
                        )}

                        {/* More Menu Dropdown */}
                        <div className="maint-more-menu-wrapper">
                          <button
                            type="button"
                            className="maint-action-btn more"
                            onClick={() =>
                              setOpenMenuId(openMenuId === record.id ? null : record.id)
                            }
                            title="More Options"
                            aria-label="More options"
                            aria-expanded={openMenuId === record.id}
                          >
                            <Icon type="more-vertical" size={14} />
                          </button>

                          {openMenuId === record.id && (
                            <div
                              className="maint-context-menu"
                              ref={menuRef}
                              role="menu"
                            >
                              <button
                                type="button"
                                className="maint-context-item"
                                onClick={() => {
                                  setOpenMenuId(null);
                                  onOpenDetails && onOpenDetails(record);
                                }}
                                role="menuitem"
                              >
                                <Icon type="eye" size={13} />
                                <span>Inspect Details</span>
                              </button>

                              {onEdit && (
                                <button
                                  type="button"
                                  className="maint-context-item"
                                  onClick={() => {
                                    setOpenMenuId(null);
                                    onEdit(record);
                                  }}
                                  role="menuitem"
                                >
                                  <Icon type="edit" size={13} />
                                  <span>Edit Task</span>
                                </button>
                              )}

                              {record.status !== "Completed" &&
                                record.status !== "Cancelled" &&
                                onStatusChange && (
                                  <button
                                    type="button"
                                    className="maint-context-item danger"
                                    onClick={() => {
                                      setOpenMenuId(null);
                                      onStatusChange(record.id, "Cancelled");
                                    }}
                                    role="menuitem"
                                  >
                                    <span>Cancel Task</span>
                                  </button>
                                )}

                              {onDelete && (
                                <button
                                  type="button"
                                  className="maint-context-item danger"
                                  onClick={() => {
                                    setOpenMenuId(null);
                                    if (
                                      window.confirm(
                                        `Are you sure you want to delete maintenance record #${record.id}?`
                                      )
                                    ) {
                                      onDelete(record.id);
                                    }
                                  }}
                                  role="menuitem"
                                >
                                  <Icon type="trash" size={13} />
                                  <span>Delete Record</span>
                                </button>
                              )}
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

      {/* Pagination Footer */}
      <div className="maint-table-footer">
        <div className="maint-footer-left">
          <span className="maint-footer-range">
            Showing {totalCount === 0 ? 0 : startIndex + 1} to {endIndex} of{" "}
            {totalCount} records
          </span>
          <div className="maint-page-size-selector">
            <label htmlFor="maint-page-size">Per page:</label>
            <select
              id="maint-page-size"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setCurrentPage(1);
              }}
              className="maint-page-size-select"
            >
              <option value={10}>10</option>
              <option value={25}>25</option>
              <option value={50}>50</option>
            </select>
          </div>
        </div>

        <div className="maint-footer-right">
          <button
            type="button"
            className="maint-page-nav-btn"
            disabled={safeCurrentPage <= 1}
            onClick={() => handlePageChange(safeCurrentPage - 1)}
            aria-label="Previous page"
          >
            Previous
          </button>

          <div className="maint-page-numbers">
            {paginationItems.map((item, idx) =>
              item === "..." ? (
                <span key={`ellipsis-${idx}`} className="maint-page-ellipsis">
                  ...
                </span>
              ) : (
                <button
                  key={`page-${item}`}
                  type="button"
                  className={`maint-page-number-btn ${
                    item === safeCurrentPage ? "active" : ""
                  }`}
                  onClick={() => handlePageChange(item)}
                >
                  {item}
                </button>
              )
            )}
          </div>

          <button
            type="button"
            className="maint-page-nav-btn"
            disabled={safeCurrentPage >= totalPages}
            onClick={() => handlePageChange(safeCurrentPage + 1)}
            aria-label="Next page"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

export default MaintenanceTable;
