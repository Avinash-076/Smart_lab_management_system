import Icon from "../../../../components/ui/Icon";
import "./SoftwareHeader.css";

export default function SoftwareHeader({
  onRefresh,
  onExportReport,
  loading,
  lastRefreshedAt,
  successMsg,
  errorMsg,
}) {
  const formatTime = (date) => {
    if (!date) return "";
    return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div className="software-header-container">
      {/* Toast notifications */}
      {successMsg && (
        <div className="software-header-toast success">
          <Icon type="check" size={16} />
          <span>{successMsg}</span>
        </div>
      )}
      {errorMsg && (
        <div className="software-header-toast error">
          <Icon type="danger" size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="software-header-main">
        {/* Semantic Title & Subtitle for accessibility & test compatibility, hidden visually to avoid duplication with global Header */}
        <div className="sr-only">
          <h1 className="software-header-title">Software Inventory</h1>
          <p className="software-header-subtitle">
            Track and analyze software installations across all lab computers.
          </p>
        </div>

        <div className="software-header-actions">
          {lastRefreshedAt && (
            <span className="software-header-last-updated">
              Updated at {formatTime(lastRefreshedAt)}
            </span>
          )}

          <button
            type="button"
            className="software-header-refresh-btn"
            onClick={onRefresh}
            disabled={loading}
            title="Refresh software inventory"
          >
            <Icon type="refresh" size={16} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            className="software-header-export-btn"
            onClick={onExportReport}
          >
            <Icon type="download" size={16} />
            <span>Export Report</span>
          </button>
        </div>
      </div>
    </div>
  );
}
