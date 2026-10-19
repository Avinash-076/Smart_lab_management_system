import StatCard from "../../../../components/ui/StatCard";
import "./AuditStats.css";

function AuditStats({ stats, loading = false }) {
  const safeStats = stats || {
    total: 0,
    success: 0,
    failure: 0,
    commands: 0,
    last_24h: 0,
  };

  const successRate =
    safeStats.total > 0
      ? Math.round((safeStats.success / safeStats.total) * 100)
      : 100;

  return (
    <div className="audit-stats-grid" data-testid="audit-stats">
      <StatCard
        icon="audit"
        title="Total Events"
        number={loading ? "..." : safeStats.total.toLocaleString()}
        footer={`Recorded operations (${safeStats.last_24h} in last 24h)`}
        type="blue"
      />
      <StatCard
        icon="software"
        title="Successful Operations"
        number={loading ? "..." : safeStats.success.toLocaleString()}
        footer={`${successRate}% overall success rate`}
        type="green"
      />
      <StatCard
        icon="issue"
        title="Security & Failures"
        number={loading ? "..." : safeStats.failure.toLocaleString()}
        footer="Unauthorized or failed attempts"
        type="red"
      />
      <StatCard
        icon="computer"
        title="Remote Commands"
        number={loading ? "..." : safeStats.commands.toLocaleString()}
        footer="Dispatched command records"
        type="purple"
      />
    </div>
  );
}

export default AuditStats;
