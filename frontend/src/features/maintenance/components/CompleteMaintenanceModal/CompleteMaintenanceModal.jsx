import { useEffect } from "react";
import Icon from "../../../../components/ui/Icon";
import { formatDate } from "../../utils/maintenanceUtils";
import "./CompleteMaintenanceModal.css";

function CompleteMaintenanceModal({
  isOpen,
  onClose,
  record,
  workPerformed = "",
  onWorkPerformedChange,
  notes = "",
  onNotesChange,
  onSubmit,
  loading = false,
  error = "",
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

  const handleSubmit = (e) => {
    e.preventDefault();
    if (onSubmit) {
      onSubmit(e);
    }
  };

  const hostname =
    record.computer_hostname ||
    record.computer_name ||
    `Computer #${record.computer_id || "N/A"}`;

  return (
    <div
      className="maint-complete-overlay"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="maint-complete-card"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="maint-complete-header">
          <div className="maint-complete-header-left">
            <div className="maint-complete-header-icon">
              <Icon type="check" size={20} />
            </div>
            <div>
              <h2 className="maint-complete-title">Complete Maintenance</h2>
              <p className="maint-complete-subtitle">
                Log the work performed and record final servicing notes for #{record.id}.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="maint-complete-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Task Summary Banner */}
        <div className="maint-complete-summary">
          <div className="maint-complete-summary-item">
            <span className="summary-label">Target Computer:</span>
            <span className="summary-value highlight">{hostname}</span>
          </div>
          <div className="maint-complete-summary-item">
            <span className="summary-label">Task:</span>
            <span className="summary-value">{record.title}</span>
          </div>
          <div className="maint-complete-summary-item">
            <span className="summary-label">Scheduled Date:</span>
            <span className="summary-value">
              {formatDate(record.scheduled_at || record.scheduled_date)}
            </span>
          </div>
          <div className="maint-complete-summary-item">
            <span className="summary-label">Technician:</span>
            <span className="summary-value">
              {record.technician_name || record.technician || "Unassigned"}
            </span>
          </div>
        </div>

        {/* Form Body */}
        <form className="maint-complete-form" onSubmit={handleSubmit}>
          {error && <div className="maint-complete-error">{error}</div>}

          {/* Work Performed */}
          <div className="maint-complete-group">
            <label className="maint-complete-label" htmlFor="maint-work-performed">
              Work Performed / Service Summary <span className="maint-required">*</span>
            </label>
            <textarea
              id="maint-work-performed"
              className="maint-complete-textarea"
              rows={4}
              placeholder="Describe the actions taken (e.g. Replaced failed CPU cooling fan, reapplied thermal compound, verified BIOS temperature within 42°C threshold)..."
              value={workPerformed}
              onChange={(e) => onWorkPerformedChange && onWorkPerformedChange(e.target.value)}
              required
            />
          </div>

          {/* Notes / Follow-up */}
          <div className="maint-complete-group">
            <label className="maint-complete-label" htmlFor="maint-complete-notes">
              Follow-Up Notes &amp; Observations
            </label>
            <textarea
              id="maint-complete-notes"
              className="maint-complete-textarea"
              rows={3}
              placeholder="Optional notes, recommendations for next cycle, or parts replaced..."
              value={notes}
              onChange={(e) => onNotesChange && onNotesChange(e.target.value)}
            />
          </div>

          {/* Footer Actions */}
          <div className="maint-complete-actions">
            <button
              type="button"
              className="maint-complete-btn cancel"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="maint-complete-btn submit"
              disabled={loading}
            >
              {loading ? (
                <span>Completing...</span>
              ) : (
                <>
                  <Icon type="check" size={15} />
                  <span>Mark as Completed</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CompleteMaintenanceModal;
