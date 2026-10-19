import Icon from "../../../../components/ui/Icon";
import { formatDate } from "../../utils/auditUtils";
import "./AuditHeader.css";

function AuditHeader({
  onRefresh,
  onExport,
  loading,
  exporting,
  lastRefreshedAt,
  successMsg,
  errorMsg,
}) {
  return (
    <div className="audit-header-container" data-testid="audit-header">
      {/* Semantic Title & Subtitle for accessibility & screen readers (Header.jsx provides visual title) */}
      <div className="sr-only">
        <h1 className="audit-main-title">Audit Logs</h1>
        <p className="audit-subtitle">
          Complete traceability and security audit trail for all operations across the laboratory.
        </p>
      </div>

      {/* Sleek Upper-Right Action Bar matching other tabs */}
      <div className="audit-top-actions">
        <span className="audit-live-pill" title="Live database audit trail active">
          <span className="audit-pulse-dot" />
          Live Audit Stream
        </span>

        <div className="audit-timestamp-badge" title="Timestamp of last data fetch">
          <Icon type="clock" size={14} />
          <span>Updated: {formatDate(lastRefreshedAt)}</span>
        </div>

        <button
          type="button"
          className="audit-action-btn audit-btn-secondary"
          onClick={onRefresh}
          disabled={loading || exporting}
          title="Refresh audit event records"
        >
          <Icon
            type="refresh"
            size={15}
            className={loading ? "audit-spinning" : ""}
          />
          <span>{loading ? "Refreshing..." : "Refresh"}</span>
        </button>

        <button
          type="button"
          className="audit-action-btn audit-btn-primary"
          onClick={onExport}
          disabled={loading || exporting}
          title="Export filtered audit logs as sanitized CSV"
        >
          <Icon type="export" size={15} />
          <span>{exporting ? "Generating CSV..." : "Export CSV"}</span>
        </button>
      </div>

      {successMsg && (
        <div className="audit-alert audit-alert-success" role="status">
          <Icon type="check" size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="audit-alert audit-alert-error" role="alert">
          <Icon type="issue" size={18} />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}

export default AuditHeader;
