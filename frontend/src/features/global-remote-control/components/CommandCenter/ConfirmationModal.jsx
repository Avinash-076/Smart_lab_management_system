import Icon from "../../../../components/ui/Icon";
import "./ConfirmationModal.css";

export default function ConfirmationModal({
  isOpen,
  commandType,
  targets = [],
  onConfirm,
  onCancel,
  loading = false,
}) {
  if (!isOpen) return null;

  const getActionDetails = () => {
    switch (commandType) {
      case "lock":
        return {
          title: "Confirm Workstation Lock",
          verb: "Lock Workstations",
          colorClass: "amber",
          icon: "lock",
          warning:
            "This will lock the screen on all selected computers immediately. Users will need to enter their credentials to regain access.",
        };
      case "restart":
        return {
          title: "Confirm Computer Restart",
          verb: "Restart Computers",
          colorClass: "red",
          icon: "restart",
          warning:
            "This will restart the operating system on all selected computers. Unsaved user work may be lost.",
        };
      case "shutdown":
        return {
          title: "Confirm Computer Shutdown",
          verb: "Shutdown Computers",
          colorClass: "purple",
          icon: "shutdown",
          warning:
            "This will cleanly shut down the selected computers. They will need to be powered on physically or via Wake-on-LAN.",
        };
      default:
        return {
          title: "Confirm Remote Command",
          verb: "Execute Command",
          colorClass: "blue",
          icon: "play",
          warning: "Are you sure you want to execute this command?",
        };
    }
  };

  const action = getActionDetails();
  const offlineTargets = targets.filter(
    (t) => t.status?.toLowerCase() === "offline"
  );

  return (
    <div className="grc-modal-overlay" onClick={onCancel} role="dialog" aria-modal="true">
      <div className="grc-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className={`grc-modal-header ${action.colorClass}`}>
          <div className="grc-modal-icon">
            <Icon name={action.icon} size={22} />
          </div>
          <div className="grc-modal-header-text">
            <h3 className="grc-modal-title">{action.title}</h3>
            <span className="grc-modal-sub">
              Executing on {targets.length} target computer{targets.length > 1 ? "s" : ""}
            </span>
          </div>
          <button
            type="button"
            className="grc-modal-close-btn"
            onClick={onCancel}
            disabled={loading}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        <div className="grc-modal-body">
          <div className="grc-modal-warning-box">
            <Icon name="alert" size={18} />
            <p>{action.warning}</p>
          </div>

          <div className="grc-modal-targets-section">
            <label className="grc-modal-targets-label">
              Target Computers ({targets.length}):
            </label>
            <div className="grc-modal-targets-list">
              {targets.map((t) => {
                const isOnline = t.status?.toLowerCase() === "online";
                return (
                  <div key={t.id} className="grc-modal-target-item">
                    <span className="target-name">
                      {t.name || t.hostname || `PC-${t.id}`}
                    </span>
                    <span className="target-ip">({t.ip_address || t.hostname})</span>
                    <span className={`status-pill mini ${isOnline ? "online" : "offline"}`}>
                      <span className="status-dot" />
                      {isOnline ? "Online" : "Offline"}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          {offlineTargets.length > 0 && (
            <div className="grc-modal-offline-notice">
              <Icon name="info" size={16} />
              <span>
                <strong>Notice:</strong> {offlineTargets.length} offline computer
                {offlineTargets.length > 1 ? "s" : ""} will receive this command when
                they next connect to the server.
              </span>
            </div>
          )}
        </div>

        <div className="grc-modal-footer">
          <button
            type="button"
            className="grc-btn-secondary"
            onClick={onCancel}
            disabled={loading}
          >
            Cancel
          </button>
          <button
            type="button"
            className={`grc-btn-action ${action.colorClass}`}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? (
              <span className="spinner-text">Dispatching...</span>
            ) : (
              action.verb
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
