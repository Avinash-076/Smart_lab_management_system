import { useState } from "react";
import "./ReportIssueModal.css";

function ReportIssueModal({
  isOpen,
  onClose,
  computers = [],
  onSubmit,
  loading = false,
}) {
  const [form, setForm] = useState({
    computer_id: "",
    title: "",
    description: "",
    severity: "medium",
  });
  const [error, setError] = useState("");

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!form.computer_id) {
      setError("Please select a computer.");
      return;
    }
    if (!form.title.trim()) {
      setError("Issue title is required.");
      return;
    }
    if (!form.description.trim()) {
      setError("Issue description is required.");
      return;
    }

    setError("");
    onSubmit({
      computer_id: Number(form.computer_id),
      title: form.title.trim(),
      description: form.description.trim(),
      severity: form.severity,
    });
  };

  return (
    <div className="report-modal-overlay" role="dialog" aria-modal="true">
      <div className="report-modal-card">
        <div className="report-modal-header">
          <h2 className="report-modal-title">Report New Issue</h2>
          <button
            type="button"
            className="report-modal-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        <form className="report-modal-form" onSubmit={handleSubmit}>
          {error && <div className="report-modal-error">{error}</div>}

          <div className="report-modal-group">
            <label className="report-modal-label" htmlFor="issue-computer">
              Target Computer *
            </label>
            <select
              id="issue-computer"
              className="report-modal-select"
              value={form.computer_id}
              onChange={(e) => setForm({ ...form, computer_id: e.target.value })}
            >
              <option value="">Select a laboratory computer...</option>
              {computers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.hostname || `Computer #${c.id}`} ({c.ip_address || "No IP"})
                </option>
              ))}
            </select>
          </div>

          <div className="report-modal-group">
            <label className="report-modal-label" htmlFor="issue-title">
              Issue Title *
            </label>
            <input
              id="issue-title"
              type="text"
              className="report-modal-input"
              placeholder="e.g. Monitor display flicker or overheating"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              maxLength={255}
            />
          </div>

          <div className="report-modal-group">
            <label className="report-modal-label" htmlFor="issue-severity">
              Priority Level *
            </label>
            <select
              id="issue-severity"
              className="report-modal-select"
              value={form.severity}
              onChange={(e) => setForm({ ...form, severity: e.target.value })}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div className="report-modal-group">
            <label className="report-modal-label" htmlFor="issue-description">
              Problem Description *
            </label>
            <textarea
              id="issue-description"
              className="report-modal-textarea"
              placeholder="Describe symptoms, error codes, physical anomalies, or reproduction steps..."
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              maxLength={5000}
            />
          </div>

          <div className="report-modal-actions">
            <button
              type="button"
              className="report-modal-cancel-btn"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="report-modal-submit-btn"
              disabled={loading}
            >
              {loading ? "Reporting..." : "Submit Report"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ReportIssueModal;
