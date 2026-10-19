import Icon from "../../../../components/ui/Icon";
import { formatDate } from "../../utils/reportUtils";
import "./ReportHeader.css";

function ReportHeader({
  onRefresh,
  onExport,
  loading,
  exporting,
  lastRefreshedAt,
  successMsg,
  errorMsg,
}) {
  return (
    <div className="report-header-container" data-testid="report-header">
      {/* Semantic Title & Subtitle for accessibility & screen readers (Shared layout Header provides visual title) */}
      <div className="sr-only">
        <h1 className="report-main-title">Reports & Analytics</h1>
        <p className="report-subtitle">
          Generate, inspect, and export system metrics, telemetry, and administrative logs.
        </p>
      </div>

      <div className="report-top-actions">
        <span className="report-live-pill">
          <span className="report-pulse-dot" />
          Live Database Connected
        </span>

        <div className="report-timestamp-badge">
          <Icon type="clock" size={14} />
          <span>Updated: {formatDate(lastRefreshedAt)}</span>
        </div>

        <button
          type="button"
          className="report-action-btn report-btn-secondary"
          onClick={onRefresh}
          disabled={loading || exporting}
          title="Refresh database records"
        >
          <Icon
            type="refresh"
            size={15}
            className={loading ? "report-spinning" : ""}
          />
          <span>{loading ? "Refreshing..." : "Refresh"}</span>
        </button>

        <button
          type="button"
          className="report-action-btn report-btn-primary"
          onClick={onExport}
          disabled={loading || exporting}
          title="Export full filtered dataset as sanitized CSV"
        >
          <Icon type="export" size={15} />
          <span>{exporting ? "Generating CSV..." : "Export CSV"}</span>
        </button>
      </div>

      {successMsg && (
        <div className="report-alert report-alert-success" role="status">
          <Icon type="check" size={18} />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="report-alert report-alert-error" role="alert">
          <Icon type="issue" size={18} />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}

export default ReportHeader;
