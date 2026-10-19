import { useState, useEffect } from "react";
import Icon from "../../../../components/ui/Icon";
import "./ScheduleMaintenanceModal.css";

function ScheduleMaintenanceModal({
  isOpen,
  onClose,
  computers = [],
  onSubmit,
  initialData = null,
  loading = false,
  error: externalError = "",
}) {
  const [form, setForm] = useState(() => ({
    computer_id: initialData?.computer_id || "",
    title: initialData?.title || "",
    maintenance_type: initialData?.maintenance_type || "Preventive",
    scheduled_date:
      initialData?.scheduled_at || initialData?.scheduled_date
        ? String(initialData.scheduled_at || initialData.scheduled_date).slice(0, 10)
        : new Date().toISOString().slice(0, 10),
    technician: initialData?.technician_name || initialData?.technician || "",
    cost: initialData?.cost != null ? String(initialData.cost) : "",
    description: initialData?.description || "",
  }));
  const [internalError, setInternalError] = useState("");
  const error = externalError || internalError;
  const setError = setInternalError;

  // Handle ESC key
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

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.computer_id) {
      setError("Please select a target computer.");
      return;
    }
    if (!form.title.trim()) {
      setError("Please provide a maintenance task title.");
      return;
    }
    if (!form.scheduled_date) {
      setError("Please select a scheduled date.");
      return;
    }

    setError("");
    const payload = {
      computer_id: Number(form.computer_id),
      title: form.title.trim(),
      maintenance_type: form.maintenance_type.toLowerCase(),
      scheduled_at: form.scheduled_date
        ? new Date(form.scheduled_date).toISOString()
        : new Date().toISOString(),
      technician_name: form.technician.trim() || null,
      description: form.description.trim() || null,
    };

    onSubmit(payload);
  };

  return (
    <div
      className="maint-modal-overlay"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className="maint-modal-card"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="maint-modal-header">
          <div className="maint-modal-header-left">
            <div className="maint-modal-header-icon">
              <Icon type="maintenance" size={20} />
            </div>
            <div>
              <h2 className="maint-modal-title">
                {initialData ? "Edit Maintenance Record" : "Schedule Maintenance"}
              </h2>
              <p className="maint-modal-subtitle">
                {initialData
                  ? `Update maintenance task details for #${initialData.id}`
                  : "Plan preventative servicing, hardware inspection, or repairs."}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="maint-modal-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Form */}
        <form className="maint-modal-form" onSubmit={handleSubmit}>
          {error && <div className="maint-modal-error-banner">{error}</div>}

          {/* Computer & Type */}
          <div className="maint-modal-grid-2">
            <div className="maint-modal-group">
              <label className="maint-modal-label" htmlFor="maint-computer-select">
                Target Computer <span className="maint-required">*</span>
              </label>
              <select
                id="maint-computer-select"
                className="maint-modal-select"
                value={form.computer_id}
                onChange={(e) => setForm({ ...form, computer_id: e.target.value })}
                required
              >
                <option value="">Select a lab computer...</option>
                {computers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.hostname || `Computer #${c.id}`} ({c.ip_address || "No IP"})
                  </option>
                ))}
              </select>
            </div>

            <div className="maint-modal-group">
              <label className="maint-modal-label" htmlFor="maint-type-select">
                Maintenance Type <span className="maint-required">*</span>
              </label>
              <select
                id="maint-type-select"
                className="maint-modal-select"
                value={form.maintenance_type}
                onChange={(e) =>
                  setForm({ ...form, maintenance_type: e.target.value })
                }
              >
                <option value="Preventive">Preventive (Routine Checkup)</option>
                <option value="Corrective">Corrective (Fixing Defect)</option>
                <option value="Emergency">Emergency (Immediate)</option>
                <option value="Hardware">Hardware (Part Servicing)</option>
                <option value="Software">Software (OS / Driver / Patch)</option>
              </select>
            </div>
          </div>

          {/* Title */}
          <div className="maint-modal-group">
            <label className="maint-modal-label" htmlFor="maint-title-input">
              Task Title <span className="maint-required">*</span>
            </label>
            <input
              id="maint-title-input"
              type="text"
              className="maint-modal-input"
              placeholder="e.g. Clean dust filters, re-apply thermal paste, verify RAM"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
          </div>

          {/* Date, Technician, Cost */}
          <div className="maint-modal-grid-3">
            <div className="maint-modal-group">
              <label className="maint-modal-label" htmlFor="maint-date-input">
                Scheduled Date <span className="maint-required">*</span>
              </label>
              <input
                id="maint-date-input"
                type="date"
                className="maint-modal-input"
                value={form.scheduled_date}
                onChange={(e) =>
                  setForm({ ...form, scheduled_date: e.target.value })
                }
                required
              />
            </div>

            <div className="maint-modal-group">
              <label className="maint-modal-label" htmlFor="maint-tech-input">
                Assigned Technician
              </label>
              <input
                id="maint-tech-input"
                type="text"
                className="maint-modal-input"
                placeholder="e.g. John Doe, Lab Tech"
                value={form.technician}
                onChange={(e) => setForm({ ...form, technician: e.target.value })}
              />
            </div>

            <div className="maint-modal-group">
              <label className="maint-modal-label" htmlFor="maint-cost-input">
                Est. Cost ($)
              </label>
              <input
                id="maint-cost-input"
                type="number"
                step="0.01"
                min="0"
                className="maint-modal-input"
                placeholder="0.00"
                value={form.cost}
                onChange={(e) => setForm({ ...form, cost: e.target.value })}
              />
            </div>
          </div>

          {/* Description */}
          <div className="maint-modal-group">
            <label className="maint-modal-label" htmlFor="maint-desc-textarea">
              Task Description &amp; Scope
            </label>
            <textarea
              id="maint-desc-textarea"
              className="maint-modal-textarea"
              rows={4}
              placeholder="Outline specific instructions, safety precautions, or inspection checklist..."
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>

          {/* Footer Actions */}
          <div className="maint-modal-actions">
            <button
              type="button"
              className="maint-modal-btn cancel"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="maint-modal-btn submit"
              disabled={loading}
            >
              {loading ? (
                <span>Saving...</span>
              ) : initialData ? (
                <span>Save Changes</span>
              ) : (
                <span>Schedule Maintenance</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ScheduleMaintenanceModal;
