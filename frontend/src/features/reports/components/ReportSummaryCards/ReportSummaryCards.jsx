import Icon from "../../../../components/ui/Icon";
import { formatGigabytes } from "../../utils/reportUtils";
import "./ReportSummaryCards.css";

function ReportSummaryCards({ category, reportData, loading }) {
  if (loading && !reportData) {
    return (
      <div className="report-summary-cards-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="report-summary-card report-card-skeleton">
            <div className="report-skeleton-icon" />
            <div className="report-skeleton-lines">
              <div className="report-skeleton-title" />
              <div className="report-skeleton-val" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const getCards = () => {
    if (!reportData) return [];

    switch (category) {
      case "inventory": {
        const hw = reportData.hardware_summary || {};
        return [
          {
            title: "Total Computers",
            value: reportData.total_computers ?? 0,
            subtitle: "Registered in system",
            icon: "computer",
            tone: "blue",
          },
          {
            title: "Online Hosts",
            value: reportData.online_computers ?? 0,
            subtitle: `${reportData.offline_computers ?? 0} currently offline`,
            icon: "pulse",
            tone: "green",
          },
          {
            title: "Total Memory",
            value: formatGigabytes(hw.total_ram_gb),
            subtitle: `Across ${hw.total_processors || 0} hardware profiles`,
            icon: "ram",
            tone: "purple",
          },
          {
            title: "Total Storage",
            value: formatGigabytes(hw.total_storage_gb),
            subtitle: `Avg cores: ${hw.avg_cores || 0}`,
            icon: "storage",
            tone: "indigo",
          },
        ];
      }

      case "utilization": {
        const ms = reportData.metrics_summary || {};
        return [
          {
            title: "Average CPU",
            value: `${ms.avg_cpu_percent ?? 0}%`,
            subtitle: `Peak CPU: ${ms.max_cpu_percent ?? 0}%`,
            icon: "cpu",
            tone: ms.avg_cpu_percent > 80 ? "red" : "blue",
          },
          {
            title: "Average Memory",
            value: `${ms.avg_ram_percent ?? 0}%`,
            subtitle: `Peak RAM: ${ms.max_ram_percent ?? 0}%`,
            icon: "ram",
            tone: ms.avg_ram_percent > 80 ? "orange" : "purple",
          },
          {
            title: "Average Storage",
            value: `${ms.avg_disk_percent ?? 0}%`,
            subtitle: `Peak Disk: ${ms.max_disk_percent ?? 0}%`,
            icon: "storage",
            tone: "indigo",
          },
          {
            title: "Online Hosts",
            value: reportData.online_computers ?? 0,
            subtitle: `Out of ${reportData.total_computers ?? 0} total`,
            icon: "pulse",
            tone: "green",
          },
        ];
      }

      case "software": {
        const top = reportData.top_installed?.[0];
        return [
          {
            title: "Installed Records",
            value: reportData.total_records ?? 0,
            subtitle: "Detected packages",
            icon: "software",
            tone: "blue",
          },
          {
            title: "Unique Software",
            value: reportData.unique_software_count ?? 0,
            subtitle: "Distinct catalog items",
            icon: "box",
            tone: "purple",
          },
          {
            title: "Most Installed App",
            value: top ? top.name : "N/A",
            subtitle: top ? `${top.count} computer installs` : "No software found",
            icon: "details",
            tone: "indigo",
          },
          {
            title: "Catalog Health",
            value: "100%",
            subtitle: "Indexed and searchable",
            icon: "check",
            tone: "green",
          },
        ];
      }

      case "issues": {
        const byStat = reportData.by_status || {};
        const bySev = reportData.by_severity || {};
        return [
          {
            title: "Total Issues",
            value: reportData.total_issues ?? 0,
            subtitle: "Logged lab issues",
            icon: "issue",
            tone: "blue",
          },
          {
            title: "Open Issues",
            value: byStat.open ?? 0,
            subtitle: `${byStat.in_progress ?? 0} in progress`,
            icon: "info",
            tone: byStat.open > 0 ? "orange" : "green",
          },
          {
            title: "Resolved Issues",
            value: byStat.resolved ?? 0,
            subtitle: "Closed successfully",
            icon: "check",
            tone: "green",
          },
          {
            title: "Critical Priority",
            value: bySev.critical ?? 0,
            subtitle: `${bySev.high ?? 0} high priority`,
            icon: "issue",
            tone: bySev.critical > 0 ? "red" : "blue",
          },
        ];
      }

      case "maintenance": {
        const byStat = reportData.by_status || {};
        return [
          {
            title: "Total Maintenance",
            value: reportData.total_records ?? 0,
            subtitle: "Work orders recorded",
            icon: "maintenance",
            tone: "blue",
          },
          {
            title: "Upcoming Jobs",
            value: reportData.upcoming_count ?? 0,
            subtitle: "Scheduled in future",
            icon: "calendar",
            tone: "indigo",
          },
          {
            title: "Overdue Jobs",
            value: reportData.overdue_count ?? 0,
            subtitle: "Require immediate action",
            icon: "clock",
            tone: reportData.overdue_count > 0 ? "red" : "green",
          },
          {
            title: "Completed Jobs",
            value: byStat.completed ?? 0,
            subtitle: `${byStat.in_progress ?? 0} actively running`,
            icon: "check",
            tone: "green",
          },
        ];
      }

      case "usage": {
        const topApp = reportData.top_applications?.[0];
        return [
          {
            title: "Usage Sessions",
            value: reportData.total_sessions ?? 0,
            subtitle: "Recorded application runs",
            icon: "cpu",
            tone: "blue",
          },
          {
            title: "Total Usage Time",
            value: `${reportData.total_duration_hours ?? 0} hrs`,
            subtitle: "Aggregate compute hours",
            icon: "clock",
            tone: "indigo",
          },
          {
            title: "Unique Apps Used",
            value: reportData.unique_applications ?? 0,
            subtitle: "Distinct active software",
            icon: "box",
            tone: "purple",
          },
          {
            title: "Top Application",
            value: topApp ? topApp.application_name : "N/A",
            subtitle: topApp ? `${topApp.total_duration_hours} hrs runtime` : "No sessions",
            icon: "details",
            tone: "green",
          },
        ];
      }

      case "commands": {
        const byStat = reportData.by_status || {};
        return [
          {
            title: "Total Commands",
            value: reportData.total_commands ?? 0,
            subtitle: "Dispatched to agents",
            icon: "command",
            tone: "blue",
          },
          {
            title: "Executed",
            value: byStat.executed ?? 0,
            subtitle: "Delivered & verified",
            icon: "check",
            tone: "green",
          },
          {
            title: "Failed Commands",
            value: byStat.failed ?? 0,
            subtitle: `${byStat.pending ?? 0} still pending`,
            icon: "issue",
            tone: byStat.failed > 0 ? "red" : "blue",
          },
          {
            title: "Success Rate",
            value: `${reportData.success_rate ?? 0}%`,
            subtitle: "Overall execution reliability",
            icon: "pulse",
            tone: reportData.success_rate >= 90 ? "green" : "orange",
          },
        ];
      }

      case "audit": {
        const byRes = reportData.by_result || {};
        const topAction = Object.keys(reportData.by_action || {})[0];
        return [
          {
            title: "Audit Events",
            value: reportData.total_events ?? 0,
            subtitle: "Tracked administrative operations",
            icon: "audit",
            tone: "blue",
          },
          {
            title: "Successful Actions",
            value: byRes.success ?? 0,
            subtitle: "Passed authorization",
            icon: "check",
            tone: "green",
          },
          {
            title: "Failed Attempts",
            value: byRes.failure ?? 0,
            subtitle: "Security rejections or errors",
            icon: "issue",
            tone: byRes.failure > 0 ? "red" : "green",
          },
          {
            title: "Most Frequent Action",
            value: topAction || "N/A",
            subtitle: topAction ? `${reportData.by_action[topAction]} occurrences` : "No events",
            icon: "settings",
            tone: "indigo",
          },
        ];
      }

      default:
        return [];
    }
  };

  const cards = getCards();

  if (!cards.length) return null;

  return (
    <div className="report-summary-cards-grid">
      {cards.map((c, idx) => (
        <div key={idx} className={`report-summary-card report-tone-${c.tone}`}>
          <div className="report-card-top-row">
            <span className="report-card-title">{c.title}</span>
            <div className={`report-card-icon-wrap report-icon-${c.tone}`}>
              <Icon type={c.icon} size={18} />
            </div>
          </div>
          <div className="report-card-val-row">
            <span className="report-card-value">{c.value}</span>
          </div>
          <span className="report-card-subtitle">{c.subtitle}</span>
        </div>
      ))}
    </div>
  );
}

export default ReportSummaryCards;
