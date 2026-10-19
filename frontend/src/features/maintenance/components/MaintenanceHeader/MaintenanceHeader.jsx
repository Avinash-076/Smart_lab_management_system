import Icon from "../../../../components/ui/Icon";
import "./MaintenanceHeader.css";

function MaintenanceHeader({
  onScheduleClick,
  onExportCsv,
  onRefresh,
  loading = false,
  totalRecords = 0,
}) {
  return (
    <div className="maintenance-header" data-testid="maintenance-header">
      {/* Semantic Title & Subtitle for accessibility */}
      <div className="sr-only">
        <h1 className="maintenance-header-title">Maintenance Records</h1>
        <p className="maintenance-header-subtitle">
          Schedule, track, and manage computer maintenance and servicing activities.
        </p>
      </div>

      {/* Sleek Upper-Right Action Bar matching Computers & Issue Management */}
      <div className="maintenance-top-actions">
        {onExportCsv && (
          <button
            type="button"
            className="maintenance-action-btn maintenance-action-btn--secondary"
            onClick={onExportCsv}
            disabled={totalRecords === 0}
            title="Export maintenance logs to CSV"
          >
            <Icon type="export" size={15} />
            <span>Export</span>
          </button>
        )}

        <button
          type="button"
          className="maintenance-action-btn maintenance-action-btn--primary"
          onClick={onScheduleClick}
          title="Schedule a new maintenance task"
        >
          <Icon type="plus" size={15} />
          <span>Schedule Maintenance</span>
        </button>

        {onRefresh && (
          <button
            type="button"
            className="maintenance-action-btn maintenance-action-btn--secondary"
            onClick={onRefresh}
            disabled={loading}
            title="Refresh maintenance records"
          >
            <Icon
              type="refresh"
              size={15}
              className={loading ? "maintenance-spinning" : ""}
            />
            <span>Refresh</span>
          </button>
        )}
      </div>
    </div>
  );
}

export default MaintenanceHeader;
