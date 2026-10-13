import { useState } from "react";
import Icon from "../../../components/ui/Icon";
import "./DeleteConfirmModal.css";

function DeleteConfirmModal({ computer, onClose, onConfirm }) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  if (!computer) return null;

  const hostname = computer.hostname || computer.name || `PC-${computer.id}`;

  const handleDelete = async () => {
    try {
      setDeleting(true);
      setError("");
      await onConfirm(computer.id);
    } catch (err) {
      setError(err.message || "Failed to delete computer.");
      setDeleting(false);
    }
  };

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-dialog-title"
    >
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="delete-modal__header">
          <div className="delete-modal__icon">
            <Icon type="trash" size={20} />
          </div>
          <h2 id="delete-dialog-title" className="delete-modal__title">
            Delete Computer
          </h2>
        </div>

        <div className="delete-modal__body">
          <p>
            Are you sure you want to delete <strong>{hostname}</strong>?
          </p>
          <p style={{ marginTop: "8px", fontSize: "12.5px", color: "#64748b" }}>
            This action will permanently remove the computer record, its credentials, and
            associated telemetry history from the database.
          </p>
          {error && (
            <p style={{ color: "#dc2626", marginTop: "10px", fontSize: "12.5px" }}>
              {error}
            </p>
          )}
        </div>

        <div className="delete-modal__footer">
          <button
            type="button"
            className="btn-cancel"
            onClick={onClose}
            disabled={deleting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="btn-danger"
            onClick={handleDelete}
            disabled={deleting}
          >
            {deleting ? "Deleting..." : "Delete Computer"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default DeleteConfirmModal;
