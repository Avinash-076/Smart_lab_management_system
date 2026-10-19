import { useState } from "react";
import "./ResolveIssueModal.css";

function ResolveIssueModal({
  isOpen,
  issue,
  onClose,
  onSubmit,
  loading = false,
}) {
  const [notes, setNotes] = useState("");

  if (!isOpen || !issue) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(issue.id, notes.trim() || null);
    setNotes("");
  };

  return (
    <div className="resolve-modal-overlay" role="dialog" aria-modal="true">
      <div className="resolve-modal-card">
        <div className="resolve-modal-header">
          <h2 className="resolve-modal-title">{`Resolve Issue #${issue.id}`}</h2>
          <button
            type="button"
            className="report-modal-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        <form className="resolve-modal-form" onSubmit={handleSubmit}>
          <div style={{ fontSize: "13px", color: "#475569" }}>
            Marking issue <strong style={{ color: "#172033" }}>"{issue.title}"</strong> on{" "}
            <strong>{issue.computer_hostname || `Computer #${issue.computer_id}`}</strong> as resolved.
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label style={{ fontSize: "13px", fontWeight: "600", color: "#334155" }}>
              Resolution Notes (Optional)
            </label>
            <textarea
              className="resolve-modal-textarea"
              placeholder="Describe corrective actions taken, replaced components, or driver updates..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={5000}
            />
          </div>

          <div className="resolve-modal-actions">
            <button
              type="button"
              className="resolve-modal-cancel-btn"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="resolve-modal-submit-btn"
              disabled={loading}
            >
              {loading ? "Resolving..." : "Confirm Resolution"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default ResolveIssueModal;
