import { useState } from "react";
import { parseApiDate } from "../../utils/computerUtils";
import "./CommandDetailsPanel.css";

function formatTimestamp(ts) {
  if (!ts) return "—";
  try {
    const d = parseApiDate(ts) || new Date(ts);
    if (!d || isNaN(d.getTime())) return ts;
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  } catch {
    return ts;
  }
}

function getCommandDisplayName(type) {
  switch (type?.toLowerCase()) {
    case "message":
      return "Send Message";
    case "lock":
      return "Lock Workstation";
    case "restart":
      return "Restart Computer";
    case "shutdown":
      return "Shutdown Computer";
    default:
      return type || "Unknown Command";
  }
}

export default function CommandDetailsPanel({ command, onClose }) {
  const [activeTab, setActiveTab] = useState("result"); // 'result' | 'raw'
  const [copied, setCopied] = useState(false);

  if (!command) return null;

  const isSuccess = command.status === "executed" || command.result?.success;
  const isFailed = command.status === "failed" || (command.result && !command.result.success);
  const isPending = command.status === "pending";
  const isDelivered = command.status === "delivered";

  const bannerClass = isSuccess
    ? "success"
    : isFailed
    ? "failed"
    : isPending
    ? "pending"
    : isDelivered
    ? "delivered"
    : "cancelled";

  const bannerText = isSuccess
    ? "Command Executed Successfully"
    : isFailed
    ? "Command Execution Failed"
    : isPending
    ? "Command Pending Delivery"
    : isDelivered
    ? "Command Delivered to Client"
    : "Command Cancelled";

  const executedAt = formatTimestamp(
    command.result?.completed_at || command.created_at
  );

  const executedBy =
    command.issued_by_username || (command.issued_by ? `User #${command.issued_by}` : "Administrator");

  const durationText =
    command.duration_seconds !== null && command.duration_seconds !== undefined
      ? `${command.duration_seconds} seconds`
      : command.result?.completed_at && command.created_at
      ? `${Math.max(0, Math.round(((new Date(command.result.completed_at) - new Date(command.created_at)) / 1000) * 10) / 10)} seconds`
      : "—";

  const resultMessage =
    command.result?.message ||
    (command.command_type === "message" && command.payload
      ? `Payload: "${command.payload}"`
      : isSuccess
      ? "Command completed successfully."
      : isPending
      ? "Waiting for client agent to accept command."
      : "No detailed execution message reported.");

  const rawJson = JSON.stringify(command, null, 2);

  const handleCopy = (text) => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="cmd-details-panel">
      {/* Panel Header */}
      <div className="cmd-details-header">
        <h3 className="cmd-details-title">Command Details</h3>
        <button
          type="button"
          className="cmd-details-close-btn"
          onClick={onClose}
          title="Close details"
        >
          ✕
        </button>
      </div>

      {/* Status Banner */}
      <div className={`cmd-details-banner ${bannerClass}`}>
        <span className="banner-icon">
          {isSuccess ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : isFailed ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10" />
              <line x1="15" y1="9" x2="9" y2="15" />
              <line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          )}
        </span>
        <span className="banner-text">{bannerText}</span>
      </div>

      {/* Meta Properties */}
      <div className="cmd-details-meta">
        <div className="meta-row">
          <span className="meta-label">Command</span>
          <span className="meta-colon">:</span>
          <span className="meta-value font-medium">
            {getCommandDisplayName(command.command_type)}
          </span>
        </div>

        <div className="meta-row">
          <span className="meta-label">Executed At</span>
          <span className="meta-colon">:</span>
          <span className="meta-value">{executedAt}</span>
        </div>

        <div className="meta-row">
          <span className="meta-label">Executed By</span>
          <span className="meta-colon">:</span>
          <span className="meta-value">{executedBy}</span>
        </div>

        <div className="meta-row">
          <span className="meta-label">Duration</span>
          <span className="meta-colon">:</span>
          <span className="meta-value">{durationText}</span>
        </div>

        <div className="meta-row">
          <span className="meta-label">Status</span>
          <span className="meta-colon">:</span>
          <span className={`meta-value status-text ${bannerClass}`}>
            {isSuccess
              ? "Success"
              : isFailed
              ? "Failed"
              : isPending
              ? "Pending"
              : isDelivered
              ? "Delivered"
              : "Cancelled"}
          </span>
        </div>

        {command.payload && command.command_type === "message" && (
          <div className="meta-row">
            <span className="meta-label">Message</span>
            <span className="meta-colon">:</span>
            <span className="meta-value message-quote">&quot;{command.payload}&quot;</span>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="cmd-details-tabs">
        <button
          type="button"
          className={`cmd-details-tab ${activeTab === "result" ? "active" : ""}`}
          onClick={() => setActiveTab("result")}
        >
          Result
          {activeTab === "result" && <span className="tab-indicator" />}
        </button>
        <button
          type="button"
          className={`cmd-details-tab ${activeTab === "raw" ? "active" : ""}`}
          onClick={() => setActiveTab("raw")}
        >
          Raw Data
          {activeTab === "raw" && <span className="tab-indicator" />}
        </button>
      </div>

      {/* Tab Content Box */}
      <div className="cmd-details-content-box">
        {activeTab === "result" ? (
          <div className="result-text-area">
            <p className="result-message">{resultMessage}</p>
            <button
              type="button"
              className="copy-btn"
              onClick={() => handleCopy(resultMessage)}
              title="Copy result message"
            >
              {copied ? (
                <span className="copied-text">Copied!</span>
              ) : (
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              )}
            </button>
          </div>
        ) : (
          <div className="raw-text-area">
            <pre className="raw-json">{rawJson}</pre>
            <button
              type="button"
              className="copy-btn"
              onClick={() => handleCopy(rawJson)}
              title="Copy raw JSON"
            >
              {copied ? (
                <span className="copied-text">Copied!</span>
              ) : (
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
