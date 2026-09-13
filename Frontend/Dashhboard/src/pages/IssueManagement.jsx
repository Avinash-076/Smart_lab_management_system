import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function IssueManagement() {
  return (
    <div className="content">

      <div className="page-top">
        <div>
          <h2>Issue Management</h2>

          <p>
            Track and manage problems reported by laboratory computers.
          </p>
        </div>
      </div>

      <div className="cards">

        <StatCard
          icon="issue"
          title="Total Issues"
          number="0"
          footer="All reported issues"
          type="blue"
        />

        <StatCard
          icon="issue"
          title="Open"
          number="0"
          footer="Issues requiring attention"
          type="orange"
        />

        <StatCard
          icon="issue"
          title="In Progress"
          number="0"
          footer="Issues being resolved"
          type="purple"
        />

        <StatCard
          icon="details"
          title="Resolved"
          number="0"
          footer="Resolved issues"
          type="green"
        />

      </div>

      <div className="table-card">

        <div className="page-section-header">
          <div>
            <h3>Reported Issues</h3>

            <p>
              Problems reported by lab users or client agents.
            </p>
          </div>
        </div>

        <div className="empty-state">

          <Icon
            type="issue"
            size={40}
          />

          <h3>
            No issues reported
          </h3>

          <p>
            Reported computer problems will appear here.
          </p>

        </div>

      </div>

    </div>
  );
}

export default IssueManagement;