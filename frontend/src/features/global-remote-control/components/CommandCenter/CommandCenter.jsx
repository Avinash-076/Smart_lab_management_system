import { useState } from "react";
import Icon from "../../../../components/ui/Icon";
import ConfirmationModal from "./ConfirmationModal";
import "./CommandCenter.css";

const MAX_MESSAGE_LEN = 255;

export default function CommandCenter({
  selectedComputers = [],
  onClearSelection,
  onExecuteBatch,
  isExecuting = false,
}) {
  const [messageText, setMessageText] = useState("");
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    commandType: null,
  });
  const [feedback, setFeedback] = useState(null);

  const hasTargets = selectedComputers.length > 0;

  const showFeedback = (type, message) => {
    setFeedback({ type, message });
    setTimeout(() => {
      setFeedback(null);
    }, 6000);
  };

  const handleSendMessage = async () => {
    if (!hasTargets) return;
    const trimmed = messageText.trim();
    if (!trimmed) {
      showFeedback("error", "Please enter a message to send.");
      return;
    }
    if (trimmed.length > MAX_MESSAGE_LEN) {
      showFeedback(
        "error",
        `Message exceeds maximum limit of ${MAX_MESSAGE_LEN} characters.`
      );
      return;
    }

    try {
      const res = await onExecuteBatch("message", trimmed);
      setMessageText("");
      showFeedback(
        "success",
        `Dispatched message to ${res?.successful_count ?? selectedComputers.length} computer(s).`
      );
    } catch (err) {
      showFeedback("error", err?.message || "Failed to dispatch message.");
    }
  };

  const handleOpenConfirm = (commandType) => {
    if (!hasTargets) return;
    setConfirmModal({ isOpen: true, commandType });
  };

  const handleCloseConfirm = () => {
    if (isExecuting) return;
    setConfirmModal({ isOpen: false, commandType: null });
  };

  const handleConfirmAction = async () => {
    const cmdType = confirmModal.commandType;
    try {
      const res = await onExecuteBatch(cmdType, null);
      handleCloseConfirm();
      const count = res?.successful_count ?? selectedComputers.length;
      showFeedback(
        "success",
        `Successfully queued ${cmdType.toUpperCase()} on ${count} computer(s).`
      );
    } catch (err) {
      handleCloseConfirm();
      showFeedback("error", err?.message || `Failed to execute ${cmdType}.`);
    }
  };

  return (
    <div className="command-center-card" data-testid="command-center-section">
      {/* Header */}
      <div className="command-center-header">
        <div className="command-center-header-icon">
          <Icon name="play" size={20} />
        </div>
        <div>
          <h2 className="command-center-title">Command Center</h2>
          <p className="command-center-sub">
            Execute commands on the selected computers
          </p>
        </div>
      </div>

      {feedback && (
        <div className={`command-center-banner ${feedback.type}`}>
          <Icon
            name={feedback.type === "success" ? "check-circle" : "alert"}
            size={18}
          />
          <span>{feedback.message}</span>
          <button
            type="button"
            className="banner-close-btn"
            onClick={() => setFeedback(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Content: Left target summary + Right 4 action cards */}
      <div className="command-center-layout">
        {/* Left Target Summary */}
        <div className="selected-summary-panel">
          <div className="selected-summary-icon">
            <Icon name="users-group" size={26} />
          </div>
          <h3 className="selected-summary-count">
            {selectedComputers.length} computer
            {selectedComputers.length === 1 ? "" : "s"} selected
          </h3>

          {hasTargets ? (
            <>
              <div className="selected-targets-list">
                {selectedComputers.map((comp) => {
                  const isOnline = comp.status?.toLowerCase() === "online";
                  const name =
                    comp.name || comp.hostname?.toUpperCase() || `PC-${comp.id}`;
                  return (
                    <div key={comp.id} className="selected-target-pill">
                      <span
                        className={`target-dot ${
                          isOnline ? "online" : "offline"
                        }`}
                      />
                      <span className="target-pill-name">{name}</span>
                      <span className="target-pill-status">
                        ({isOnline ? "Online" : "Offline"})
                      </span>
                    </div>
                  );
                })}
              </div>
              <button
                type="button"
                className="clear-selection-btn"
                onClick={onClearSelection}
                disabled={isExecuting}
              >
                Clear Selection
              </button>
            </>
          ) : (
            <p className="selected-summary-placeholder">
              Select one or more computers from the table above to enable remote
              command execution.
            </p>
          )}
        </div>

        {/* Right: 4 Command Action Cards */}
        <div className="command-actions-grid">
          {/* Card 1: Send Message */}
          <div
            className={`command-action-card blue ${
              !hasTargets ? "card-disabled" : ""
            }`}
          >
            <div className="action-card-header">
              <div className="action-icon-box blue">
                <Icon name="message" size={18} />
              </div>
              <div className="action-header-text">
                <h4 className="action-title">Send Message</h4>
                <p className="action-sub">
                  Display a message on selected computers
                </p>
              </div>
            </div>

            <div className="message-textarea-wrapper">
              <textarea
                className="message-textarea"
                placeholder="Type your message here..."
                maxLength={MAX_MESSAGE_LEN}
                rows={3}
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                disabled={!hasTargets || isExecuting}
              />
              <div className="message-char-count">
                {messageText.length}/{MAX_MESSAGE_LEN}
              </div>
            </div>

            <button
              type="button"
              className="action-submit-btn blue"
              onClick={handleSendMessage}
              disabled={
                !hasTargets || !messageText.trim() || isExecuting
              }
            >
              <Icon name="play" size={14} />
              <span>
                {isExecuting ? "Sending..." : "Send Message"}
              </span>
            </button>
          </div>

          {/* Card 2: Lock Workstation */}
          <div
            className={`command-action-card amber ${
              !hasTargets ? "card-disabled" : ""
            }`}
          >
            <div className="action-card-header">
              <div className="action-icon-box amber">
                <Icon name="lock" size={18} />
              </div>
              <div className="action-header-text">
                <h4 className="action-title">Lock Workstation</h4>
                <p className="action-sub">
                  Lock the screen on selected computers
                </p>
              </div>
            </div>

            <div className="action-warning-banner amber">
              <Icon name="alert" size={16} />
              <span>
                This will immediately lock the selected workstations.
              </span>
            </div>

            <div className="action-spacer" />

            <button
              type="button"
              className="action-submit-btn amber"
              onClick={() => handleOpenConfirm("lock")}
              disabled={!hasTargets || isExecuting}
            >
              <Icon name="lock" size={14} />
              <span>Lock Workstations</span>
            </button>
          </div>

          {/* Card 3: Restart Computer */}
          <div
            className={`command-action-card red ${
              !hasTargets ? "card-disabled" : ""
            }`}
          >
            <div className="action-card-header">
              <div className="action-icon-box red">
                <Icon name="restart" size={18} />
              </div>
              <div className="action-header-text">
                <h4 className="action-title">Restart Computer</h4>
                <p className="action-sub">Restart the selected computers</p>
              </div>
            </div>

            <div className="action-warning-banner red">
              <Icon name="alert" size={16} />
              <span>This will restart the selected computers.</span>
            </div>

            <div className="action-spacer" />

            <button
              type="button"
              className="action-submit-btn red"
              onClick={() => handleOpenConfirm("restart")}
              disabled={!hasTargets || isExecuting}
            >
              <Icon name="restart" size={14} />
              <span>Restart Computers</span>
            </button>
          </div>

          {/* Card 4: Shutdown Computer */}
          <div
            className={`command-action-card purple ${
              !hasTargets ? "card-disabled" : ""
            }`}
          >
            <div className="action-card-header">
              <div className="action-icon-box purple">
                <Icon name="shutdown" size={18} />
              </div>
              <div className="action-header-text">
                <h4 className="action-title">Shutdown Computer</h4>
                <p className="action-sub">Shutdown the selected computers</p>
              </div>
            </div>

            <div className="action-warning-banner purple">
              <Icon name="alert" size={16} />
              <span>This will shutdown the selected computers.</span>
            </div>

            <div className="action-spacer" />

            <button
              type="button"
              className="action-submit-btn purple"
              onClick={() => handleOpenConfirm("shutdown")}
              disabled={!hasTargets || isExecuting}
            >
              <Icon name="shutdown" size={14} />
              <span>Shutdown Computers</span>
            </button>
          </div>
        </div>
      </div>

      {/* Confirmation Modal for destructive actions */}
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        commandType={confirmModal.commandType}
        targets={selectedComputers}
        onConfirm={handleConfirmAction}
        onCancel={handleCloseConfirm}
        loading={isExecuting}
      />
    </div>
  );
}
