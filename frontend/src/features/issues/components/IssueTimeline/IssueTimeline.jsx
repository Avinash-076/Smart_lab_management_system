import { formatDateTime } from "../../utils/issueUtils";
import "./IssueTimeline.css";

function IssueTimeline({ issue }) {
  if (!issue) return null;

  // Construct real milestones from issue lifecycle fields
  const milestones = [];

  // 1. Issue Reported
  milestones.push({
    id: "reported",
    title: "Issue reported",
    time: formatDateTime(issue.created_at),
    note:
      issue.source === "agent"
        ? `Reported automatically by Client Agent on ${issue.computer_hostname || "computer"}.`
        : issue.description
        ? issue.description.slice(0, 90) + (issue.description.length > 90 ? "..." : "")
        : "Initial problem logged.",
    dotColor: "orange",
  });

  // 2. Automated triage / assignment
  milestones.push({
    id: "assigned",
    title: "Issue assigned",
    time: formatDateTime(issue.created_at),
    note: "Automatically assigned for review.",
    dotColor: "blue",
  });

  // 3. Status progression
  if (issue.status === "in_progress" || issue.status === "resolved") {
    milestones.push({
      id: "investigation",
      title: "Investigation started",
      time: formatDateTime(issue.updated_at || issue.created_at),
      note: "Administrator started investigating the issue.",
      dotColor: "blue",
    });
  }

  // 4. Resolution
  if (issue.status === "resolved") {
    milestones.push({
      id: "resolved",
      title: "Issue resolved",
      time: formatDateTime(issue.resolved_at || issue.updated_at),
      note:
        issue.resolution_notes ||
        "Confirmed resolved and verified by administrator.",
      dotColor: "green",
    });
  }

  return (
    <div className="issue-timeline-container">
      <ul className="issue-timeline-list">
        {milestones.map((m) => (
          <li key={m.id} className="issue-timeline-item">
            <span className={`issue-timeline-dot ${m.dotColor}`} />
            <div className="issue-timeline-content">
              <span className="issue-timeline-title">{m.title}</span>
              <span className="issue-timeline-time">{m.time}</span>
              <p className="issue-timeline-note">{m.note}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default IssueTimeline;
