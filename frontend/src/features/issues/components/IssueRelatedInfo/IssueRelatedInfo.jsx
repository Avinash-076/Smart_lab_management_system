import { useState } from "react";
import { parseStructuredIssue } from "../../utils/issueUtils";
import "./IssueRelatedInfo.css";

function IssueRelatedInfo({ issue, computer }) {
  const [copied, setCopied] = useState(false);
  const structured = parseStructuredIssue(issue);

  const handleCopy = (text) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="issue-related-container">
      {/* 1. Unauthorized Device Details */}
      {structured?.isDevice && (
        <div className="issue-related-device-box">
          <h4 className="issue-related-section-title">Peripheral Security Details</h4>
          
          <div className="issue-related-chip-row">
            {structured.vidPid && (
              <span className="issue-chip vid-pid">
                VID/PID: {structured.vidPid}
              </span>
            )}
            {structured.deviceClass && (
              <span className="issue-chip class">
                Class: {structured.deviceClass}
              </span>
            )}
            {structured.riskLevel && (
              <span className="issue-chip risk">
                Risk: {structured.riskLevel}
              </span>
            )}
          </div>

          {structured.hardwareId && (
            <div className="issue-pnp-box">
              <div className="issue-pnp-header">
                <span>Hardware PnP ID</span>
                <button
                  type="button"
                  className={`issue-copy-btn ${copied ? "copied" : ""}`}
                  onClick={() => handleCopy(structured.hardwareId)}
                >
                  {copied ? "✓ Copied" : "Copy ID"}
                </button>
              </div>
              <code className="issue-pnp-code">{structured.hardwareId}</code>
            </div>
          )}

          <div className="issue-security-tip">
            💡 <strong>Security Guidance:</strong> If this peripheral is legitimate for lab use, administrators can whitelist its Hardware ID or VID/PID in the authorized devices database.
          </div>
        </div>
      )}

      {/* 2. Metric Alert Telemetry */}
      {structured?.isMetric && (
        <div className="issue-metric-box">
          <h4 className="issue-related-section-title">
            Resource Consumption ({structured.metricType})
          </h4>
          <div className="issue-metric-row">
            <span>Observed Usage: {structured.currentValue ?? "N/A"}%</span>
            <span style={{ color: "#EF4444" }}>
              Threshold: {structured.threshold ?? 90}%
            </span>
          </div>
          <div className="issue-metric-track">
            <div
              className="issue-metric-fill high"
              style={{
                width: `${Math.min(100, structured.currentValue || 0)}%`,
              }}
            />
          </div>
          <p style={{ margin: "4px 0 0", fontSize: "11px", color: "#64748B" }}>
            Triggered automatically after consecutive cycles above limit. Auto-recovers once resource usage drops below policy threshold.
          </p>
        </div>
      )}

      {/* 3. Computer Context */}
      <div className="issue-related-device-box">
        <h4 className="issue-related-section-title">Host Computer Profile</h4>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", fontSize: "12px" }}>
          <div>
            <span style={{ color: "#64748B" }}>Hostname:</span>{" "}
            <strong>{issue?.computer_hostname || computer?.hostname || `PC #${issue?.computer_id}`}</strong>
          </div>
          <div>
            <span style={{ color: "#64748B" }}>IP Address:</span>{" "}
            <strong>{computer?.ip_address || "N/A"}</strong>
          </div>
          <div>
            <span style={{ color: "#64748B" }}>Operating System:</span>{" "}
            <span>{computer?.os_name || "Windows 10 / 11"}</span>
          </div>
          <div>
            <span style={{ color: "#64748B" }}>Status:</span>{" "}
            <span style={{ color: computer?.status === "offline" ? "#DC2626" : "#16A34A", fontWeight: 600 }}>
              {computer?.status || "Online"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default IssueRelatedInfo;
