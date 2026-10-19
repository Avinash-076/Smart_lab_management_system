import { useEffect, useState } from "react";
import Icon from "../../../../components/ui/Icon";
import {
  formatDate,
  getActionBadgeClass,
  getOutcomeBadgeClass,
} from "../../utils/auditUtils";
import "./AuditDetailModal.css";

function AuditDetailModal({ log, onClose }) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!log) return null;

  const actionClass = getActionBadgeClass(log.action);
  const outcomeClass = getOutcomeBadgeClass(log.result);

  const handleCopyJSON = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(log, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div
      className="audit-modal-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="audit-modal-title"
    >
      <div
        className="audit-modal-container"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="audit-modal-header">
          <div className="audit-modal-title-group">
            <div className="audit-modal-icon-badge">
              <Icon type="audit" size={20} />
            </div>
            <div>
              <h3 id="audit-modal-title" className="audit-modal-title">
                Audit Event #{log.id}
              </h3>
              <p className="audit-modal-subtitle">
                Traceability parameters, actor identification, and event metadata
              </p>
            </div>
          </div>
          <button
            type="button"
            className="audit-modal-close-btn"
            onClick={onClose}
            aria-label="Close details modal"
          >
            ×
          </button>
        </div>

        {/* Modal Body */}
        <div className="audit-modal-body">
          {/* Metadata Grid */}
          <div className="audit-modal-meta-grid">
            <div className="audit-modal-field">
              <span className="audit-modal-label">ACTION CODE</span>
              <div className="audit-modal-val">
                <span className={`audit-badge ${actionClass}`}>
                  {log.action}
                </span>
              </div>
            </div>

            <div className="audit-modal-field">
              <span className="audit-modal-label">OUTCOME</span>
              <div className="audit-modal-val">
                <span className={`audit-outcome-badge ${outcomeClass}`}>
                  {log.result}
                </span>
              </div>
            </div>

            <div className="audit-modal-field">
              <span className="audit-modal-label">ACTOR IDENTITY</span>
              <div className="audit-modal-val-text">
                {log.username ? (
                  <strong>{log.username}</strong>
                ) : log.user_id ? (
                  <span>User #{log.user_id}</span>
                ) : (
                  <span className="audit-actor-system">SYSTEM / AGENT</span>
                )}
              </div>
            </div>

            <div className="audit-modal-field">
              <span className="audit-modal-label">SOURCE IP ADDRESS</span>
              <div className="audit-modal-val-text audit-ip-mono">
                {log.ip_address || "None / Internal Host"}
              </div>
            </div>

            <div className="audit-modal-field">
              <span className="audit-modal-label">TARGET RESOURCE</span>
              <div className="audit-modal-val-text">
                {log.target_type ? (
                  <span>
                    <strong>{log.target_type}</strong>
                    {log.target_id !== null && log.target_id !== undefined
                      ? ` (ID #${log.target_id})`
                      : ""}
                  </span>
                ) : (
                  <span className="audit-text-muted">None</span>
                )}
              </div>
            </div>

            <div className="audit-modal-field">
              <span className="audit-modal-label">TIMESTAMP</span>
              <div className="audit-modal-val-text">
                {formatDate(log.created_at)}
              </div>
            </div>
          </div>

          {/* Raw JSON Record */}
          <div className="audit-modal-json-section">
            <div className="audit-modal-json-header">
              <span className="audit-modal-label">RAW AUDIT RECORD (JSON)</span>
              <button
                type="button"
                className="audit-modal-copy-btn"
                onClick={handleCopyJSON}
                title="Copy raw JSON to clipboard"
              >
                <Icon type={copied ? "check" : "copy"} size={13} />
                <span>{copied ? "Copied!" : "Copy JSON"}</span>
              </button>
            </div>
            <pre className="audit-modal-json-content">
              {JSON.stringify(log, null, 2)}
            </pre>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="audit-modal-footer">
          <button
            type="button"
            className="audit-action-btn audit-btn-secondary"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default AuditDetailModal;
