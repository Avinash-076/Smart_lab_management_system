import { useState } from "react";
import Icon from "../../../../components/ui/Icon";
import { parseApiDate } from "../../../computers/utils/computerUtils";
import "./GlobalCommandDetailModal.css";

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

export default function GlobalCommandDetailModal({ command, onClose }) {
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
    ? "Command Queued (Pending)"
    : isDelivered
    ? "Command Delivered to Client"
    : "Command Cancelled";

  const handleCopy = () => {
    try {
      navigator.clipboard.writeText(JSON.stringify(command, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const rawJson = JSON.stringify(command, null, 2);

  return (
    <div
      className="gcd-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="gcd-modal-title"
    >
      <div className="gcd-modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="gcd-modal-header">
          <div className="gcd-modal-header-info">
            <h3 id="gcd-modal-title" className="gcd-modal-title">
              Command Details: #{command.id}
            </h3>
            <span className="gcd-modal-badge">{getCommandDisplayName(command.command_type)}</span>
          </div>
          <button
            type="button"
            className="gcd-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Status banner */}
        <div className={`gcd-status-banner ${bannerClass}`}>
          <div className="gcd-banner-content">
            <span className="gcd-banner-dot" />
            <span className="gcd-banner-text">{bannerText}</span>
          </div>
          <div className="gcd-banner-duration">
            {command.duration_seconds !== null && command.duration_seconds !== undefined
              ? `${command.duration_seconds.toFixed(2)}s`
              : "—"}
          </div>
        </div>

        {/* Metadata Grid */}
        <div className="gcd-meta-grid">
          <div className="gcd-meta-item">
            <span className="gcd-meta-label">Command ID</span>
            <span className="gcd-meta-val">#{command.id}</span>
          </div>
          <div className="gcd-meta-item">
            <span className="gcd-meta-label">Target Computer</span>
            <span className="gcd-meta-val">
              {command.computer_hostname || `PC-${command.computer_id || "—"}`}
            </span>
          </div>
          <div className="gcd-meta-item">
            <span className="gcd-meta-label">Target IP</span>
            <span className="gcd-meta-val">{command.computer_ip || "—"}</span>
          </div>
          <div className="gcd-meta-item">
            <span className="gcd-meta-label">Issued By</span>
            <span className="gcd-meta-val">
              {command.issued_by_username || (command.issued_by ? `User #${command.issued_by}` : "Admin")}
            </span>
          </div>
          <div className="gcd-meta-item">
            <span className="gcd-meta-label">Created At</span>
            <span className="gcd-meta-val">{formatTimestamp(command.created_at)}</span>
          </div>
          <div className="gcd-meta-item">
            <span className="gcd-meta-label">Executed At</span>
            <span className="gcd-meta-val">
              {formatTimestamp(command.result?.executed_at || command.executed_at)}
            </span>
          </div>
        </div>

        {/* Tabs */}
        <div className="gcd-tabs">
          <button
            type="button"
            className={`gcd-tab-btn ${activeTab === "result" ? "active" : ""}`}
            onClick={() => setActiveTab("result")}
          >
            Execution Result
          </button>
          <button
            type="button"
            className={`gcd-tab-btn ${activeTab === "raw" ? "active" : ""}`}
            onClick={() => setActiveTab("raw")}
          >
            Raw JSON
          </button>
        </div>

        {/* Tab Body */}
        <div className="gcd-tab-content">
          {activeTab === "result" ? (
            <div className="gcd-result-view">
              {command.payload && (
                <div className="gcd-field-group">
                  <span className="gcd-field-label">Command Payload / Message</span>
                  <div className="gcd-payload-box">{command.payload}</div>
                </div>
              )}

              {command.result ? (
                <>
                  <div className="gcd-field-group">
                    <span className="gcd-field-label">Output Message</span>
                    <div className="gcd-output-box">
                      {command.result.message || command.result.stdout || "No message logged."}
                    </div>
                  </div>

                  {command.result.error && (
                    <div className="gcd-field-group">
                      <span className="gcd-field-label text-error">Error Message</span>
                      <div className="gcd-error-box">{command.result.error}</div>
                    </div>
                  )}

                  <div className="gcd-exec-stats">
                    <span>
                      <strong>Return Code:</strong>{" "}
                      <code>{command.result.return_code ?? (command.result.success ? 0 : 1)}</code>
                    </span>
                    <span>
                      <strong>Execution Status:</strong>{" "}
                      {command.result.success ? "Success" : "Failed"}
                    </span>
                  </div>
                </>
              ) : (
                <div className="gcd-empty-result">
                  No execution result reported yet. Command is in <strong>{command.status}</strong> state.
                </div>
              )}
            </div>
          ) : (
            <div className="gcd-raw-view">
              <div className="gcd-raw-actions">
                <button
                  type="button"
                  className="gcd-copy-btn"
                  onClick={handleCopy}
                  title="Copy raw JSON"
                >
                  <Icon name={copied ? "check" : "copy"} size={14} />
                  <span>{copied ? "Copied!" : "Copy JSON"}</span>
                </button>
              </div>
              <pre className="gcd-raw-pre">{rawJson}</pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="gcd-modal-footer">
          <button type="button" className="gcd-btn-close" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
