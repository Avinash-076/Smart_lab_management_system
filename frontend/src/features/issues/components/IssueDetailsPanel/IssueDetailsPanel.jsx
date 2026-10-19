import { useState, useEffect } from "react";
import Icon from "../../../../components/ui/Icon";
import {
  formatDateTime,
  getPriorityBadgeConfig,
  getStatusBadgeConfig,
} from "../../utils/issueUtils";
import IssueTimeline from "../IssueTimeline/IssueTimeline";
import IssueRelatedInfo from "../IssueRelatedInfo/IssueRelatedInfo";
import IssueComments from "../IssueComments/IssueComments";
import IssueStatusActions from "../IssueStatusActions/IssueStatusActions";
import "./IssueDetailsPanel.css";

function IssueDetailsPanel({
  issue,
  computer,
  onClose,
  onStatusChange,
  onOpenResolve,
  onAddComment,
  onViewComputer,
  onEditIssue,
  loading = false,
}) {
  const [activeTab, setActiveTab] = useState("timeline");

  // Close on Escape key press
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === "Escape") {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!issue) return null;

  const priorityConfig = getPriorityBadgeConfig(issue.severity);
  const statusConfig = getStatusBadgeConfig(issue.status);
  const commentsCount = issue.resolution_notes ? 1 : 0;

  return (
    <div
      className="issue-details-modal-overlay"
      onClick={onClose}
      data-testid="issue-details-modal"
    >
      <div
        className="issue-details-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Issue Details"
      >
        {/* 1. MODAL HEADER */}
        <div className="issue-details-modal-header">
          <div className="issue-details-header-left">
            <div className="issue-details-header-icon">
              <Icon type="details" size={18} />
            </div>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h2 className="issue-details-header-title">Issue Details</h2>
                <span className="issue-details-header-id">{`#${issue.id}`}</span>
              </div>
              <p className="issue-details-header-sub">
                Complete diagnostic information and incident resolution tracking
              </p>
            </div>
          </div>

          <button
            type="button"
            className="issue-details-close-btn"
            onClick={onClose}
            aria-label="Close details panel"
            title="Close (Esc)"
          >
            ✕
          </button>
        </div>

        {/* 2. MODAL BODY (SCROLLABLE) */}
        <div className="issue-details-modal-body">
          {/* TITLE & BADGES HERO BANNER */}
          <div className="issue-details-hero-banner">
            <div className="issue-details-hero-left">
              <div className="issue-details-title-icon">
                <Icon type="issue" size={20} />
              </div>
              <div className="issue-details-hero-text">
                <h3 className="issue-details-title">{issue.title}</h3>
                <span className="issue-details-reported-time">
                  Reported on {formatDateTime(issue.created_at)}
                </span>
              </div>
            </div>

            <div className="issue-details-hero-badges">
              <span
                className="issue-badge-priority"
                style={{
                  background: priorityConfig.bg,
                  color: priorityConfig.color,
                  border: priorityConfig.border,
                }}
              >
                {priorityConfig.label}
              </span>

              <span
                className="issue-badge-status"
                style={{
                  background: statusConfig.bg,
                  color: statusConfig.color,
                  border: statusConfig.border,
                }}
              >
                <span
                  className="issue-status-dot"
                  style={{ background: statusConfig.dotColor }}
                />
                <span>{statusConfig.label}</span>
              </span>
            </div>
          </div>

          {/* METADATA CARDS GRID */}
          <div className="issue-details-meta-grid">
            <div className="issue-meta-item">
              <span className="issue-meta-label">Computer</span>
              <span className="issue-meta-value">
                <Icon type="computer" size={15} />
                <button
                  type="button"
                  className="issue-meta-link"
                  onClick={() => {
                    onClose();
                    onViewComputer(issue);
                  }}
                  title="View computer in inventory"
                >
                  {issue.computer_hostname || computer?.hostname || `Computer #${issue.computer_id}`}
                </button>
              </span>
            </div>

            <div className="issue-meta-item">
              <span className="issue-meta-label">Reported</span>
              <span className="issue-meta-value">{formatDateTime(issue.created_at)}</span>
            </div>

            <div className="issue-meta-item">
              <span className="issue-meta-label">Reported By</span>
              <span className="issue-meta-value">
                {issue.source === "agent" ? "Client Agent" : "Administrator"}
              </span>
            </div>

            <div className="issue-meta-item">
              <span className="issue-meta-label">Issue ID</span>
              <span className="issue-meta-value issue-mono">
                {`#${issue.id}`}
              </span>
            </div>
          </div>

          {/* DESCRIPTION CONTAINER */}
          <div className="issue-details-desc-box">
            <h4 className="issue-desc-label">Description</h4>
            <div className="issue-desc-text-wrapper">
              <p className="issue-desc-text">{issue.description}</p>
            </div>
          </div>

          {/* TABS HEADER */}
          <div className="issue-details-tabs-header">
            <button
              type="button"
              className={`issue-details-tab-btn ${activeTab === "timeline" ? "active" : ""}`}
              onClick={() => setActiveTab("timeline")}
            >
              Timeline
            </button>

            <button
              type="button"
              className={`issue-details-tab-btn ${activeTab === "related" ? "active" : ""}`}
              onClick={() => setActiveTab("related")}
            >
              Related Information
            </button>

            <button
              type="button"
              className={`issue-details-tab-btn ${activeTab === "comments" ? "active" : ""}`}
              onClick={() => setActiveTab("comments")}
            >
              {`Comments (${commentsCount})`}
            </button>
          </div>

          {/* TAB CONTENT CONTAINER */}
          <div className="issue-details-tab-content">
            {activeTab === "timeline" && <IssueTimeline issue={issue} />}
            {activeTab === "related" && (
              <IssueRelatedInfo issue={issue} computer={computer} />
            )}
            {activeTab === "comments" && (
              <IssueComments
                issue={issue}
                onAddComment={onAddComment}
                loading={loading}
              />
            )}
          </div>
        </div>

        {/* 3. MODAL FOOTER ACTIONS */}
        <div className="issue-details-modal-footer">
          <IssueStatusActions
            issue={issue}
            onStatusChange={onStatusChange}
            onOpenResolve={onOpenResolve}
            onAddCommentClick={() => setActiveTab("comments")}
            onViewComputer={(iss) => {
              onClose();
              onViewComputer(iss);
            }}
            onEditIssue={onEditIssue}
            loading={loading}
          />
        </div>
      </div>
    </div>
  );
}

export default IssueDetailsPanel;
