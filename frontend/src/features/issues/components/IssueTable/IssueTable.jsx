import { useState, useEffect, useRef } from "react";
import Icon from "../../../../components/ui/Icon";
import {
  formatDateTime,
  getPriorityBadgeConfig,
  getStatusBadgeConfig,
  getPaginationItems,
} from "../../utils/issueUtils";
import "./IssueTable.css";

function IssueTable({
  issues = [],
  selectedIssue = null,
  onSelectIssue,
  computerMap,
  onStatusChange,
  onOpenResolve,
  onEditIssue,
  onDeleteIssue,
  loading = false,
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [openMenuId, setOpenMenuId] = useState(null);
  const menuRef = useRef(null);

  // Close more menu when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpenMenuId(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const totalCount = issues.length;
  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const safeCurrentPage = Math.min(Math.max(1, currentPage), totalPages);
  const startIndex = (safeCurrentPage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalCount);
  const paginatedIssues = issues.slice(startIndex, endIndex);

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const handleRowClick = (issue) => {
    onSelectIssue(issue);
  };

  const paginationItems = getPaginationItems(safeCurrentPage, totalPages);

  return (
    <div className="issue-table-card" data-testid="issue-table-card">
      {/* CARD HEADER */}
      <div className="issue-table-header">
        <div className="issue-table-header-left">
          <div className="issue-table-header-icon">
            <Icon type="issue" size={18} />
          </div>
          <div>
            <h2 className="issue-table-header-title">Reported Issues</h2>
            <p className="issue-table-header-subtitle">
              Problems reported by client agents and administrators are displayed here.
            </p>
          </div>
        </div>
      </div>

      {/* TABLE SCROLL WRAPPER */}
      <div className="issue-table-wrapper">
        <table className="issue-data-table">
          <thead>
            <tr>
              <th className="issue-th-checkbox">
                <input
                  type="checkbox"
                  className="issue-checkbox"
                  checked={paginatedIssues.length > 0 && selectedIssue !== null}
                  onChange={() => {
                    if (selectedIssue) {
                      onSelectIssue(null);
                    } else if (paginatedIssues.length > 0) {
                      onSelectIssue(paginatedIssues[0]);
                    }
                  }}
                  aria-label="Select all"
                />
              </th>
              <th className="issue-th-computer">Computer</th>
              <th className="issue-th-issue">Issue</th>
              <th className="issue-th-priority">Priority</th>
              <th className="issue-th-status">Status</th>
              <th className="issue-th-reported">Reported</th>
              <th className="issue-th-actions">Actions</th>
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="issue-table-empty">
                  <div className="issue-table-loading-spinner" />
                  <p>Loading issues...</p>
                </td>
              </tr>
            ) : paginatedIssues.length === 0 ? (
              <tr>
                <td colSpan={7} className="issue-table-empty">
                  <div className="issue-table-empty-icon">📋</div>
                  <strong>No issues found matching your filters</strong>
                  <p style={{ marginTop: "4px", fontSize: "12px" }}>
                    Try clearing your search query or reset filters.
                  </p>
                </td>
              </tr>
            ) : (
              paginatedIssues.map((issue) => {
                const isSelected = selectedIssue?.id === issue.id;
                const compName =
                  issue.computer_hostname ||
                  (computerMap && computerMap.get ? computerMap.get(issue.computer_id) : null) ||
                  `Computer #${issue.computer_id}`;
                const priorityConfig = getPriorityBadgeConfig(issue.severity);
                const statusConfig = getStatusBadgeConfig(issue.status);
                const isMenuOpen = openMenuId === issue.id;

                return (
                  <tr
                    key={issue.id}
                    className={isSelected ? "selected" : ""}
                    onClick={() => handleRowClick(issue)}
                  >
                    {/* Checkbox */}
                    <td
                      className="issue-td-checkbox"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectIssue(isSelected ? null : issue);
                      }}
                    >
                      <input
                        type="checkbox"
                        className="issue-checkbox"
                        checked={isSelected}
                        onChange={() => {}}
                        aria-label={`Select issue ${issue.id}`}
                      />
                    </td>

                    {/* Computer */}
                    <td>
                      <div className="issue-cell-computer">
                        <span className="issue-cell-computer-icon">
                          <Icon type="computer" size={16} />
                        </span>
                        <span className="issue-cell-computer-name">{compName}</span>
                      </div>
                    </td>

                    {/* Issue Title & Description snippet */}
                    <td>
                      <div className="issue-cell-title-block">
                        <span className="issue-title-bold">{issue.title}</span>
                        <span className="issue-desc-snippet" title={issue.description}>
                          {issue.description}
                        </span>
                      </div>
                    </td>

                    {/* Priority */}
                    <td>
                      <span
                        className="issue-badge-priority"
                        style={{
                          background: priorityConfig.bg,
                          color: priorityConfig.color,
                          border: priorityConfig.border,
                        }}
                      >
                        {priorityConfig.label}
                      </span>
                    </td>

                    {/* Status */}
                    <td>
                      <span
                        className="issue-badge-status"
                        style={{
                          background: statusConfig.bg,
                          color: statusConfig.color,
                          border: statusConfig.border,
                        }}
                      >
                        <span
                          className="issue-status-dot"
                          style={{ background: statusConfig.dotColor }}
                        />
                        <span>{statusConfig.label}</span>
                      </span>
                    </td>

                    {/* Reported Timestamp */}
                    <td>
                      <span className="issue-cell-date">
                        {formatDateTime(issue.created_at)}
                      </span>
                    </td>

                    {/* Actions */}
                    <td>
                      <div
                        className="issue-cell-actions"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          type="button"
                          className="action-btn action-btn--view"
                          onClick={() => onSelectIssue(issue)}
                          title="View Details"
                          aria-label="View Details"
                        >
                          <Icon type="eye" size={15} />
                          <span className="sr-only">View</span>
                        </button>

                        {issue.status !== "resolved" && (
                          <button
                            type="button"
                            className="action-btn action-btn--resolve"
                            onClick={() => onOpenResolve(issue)}
                            title="Resolve Issue"
                            aria-label="Resolve Issue"
                          >
                            <Icon type="check" size={14} />
                          </button>
                        )}

                        <button
                          type="button"
                          className="action-btn action-btn--more"
                          onClick={() => setOpenMenuId(isMenuOpen ? null : issue.id)}
                          aria-label="More actions"
                          title="More actions"
                        >
                          <Icon type="more-vertical" size={15} />
                        </button>

                        {isMenuOpen && (
                          <div className="issue-dropdown-menu" ref={menuRef}>
                            {issue.status !== "in_progress" && (
                              <button
                                type="button"
                                className="issue-dropdown-item"
                                onClick={() => {
                                  setOpenMenuId(null);
                                  onStatusChange(issue, "in_progress");
                                }}
                              >
                                ▶ Start Working
                              </button>
                            )}

                            {issue.status !== "resolved" && (
                              <button
                                type="button"
                                className="issue-dropdown-item"
                                onClick={() => {
                                  setOpenMenuId(null);
                                  onOpenResolve(issue);
                                }}
                              >
                                ✓ Resolve Issue
                              </button>
                            )}

                            {issue.status === "resolved" && (
                              <button
                                type="button"
                                className="issue-dropdown-item"
                                onClick={() => {
                                  setOpenMenuId(null);
                                  onStatusChange(issue, "open");
                                }}
                              >
                                ↺ Reopen Issue
                              </button>
                            )}

                            <button
                              type="button"
                              className="issue-dropdown-item"
                              onClick={() => {
                                setOpenMenuId(null);
                                onEditIssue(issue);
                              }}
                            >
                              ✏ Edit Issue
                            </button>

                            <button
                              type="button"
                              className="issue-dropdown-item danger"
                              onClick={() => {
                                setOpenMenuId(null);
                                onDeleteIssue(issue);
                              }}
                            >
                              🗑 Delete Issue
                            </button>
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

      {/* CARD FOOTER PAGINATION */}
      <div className="issue-pagination-bar">
        <div className="issue-pagination-info">
          {`Showing ${totalCount > 0 ? startIndex + 1 : 0} to ${endIndex} of ${totalCount} issues`}
        </div>

        <div className="issue-pagination-controls">
          <button
            type="button"
            className="issue-pagination-btn"
            onClick={() => handlePageChange(1)}
            disabled={safeCurrentPage <= 1}
            title="First page"
            aria-label="First page"
          >
            «
          </button>
          <button
            type="button"
            className="issue-pagination-btn"
            onClick={() => handlePageChange(safeCurrentPage - 1)}
            disabled={safeCurrentPage <= 1}
            title="Previous page"
            aria-label="Previous page"
          >
            ‹
          </button>

          {paginationItems.map((item, idx) =>
            item === "..." ? (
              <span key={`el-${idx}`} className="issue-pagination-ellipsis" aria-hidden="true">
                ...
              </span>
            ) : (
              <button
                key={`p-${item}`}
                type="button"
                className={`issue-pagination-btn ${Number(item) === safeCurrentPage ? "active" : ""}`}
                onClick={() => handlePageChange(Number(item))}
                aria-label={`Page ${item}`}
                aria-current={Number(item) === safeCurrentPage ? "page" : undefined}
              >
                {item}
              </button>
            )
          )}

          <button
            type="button"
            className="issue-pagination-btn"
            onClick={() => handlePageChange(safeCurrentPage + 1)}
            disabled={safeCurrentPage >= totalPages}
            title="Next page"
            aria-label="Next page"
          >
            ›
          </button>
          <button
            type="button"
            className="issue-pagination-btn"
            onClick={() => handlePageChange(totalPages)}
            disabled={safeCurrentPage >= totalPages}
            title="Last page"
            aria-label="Last page"
          >
            »
          </button>

          <select
            className="issue-pagination-per-page"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value));
              setCurrentPage(1);
            }}
            aria-label="Issues per page"
          >
            <option value={10}>10 / page</option>
            <option value={25}>25 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>
      </div>
    </div>
  );
}

export default IssueTable;
