import Icon from "../../../../components/ui/Icon";
import "./IssueHeader.css";

function IssueHeader({
  onReportClick,
  onExportCsv,
  onRefresh,
  loading = false,
  totalIssues = 0,
}) {
  return (
    <div className="issue-header" data-testid="issue-header">
      {/* Semantic Title & Subtitle for test compatibility & screen readers */}
      <div className="sr-only">
        <h1 className="issue-header-title">Issue Management</h1>
        <p className="issue-header-subtitle">
          Monitor and manage problems reported by laboratory computers.
        </p>
      </div>

      {/* Sleek Upper-Right Action Bar matching ComputersPage */}
      <div className="issue-top-actions">
        {onExportCsv && (
          <button
            type="button"
            className="issue-action-btn issue-action-btn--secondary"
            onClick={onExportCsv}
            disabled={totalIssues === 0}
            title="Export issue logs to CSV"
          >
            <Icon type="export" size={15} />
            <span>Export</span>
          </button>
        )}

        <button
          type="button"
          className="issue-action-btn issue-action-btn--primary"
          onClick={onReportClick}
          title="Report a new issue"
        >
          <Icon type="plus" size={15} />
          <span>Report Issue</span>
        </button>

        {onRefresh && (
          <button
            type="button"
            className="issue-action-btn issue-action-btn--secondary"
            onClick={onRefresh}
            disabled={loading}
            title="Refresh issues list"
          >
            <Icon
              type="refresh"
              size={15}
              className={loading ? "issue-spinning" : ""}
            />
            <span>Refresh</span>
          </button>
        )}
      </div>
    </div>
  );
}

export default IssueHeader;
