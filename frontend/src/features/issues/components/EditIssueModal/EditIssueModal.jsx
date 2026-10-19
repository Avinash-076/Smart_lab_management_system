import { useState } from "react";
import "./EditIssueModal.css";

function EditIssueModalForm({
  issue,
  onClose,
  onSubmit,
  loading = false,
}) {
  const [title, setTitle] = useState(issue?.title || "");
  const [description, setDescription] = useState(issue?.description || "");
  const [severity, setSeverity] = useState(issue?.severity || "medium");
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setError("Title cannot be empty.");
      return;
    }
    if (!description.trim()) {
      setError("Description cannot be empty.");
      return;
    }
    onSubmit(issue.id, {
      title: title.trim(),
      description: description.trim(),
      severity,
    });
  };

  return (
    <div className="report-modal-overlay" role="dialog" aria-modal="true">
      <div className="report-modal-card">
        <div className="report-modal-header">
          <h2 className="report-modal-title">{`Edit Issue #${issue.id}`}</h2>
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
            <label className="report-modal-label">Issue Title</label>
            <input
              type="text"
              className="report-modal-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={255}
            />
          </div>

          <div className="report-modal-group">
            <label className="report-modal-label">Priority Level</label>
            <select
              className="report-modal-select"
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div className="report-modal-group">
            <label className="report-modal-label">Description</label>
            <textarea
              className="report-modal-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
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
              {loading ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditIssueModal({
  isOpen,
  issue,
  onClose,
  onSubmit,
  loading = false,
}) {
  if (!isOpen || !issue) return null;

  return (
    <EditIssueModalForm
      key={issue.id}
      issue={issue}
      onClose={onClose}
      onSubmit={onSubmit}
      loading={loading}
    />
  );
}

export default EditIssueModal;
