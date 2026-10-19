import { useState } from "react";
import { formatDateTime } from "../../utils/issueUtils";
import "./IssueComments.css";

function IssueComments({ issue, onAddComment, loading = false }) {
  const [commentText, setCommentText] = useState("");

  // Extract comments: resolution notes or comments stored with the issue
  const comments = [];
  if (issue?.resolution_notes) {
    comments.push({
      id: "res-notes",
      author: issue.status === "resolved" ? "Resolution Summary" : "Investigation Note",
      time: formatDateTime(issue.resolved_at || issue.updated_at),
      body: issue.resolution_notes,
    });
  }

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    onAddComment(issue, commentText.trim());
    setCommentText("");
  };

  return (
    <div className="issue-comments-container">
      {comments.length === 0 ? (
        <div className="issue-comments-empty">
          No comments or remarks recorded yet. Add an administrative note below.
        </div>
      ) : (
        <div className="issue-comments-list">
          {comments.map((c) => (
            <div key={c.id} className="issue-comment-item">
              <div className="issue-comment-meta">
                <span className="issue-comment-author">{c.author}</span>
                <span className="issue-comment-time">{c.time}</span>
              </div>
              <p className="issue-comment-body">{c.body}</p>
            </div>
          ))}
        </div>
      )}

      <form className="issue-comment-form" onSubmit={handleSubmit}>
        <textarea
          className="issue-comment-textarea"
          placeholder="Write a comment or note regarding this incident..."
          value={commentText}
          onChange={(e) => setCommentText(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="issue-comment-submit-btn"
          disabled={!commentText.trim() || loading}
        >
          {loading ? "Posting..." : "Post Comment"}
        </button>
      </form>
    </div>
  );
}

export default IssueComments;
