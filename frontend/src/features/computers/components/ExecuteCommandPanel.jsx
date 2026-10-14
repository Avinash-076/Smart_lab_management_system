import { useState } from "react";
import "./ExecuteCommandPanel.css";

const COMMANDS = [
  {
    id: "message",
    title: "Send Message",
    desc: "Display a message to logged in users",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        <line x1="9" y1="10" x2="15" y2="10" />
      </svg>
    ),
  },
  {
    id: "lock",
    title: "Lock Workstation",
    desc: "Lock the computer screen",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    ),
  },
  {
    id: "restart",
    title: "Restart Computer",
    desc: "Restart the computer (5 seconds delay)",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 4 23 10 17 10" />
        <polyline points="1 20 1 14 7 14" />
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
      </svg>
    ),
  },
  {
    id: "shutdown",
    title: "Shutdown Computer",
    desc: "Shutdown the computer (5 seconds delay)",
    icon: (
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
        <line x1="12" y1="2" x2="12" y2="12" />
      </svg>
    ),
  },
];

export default function ExecuteCommandPanel({
  isOnline = false,
  onExecute,
  executing = false,
}) {
  const [selectedCommand, setSelectedCommand] = useState("message");
  const [messageText, setMessageText] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', text: string }

  const handleSelectCommand = (cmdId) => {
    setSelectedCommand(cmdId);
    setConfirmed(false);
    setFeedback(null);
  };

  const handleClear = () => {
    setMessageText("");
    setFeedback(null);
  };

  const handleSubmit = async (e) => {
    e?.preventDefault();
    setFeedback(null);

    let payload = null;
    if (selectedCommand === "message") {
      const trimmed = messageText.trim();
      if (!trimmed) {
        setFeedback({ type: "error", text: "Please enter a message to display." });
        return;
      }
      payload = trimmed.slice(0, 255);
    } else if (selectedCommand === "restart" || selectedCommand === "shutdown") {
      if (!confirmed) {
        setFeedback({
          type: "error",
          text: `Please check the confirmation box before issuing ${selectedCommand}.`,
        });
        return;
      }
    }

    try {
      const res = await onExecute({
        command_type: selectedCommand,
        payload,
      });

      const statusText = res?.status ? `(Status: ${res.status})` : "";
      setFeedback({
        type: "success",
        text: `Command "${selectedCommand.toUpperCase()}" dispatched successfully ${statusText}.`,
      });

      if (selectedCommand === "message") {
        setMessageText("");
      }
      setConfirmed(false);
    } catch (err) {
      setFeedback({
        type: "error",
        text: err?.message || `Failed to dispatch ${selectedCommand} command.`,
      });
    }
  };

  return (
    <div className="execute-command-card" id="execute-command-panel">
      {/* Panel Header */}
      <div className="execute-card-header">
        <div className="execute-title-group">
          <div className="execute-icon-badge">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="4 17 10 11 4 5" />
              <line x1="12" y1="19" x2="20" y2="19" />
            </svg>
          </div>
          <div>
            <h2 className="execute-title">Execute Command</h2>
            <p className="execute-subtitle">
              Send predefined remote commands to this computer. Commands are executed by the client agent.
            </p>
          </div>
        </div>

        <div className="execute-status-indicator">
          <span className={`status-dot ${isOnline ? "online" : "offline"}`} />
          <span className="status-text">
            {isOnline ? "Computer is online" : "Computer is offline"}
          </span>
        </div>
      </div>

      {/* Command Selector */}
      <div className="command-selector-section">
        <label className="section-field-label">Select Command</label>
        <div className="command-options-grid">
          {COMMANDS.map((cmd) => {
            const isSelected = selectedCommand === cmd.id;
            return (
              <button
                key={cmd.id}
                type="button"
                className={`command-option-card ${isSelected ? "selected" : ""}`}
                onClick={() => handleSelectCommand(cmd.id)}
                disabled={executing}
              >
                <div className="command-option-icon">{cmd.icon}</div>
                <div className="command-option-content">
                  <span className="command-option-title">{cmd.title}</span>
                  <span className="command-option-desc">{cmd.desc}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Feedback Banner */}
      {feedback && (
        <div className={`execute-feedback-banner ${feedback.type}`}>
          <span className="feedback-icon">
            {feedback.type === "success" ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            ) : (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            )}
          </span>
          <span className="feedback-text">{feedback.text}</span>
          <button
            type="button"
            className="feedback-close"
            onClick={() => setFeedback(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* Command Form / Details Area */}
      <form onSubmit={handleSubmit} className="command-form-container">
        {selectedCommand === "message" ? (
          <div className="message-command-layout">
            <div className="message-input-column">
              <label htmlFor="message-text" className="section-field-label">
                Message Text
              </label>
              <textarea
                id="message-text"
                className="message-textarea"
                rows={4}
                maxLength={255}
                value={messageText}
                onChange={(e) => setMessageText(e.target.value)}
                placeholder="Enter message to display on the computer..."
                disabled={executing}
              />
              <div className="char-counter-row">
                <span className="char-counter">{messageText.length}/255</span>
              </div>
            </div>

            <div className="message-info-box">
              <div className="info-box-header">
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#0284c7"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
              </div>
              <ul className="info-bullets">
                <li>The message will be shown to all logged in users on the computer.</li>
                <li>Use clear and appropriate messages.</li>
                <li>This action will not close any applications.</li>
              </ul>
            </div>
          </div>
        ) : selectedCommand === "lock" ? (
          <div className="action-confirm-box lock-box">
            <div className="confirm-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
            </div>
            <div className="confirm-text">
              <h4>Lock Workstation</h4>
              <p>
                This command calls <code>LockWorkStation()</code> on the target computer. The current user session will be immediately locked and require authentication to resume.
              </p>
            </div>
          </div>
        ) : selectedCommand === "restart" ? (
          <div className="action-confirm-box warning-box">
            <div className="confirm-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#d97706" strokeWidth="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </div>
            <div className="confirm-text">
              <h4>Restart Workstation</h4>
              <p>
                The system will schedule a reboot in 5 seconds (<code>shutdown /r /t 5</code>).
                Restarting will disconnect active users and may cause unsaved data loss.
              </p>
              <label className="confirm-checkbox-label">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                  disabled={executing}
                />
                <span>I understand that active user sessions will be interrupted.</span>
              </label>
            </div>
          </div>
        ) : (
          <div className="action-confirm-box danger-box">
            <div className="confirm-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2">
                <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
                <line x1="12" y1="2" x2="12" y2="12" />
              </svg>
            </div>
            <div className="confirm-text">
              <h4>Shutdown Workstation</h4>
              <p>
                The computer will schedule a full power-off in 5 seconds (<code>shutdown /s /t 5</code>).
                Once turned off, the machine will go offline and require physical power-on.
              </p>
              <label className="confirm-checkbox-label">
                <input
                  type="checkbox"
                  checked={confirmed}
                  onChange={(e) => setConfirmed(e.target.checked)}
                  disabled={executing}
                />
                <span>I confirm shutting down this workstation.</span>
              </label>
            </div>
          </div>
        )}

        {/* Buttons Row */}
        <div className="execute-actions-bar">
          <button
            type="submit"
            className={`execute-submit-btn ${selectedCommand}`}
            disabled={
              executing ||
              (selectedCommand === "message" && !messageText.trim()) ||
              ((selectedCommand === "restart" || selectedCommand === "shutdown") && !confirmed)
            }
          >
            {executing ? (
              <>
                <span className="spinner-inline" />
                Dispatching...
              </>
            ) : selectedCommand === "message" ? (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
                Send Message
              </>
            ) : selectedCommand === "lock" ? (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                Lock Workstation Now
              </>
            ) : selectedCommand === "restart" ? (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <polyline points="23 4 23 10 17 10" />
                  <polyline points="1 20 1 14 7 14" />
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
                </svg>
                Restart Computer Now
              </>
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                  <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
                  <line x1="12" y1="2" x2="12" y2="12" />
                </svg>
                Shutdown Computer Now
              </>
            )}
          </button>

          {selectedCommand === "message" && (
            <button
              type="button"
              className="execute-clear-btn"
              onClick={handleClear}
              disabled={executing || !messageText}
            >
              Clear
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
