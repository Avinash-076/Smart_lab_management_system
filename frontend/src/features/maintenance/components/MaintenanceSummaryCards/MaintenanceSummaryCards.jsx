import Icon from "../../../../components/ui/Icon";
import "./MaintenanceSummaryCards.css";

function MiniTelemetryBars({ type }) {
  const barHeights = {
    blue: [40, 65, 90, 55, 80],
    amber: [30, 75, 50, 95, 60],
    purple: [45, 60, 85, 50, 75],
    green: [35, 65, 50, 85, 100],
  }[type] || [40, 60, 80, 50, 70];

  return (
    <div className={`maint-summary-bars ${type}`} aria-hidden="true">
      {barHeights.map((h, i) => (
        <span
          key={i}
          className={`maint-summary-bar ${type}`}
          style={{ height: `${h}%` }}
        />
      ))}
    </div>
  );
}

function MaintenanceSummaryCards({ stats = {} }) {
  const cards = [
    {
      id: "total",
      title: "Total Records",
      count: stats.total || 0,
      footer: "All maintenance records",
      type: "blue",
      icon: "maintenance",
    },
    {
      id: "scheduled",
      title: "Scheduled",
      count: stats.scheduled || 0,
      footer: "Waiting for service",
      type: "amber",
      icon: "issue",
    },
    {
      id: "in_progress",
      title: "In Progress",
      count: stats.in_progress || 0,
      footer: "Currently being serviced",
      type: "purple",
      icon: "maintenance",
    },
    {
      id: "completed",
      title: "Completed",
      count: stats.completed || 0,
      footer: "Finished maintenance",
      type: "green",
      icon: "details",
    },
  ];

  return (
    <div className="maint-summary-grid" data-testid="maintenance-summary-cards">
      {cards.map((c) => (
        <div key={c.id} className="maint-summary-card">
          <div className="maint-summary-card-body">
            <div className={`maint-summary-icon-box ${c.type}`}>
              <Icon type={c.icon} size={22} />
            </div>

            <div className="maint-summary-card-info">
              <span className="maint-summary-card-title">{c.title}</span>
              <span className="maint-summary-count">{c.count}</span>
              <span className="maint-summary-footer">{c.footer}</span>
            </div>
          </div>

          <MiniTelemetryBars type={c.type} />
        </div>
      ))}
    </div>
  );
}

export default MaintenanceSummaryCards;
