import Icon from "../../../../components/ui/Icon";
import "./IssueStatusActions.css";

function IssueStatusActions({
  issue,
  onStatusChange,
  onOpenResolve,
  onAddCommentClick,
  onViewComputer,
  onEditIssue,
  loading = false,
}) {
  if (!issue) return null;

  const currentStatus = (issue.status || "open").toLowerCase();

  return (
    <div className="issue-status-actions-container">
      {/* PRIMARY STATUS ROW */}
      <div className="issue-actions-primary-row">
        {currentStatus === "open" && (
          <button
            type="button"
            className="issue-btn-primary"
            onClick={() => onStatusChange(issue, "in_progress")}
            disabled={loading}
          >
            <Icon type="play" size={14} />
            <span>Start Working</span>
          </button>
        )}

        {currentStatus === "in_progress" && (
          <button
            type="button"
            className="issue-btn-resolve"
            onClick={() => onOpenResolve(issue)}
            disabled={loading}
          >
            <span>✓</span>
            <span>Resolve Issue</span>
          </button>
        )}

        {currentStatus === "resolved" && (
          <button
            type="button"
            className="issue-btn-reopen"
            onClick={() => onStatusChange(issue, "open")}
            disabled={loading}
          >
            <Icon type="refresh" size={14} />
            <span>Reopen Issue</span>
          </button>
        )}

        <button
          type="button"
          className="issue-btn-outline"
          onClick={onAddCommentClick}
          disabled={loading}
        >
          <Icon type="message" size={15} />
          <span>Add Comment</span>
        </button>
      </div>

      {/* SECONDARY ROW */}
      <div className="issue-actions-secondary-row">
        <button
          type="button"
          className="issue-btn-outline"
          onClick={() => onViewComputer(issue)}
        >
          <Icon type="computer" size={15} />
          <span>View Computer</span>
        </button>

        <button
          type="button"
          className="issue-btn-outline"
          onClick={() => onEditIssue(issue)}
        >
          <Icon type="edit" size={15} />
          <span>Edit Issue</span>
        </button>
      </div>
    </div>
  );
}

export default IssueStatusActions;
