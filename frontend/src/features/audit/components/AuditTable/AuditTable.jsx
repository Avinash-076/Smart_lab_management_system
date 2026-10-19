import Icon from "../../../../components/ui/Icon";
import {
  formatDate,
  getActionBadgeClass,
  getOutcomeBadgeClass,
} from "../../utils/auditUtils";
import "./AuditTable.css";

function AuditTable({
  logs,
  totalCount,
  totalPages,
  page,
  setPage,
  limit,
  setLimit,
  loading,
  onInspect,
}) {
  return (
    <div className="audit-table-card" data-testid="audit-table">
      <div className="audit-table-wrapper">
        <table className="audit-data-table">
          <thead>
            <tr>
              <th className="audit-th-id">ID</th>
              <th className="audit-th-time">Timestamp</th>
              <th className="audit-th-actor">Actor Identity</th>
              <th className="audit-th-action">Action Code</th>
              <th className="audit-th-target">Target Resource</th>
              <th className="audit-th-outcome">Outcome</th>
              <th className="audit-th-ip">Source IP</th>
              <th className="audit-th-inspect">Inspect</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={8} className="audit-table-empty">
                  <div className="audit-loading-spinner-wrapper">
                    <Icon type="refresh" size={24} className="audit-spinning" />
                    <span>Loading audit records from database...</span>
                  </div>
                </td>
              </tr>
            ) : !logs || logs.length === 0 ? (
              <tr>
                <td colSpan={8} className="audit-table-empty">
                  <div className="audit-empty-content">
                    <Icon type="search" size={28} />
                    <p className="audit-empty-title">No audit records found</p>
                    <p className="audit-empty-desc">
                      Try adjusting your search keyword, outcome, or date range filters.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              logs.map((entry) => {
                const badgeClass = getActionBadgeClass(entry.action);
                const outcomeClass = getOutcomeBadgeClass(entry.result);
                return (
                  <tr key={entry.id} className="audit-table-row">
                    <td className="audit-td-id">#{entry.id}</td>
                    <td className="audit-td-time">{formatDate(entry.created_at)}</td>
                    <td className="audit-td-actor">
                      {entry.username ? (
                        <span className="audit-actor-user">{entry.username}</span>
                      ) : entry.user_id ? (
                        <span className="audit-actor-id">User #{entry.user_id}</span>
                      ) : (
                        <span className="audit-actor-system">SYSTEM / AGENT</span>
                      )}
                    </td>
                    <td className="audit-td-action">
                      <span className={`audit-badge ${badgeClass}`}>
                        {entry.action}
                      </span>
                    </td>
                    <td className="audit-td-target">
                      {entry.target_type ? (
                        <span className="audit-target-text">
                          {entry.target_type}
                          {entry.target_id !== null && entry.target_id !== undefined
                            ? ` (#${entry.target_id})`
                            : ""}
                        </span>
                      ) : (
                        <span className="audit-text-muted">—</span>
                      )}
                    </td>
                    <td className="audit-td-outcome">
                      <span className={`audit-outcome-badge ${outcomeClass}`}>
                        {entry.result}
                      </span>
                    </td>
                    <td className="audit-td-ip">
                      {entry.ip_address ? (
                        <span className="audit-ip-mono">{entry.ip_address}</span>
                      ) : (
                        <span className="audit-text-muted">—</span>
                      )}
                    </td>
                    <td className="audit-td-inspect">
                      <button
                        type="button"
                        className="audit-inspect-btn"
                        onClick={() => onInspect(entry.id)}
                        title={`Inspect audit record #${entry.id}`}
                      >
                        View
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
      <div className="audit-pagination-bar">
        <div className="audit-pagination-info">
          Showing <strong>{logs.length}</strong> of <strong>{totalCount}</strong> audit events (Page {page} of {totalPages})
        </div>

        <div className="audit-pagination-controls">
          <div className="audit-limit-selector-wrapper">
            <label htmlFor="audit-page-size" className="audit-limit-label">
              Rows:
            </label>
            <select
              id="audit-page-size"
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setPage(1);
              }}
              className="audit-limit-select"
            >
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
              <option value={100}>100 / page</option>
            </select>
          </div>

          <button
            type="button"
            className="audit-page-btn"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1 || loading}
          >
            Previous
          </button>

          <span className="audit-page-indicator">
            {page} / {totalPages}
          </span>

          <button
            type="button"
            className="audit-page-btn"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages || loading}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}

export default AuditTable;
