import { useState } from "react";
import "./DashboardCommandModals.css";

export default function DashboardCommandModals({
  modalType, // 'select_prompt' | 'confirm_command' | 'send_message' | null
  actionType, // 'restart' | 'shutdown' | 'lock' | 'message'
  selectedComputers = [],
  onConfirm,
  onClose,
}) {
  const [messageText, setMessageText] = useState("");

  if (!modalType) return null;

  // 1. Prompt user to select computers if none were selected
  if (modalType === "select_prompt") {
    return (
      <div className="dash-modal-overlay" onClick={onClose}>
        <div className="dash-modal-dialog" onClick={(e) => e.stopPropagation()}>
          <div className="dash-modal-header">
            <div className="dash-modal-badge badge-warning">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <div>
              <h3 className="dash-modal-title">Select Target Computers</h3>
              <p className="dash-modal-sub">
                No computers are currently selected.
              </p>
            </div>
          </div>

          <div className="dash-modal-body">
            <p>
              Please check one or more computers in the <strong>Live System Status</strong> table below to execute this quick action safely.
            </p>
          </div>

          <div className="dash-modal-footer">
            <button
              type="button"
              className="dash-modal-btn btn-primary"
              onClick={onClose}
            >
              Got it
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 2. Send Message Modal
  if (modalType === "send_message") {
    const handleSend = (e) => {
      e.preventDefault();
      if (!messageText.trim()) return;
      onConfirm(actionType, messageText.trim());
    };

    return (
      <div className="dash-modal-overlay" onClick={onClose}>
        <div className="dash-modal-dialog" onClick={(e) => e.stopPropagation()}>
          <form onSubmit={handleSend}>
            <div className="dash-modal-header">
              <div className="dash-modal-badge badge-green">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <div>
                <h3 className="dash-modal-title">Send Broadcast Message</h3>
                <p className="dash-modal-sub">
                  Targeting {selectedComputers.length} selected computer(s)
                </p>
              </div>
            </div>

            <div className="dash-modal-body">
              <label className="dash-modal-field-label">Message Content</label>
              <textarea
                className="dash-modal-textarea"
                rows={4}
                placeholder="Enter message to display on student monitors..."
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                autoFocus
                required
              />
              <div className="dash-targets-list">
                {selectedComputers.map((c) => (
                  <span key={c.id} className="dash-target-tag">
                    {c.hostname || `PC-${c.id}`}
                  </span>
                ))}
              </div>
            </div>

            <div className="dash-modal-footer">
              <button
                type="button"
                className="dash-modal-btn btn-secondary"
                onClick={onClose}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="dash-modal-btn btn-success"
                disabled={!messageText.trim()}
              >
                Send Message
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  // 3. Confirm Command Modal (Restart, Shutdown, Lock)
  const isDestructive = actionType === "shutdown" || actionType === "restart";
  const actionTitle =
    actionType === "restart"
      ? "Restart Computers"
      : actionType === "shutdown"
      ? "Shutdown Computers"
      : "Lock Computers";

  return (
    <div className="dash-modal-overlay" onClick={onClose}>
      <div className="dash-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dash-modal-header">
          <div
            className={`dash-modal-badge ${
              actionType === "shutdown"
                ? "badge-danger"
                : actionType === "restart"
                ? "badge-primary"
                : "badge-warning"
            }`}
          >
            {actionType === "shutdown" ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
                <line x1="12" y1="2" x2="12" y2="12" />
              </svg>
            ) : actionType === "restart" ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
              </svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            )}
          </div>
          <div>
            <h3 className="dash-modal-title">{actionTitle}</h3>
            <p className="dash-modal-sub">
              Affects {selectedComputers.length} selected computer(s)
            </p>
          </div>
        </div>

        <div className="dash-modal-body">
          <p>
            Are you sure you want to execute <strong>{actionType.toUpperCase()}</strong> on the following machines?
          </p>
          <div className="dash-targets-list">
            {selectedComputers.map((c) => (
              <span key={c.id} className="dash-target-tag">
                {c.hostname || `PC-${c.id}`}
              </span>
            ))}
          </div>
          {isDestructive && (
            <div className="dash-modal-alert-box">
              ⚠️ Any unsaved work on these computers will be closed.
            </div>
          )}
        </div>

        <div className="dash-modal-footer">
          <button
            type="button"
            className="dash-modal-btn btn-secondary"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className={`dash-modal-btn ${isDestructive ? "btn-danger" : "btn-primary"}`}
            onClick={() => onConfirm(actionType)}
          >
            Confirm {actionTitle.split(" ")[0]}
          </button>
        </div>
      </div>
    </div>
  );
}
