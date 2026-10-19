import Icon from "../../../../components/ui/Icon";
import "./IssueSummaryCards.css";

function MiniTelemetryBars({ type }) {
  // Balanced bar heights for sparklines matching FleetOverview aesthetics
  const barHeights = {
    blue: [40, 65, 90, 55, 80],
    red: [30, 75, 50, 95, 60],
    orange: [30, 75, 50, 95, 60],
    indigo: [45, 60, 85, 50, 75],
    purple: [45, 60, 85, 50, 75],
    green: [35, 65, 50, 85, 100],
  }[type] || [40, 60, 80, 50, 70];

  return (
    <div className={`issue-summary-bars ${type}`} aria-hidden="true">
      {barHeights.map((h, i) => (
        <span
          key={i}
          className={`issue-summary-bar ${type}`}
          style={{ height: `${h}%` }}
        />
      ))}
    </div>
  );
}

function IssueSummaryCards({ stats = {} }) {
  const cards = [
    {
      id: "total",
      title: "Total Issues",
      count: stats.total || 0,
      footer: "All reported issues",
      type: "blue",
      icon: "issue",
    },
    {
      id: "open",
      title: "Open",
      count: stats.open || 0,
      footer: "Requiring attention",
      type: "red",
      icon: "issue",
    },
    {
      id: "in_progress",
      title: "In Progress",
      count: stats.in_progress || 0,
      footer: "Being handled",
      type: "indigo",
      icon: "maintenance",
    },
    {
      id: "resolved",
      title: "Resolved",
      count: stats.resolved || 0,
      footer: "Successfully resolved",
      type: "green",
      icon: "details",
    },
  ];

  return (
    <div className="issue-summary-grid">
      {cards.map((c) => (
        <div key={c.id} className="issue-summary-card">
          <div className="issue-summary-card-body">
            <div className={`issue-summary-icon-box ${c.type}`}>
              <Icon type={c.icon} size={22} />
            </div>

            <div className="issue-summary-card-info">
              <span className="issue-summary-card-title">{c.title}</span>
              <span className="issue-summary-count">{c.count}</span>
              <span className="issue-summary-footer">{c.footer}</span>
            </div>
          </div>

          <MiniTelemetryBars type={c.type} />
        </div>
      ))}
    </div>
  );
}

export default IssueSummaryCards;
