import { useEffect } from "react";
import Icon from "../../../../components/ui/Icon";
import {
  formatDateTime,
  getMaintenanceStatusConfig,
  getMaintenanceTypeConfig,
} from "../../utils/maintenanceUtils";
import "./MaintenanceDetailsModal.css";

function MaintenanceDetailsModal({
  isOpen,
  onClose,
  record,
  onStartMaintenance,
  onOpenComplete,
}) {
  useEffect(() => {
    if (!isOpen) return;
    function handleKeyDown(e) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !record) return null;

  const hostname =
    record.computer_hostname ||
    record.computer_name ||
    `Computer #${record.computer_id || "N/A"}`;
  const statusCfg = getMaintenanceStatusConfig(record.status);
  const typeCfg = getMaintenanceTypeConfig(record.maintenance_type);

  return (
    <div
      className="maint-details-overlay"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="maint-details-card"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="maint-details-header">
          <div className="maint-details-header-left">
            <span className="maint-details-id-tag">#{record.id}</span>
            <span
              className="maint-details-type-pill"
              style={{
                backgroundColor: typeCfg.bg,
                color: typeCfg.color,
                borderColor: typeCfg.border,
              }}
            >
              {typeCfg.label}
            </span>
            <span
              className="maint-details-status-pill"
              style={{
                backgroundColor: statusCfg.bg,
                color: statusCfg.color,
                borderColor: statusCfg.border,
              }}
            >
              <span
                className="maint-details-dot"
                style={{ backgroundColor: statusCfg.color }}
              />
              {statusCfg.label}
            </span>
          </div>

          <button
            type="button"
            className="maint-details-close-btn"
            onClick={onClose}
            aria-label="Close details"
          >
            ✕
          </button>
        </div>

        {/* Content Body */}
        <div className="maint-details-body">
          {/* Title */}
          <h2 className="maint-details-title">{record.title}</h2>

          {/* Quick Info Grid */}
          <div className="maint-details-grid">
            <div className="maint-details-item">
              <span className="maint-item-label">Target Computer</span>
              <div className="maint-item-val computer-val">
                <Icon type="computer" size={14} />
                <span>{hostname}</span>
              </div>
            </div>

            <div className="maint-details-item">
              <span className="maint-item-label">Assigned Technician</span>
              <div className="maint-item-val">
                <Icon type="user" size={14} />
                <span>{record.technician_name || record.technician || "Unassigned"}</span>
              </div>
            </div>

            <div className="maint-details-item">
              <span className="maint-item-label">Scheduled Date</span>
              <div className="maint-item-val">
                <Icon type="calendar" size={14} />
                <span>
                  {formatDateTime(record.scheduled_at || record.scheduled_date)}
                </span>
              </div>
            </div>

            <div className="maint-details-item">
              <span className="maint-item-label">Started At</span>
              <div className="maint-item-val">
                <Icon type="clock" size={14} />
                <span>{formatDateTime(record.started_at)}</span>
              </div>
            </div>

            <div className="maint-details-item">
              <span className="maint-item-label">Completed At</span>
              <div className="maint-item-val">
                <Icon type="check" size={14} />
                <span>{formatDateTime(record.completed_at)}</span>
              </div>
            </div>

            <div className="maint-details-item">
              <span className="maint-item-label">Recorded In Database</span>
              <div className="maint-item-val">
                <Icon type="audit" size={14} />
                <span>{formatDateTime(record.created_at)}</span>
              </div>
            </div>
          </div>

          {/* Task Description */}
          <div className="maint-details-section">
            <h3 className="maint-section-heading">Task Description &amp; Scope</h3>
            <div className="maint-section-box">
              {record.description ? (
                <p className="maint-text-content">{record.description}</p>
              ) : (
                <p className="maint-text-empty">No additional description provided.</p>
              )}
            </div>
          </div>

          {/* Work Performed (if any) */}
          <div className="maint-details-section">
            <h3 className="maint-section-heading">Work Performed</h3>
            <div className="maint-section-box highlight">
              {record.work_performed ? (
                <p className="maint-text-content">{record.work_performed}</p>
              ) : (
                <p className="maint-text-empty">
                  Work has not been completed or logged yet.
                </p>
              )}
            </div>
          </div>

          {/* Follow-up Notes & Replaced Parts */}
          {(record.notes || record.parts_replaced) && (
            <div className="maint-details-section">
              <h3 className="maint-section-heading">Observations &amp; Replaced Parts</h3>
              <div className="maint-section-box">
                {record.parts_replaced && (
                  <p className="maint-text-content" style={{ marginBottom: "0.5rem" }}>
                    <strong>Parts Replaced:</strong> {record.parts_replaced}
                  </p>
                )}
                {record.notes && (
                  <p className="maint-text-content">{record.notes}</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="maint-details-footer">
          <div className="maint-details-footer-left">
            {(record.status === "scheduled" || record.status === "Scheduled") &&
              onStartMaintenance && (
                <button
                  type="button"
                  className="maint-footer-action-btn start"
                  onClick={() => {
                    onClose();
                    onStartMaintenance(record.id);
                  }}
                >
                  <Icon type="play" size={14} />
                  <span>Start Maintenance</span>
                </button>
              )}

            {(record.status === "in_progress" || record.status === "In Progress") &&
              onOpenComplete && (
                <button
                  type="button"
                  className="maint-footer-action-btn complete"
                  onClick={() => {
                    onClose();
                    onOpenComplete(record);
                  }}
                >
                  <Icon type="check" size={14} />
                  <span>Mark Completed</span>
                </button>
              )}
          </div>

          <button
            type="button"
            className="maint-details-btn-close"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default MaintenanceDetailsModal;
