/**
 * Reports Utility Helpers
 * Formatting, labels, status badge colors, and category definitions.
 */

export const REPORT_CATEGORIES = [
  {
    id: "inventory",
    label: "Computer Inventory",
    shortLabel: "Inventory",
    icon: "computer",
    badgeKey: "total_computers",
    description: "Hardware specifications, system architecture, and operating systems.",
  },
  {
    id: "utilization",
    label: "System Health & Telemetry",
    shortLabel: "Telemetry",
    icon: "pulse",
    badgeKey: "online_computers",
    description: "CPU, memory, storage utilization trends, and real-time host telemetry.",
  },
  {
    id: "software",
    label: "Software Inventory",
    shortLabel: "Software",
    icon: "software",
    badgeKey: "unique_software_count",
    description: "Installed applications, software versions, publishers, and host distribution.",
  },
  {
    id: "issues",
    label: "Issue Tracking",
    shortLabel: "Issues",
    icon: "issue",
    badgeKey: "total_issues",
    description: "System alerts, issue status breakdown, severity metrics, and resolution history.",
  },
  {
    id: "maintenance",
    label: "Maintenance Operations",
    shortLabel: "Maintenance",
    icon: "maintenance",
    badgeKey: "total_maintenance",
    description: "Preventive and corrective maintenance tasks, schedules, and technician records.",
  },
  {
    id: "usage",
    label: "Application Usage & Processes",
    shortLabel: "App Usage",
    icon: "cpu",
    badgeKey: "total_sessions",
    description: "Application run durations, top consumed software, and live process snapshots.",
  },
  {
    id: "commands",
    label: "Remote Commands",
    shortLabel: "Commands",
    icon: "command",
    badgeKey: "total_commands",
    description: "Remote administrative execution metrics, delivery status, and success rates.",
  },
  {
    id: "audit",
    label: "Security Audit Log",
    shortLabel: "Audit Log",
    icon: "audit",
    badgeKey: "total_audit_events",
    description: "Security events, administrative actions, target objects, and outcomes.",
  },
];

export function formatDate(isoString) {
  if (!isoString) return "N/A";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return String(isoString);
    return d.toLocaleString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return String(isoString);
  }
}

export function formatDuration(seconds) {
  const sec = Number(seconds) || 0;
  if (sec <= 0) return "0s";
  const hours = Math.floor(sec / 3600);
  const minutes = Math.floor((sec % 3600) / 60);
  const remSeconds = sec % 60;

  const parts = [];
  if (hours > 0) parts.push(`${hours}h`);
  if (minutes > 0) parts.push(`${minutes}m`);
  if (!parts.length || (hours === 0 && remSeconds > 0)) {
    parts.push(`${remSeconds}s`);
  }
  return parts.join(" ");
}

export function formatGigabytes(gb) {
  if (gb === null || gb === undefined || isNaN(gb)) return "N/A";
  const num = Number(gb);
  if (num >= 1024) {
    return `${(num / 1024).toFixed(2)} TB`;
  }
  return `${num.toFixed(1)} GB`;
}

export function getStatusBadgeClass(status) {
  if (!status) return "badge-neutral";
  const s = String(status).toLowerCase();
  if (s === "online" || s === "resolved" || s === "completed" || s === "executed" || s === "success") {
    return "badge-success";
  }
  if (s === "pending" || s === "scheduled" || s === "in_progress") {
    return "badge-warning";
  }
  if (s === "offline" || s === "failed" || s === "cancelled" || s === "critical") {
    return "badge-danger";
  }
  if (s === "open" || s === "high") {
    return "badge-orange";
  }
  return "badge-neutral";
}

export function getSeverityBadgeClass(severity) {
  if (!severity) return "badge-neutral";
  const s = String(severity).toLowerCase();
  switch (s) {
    case "critical":
      return "badge-danger";
    case "high":
      return "badge-orange";
    case "medium":
      return "badge-warning";
    case "low":
      return "badge-info";
    default:
      return "badge-neutral";
  }
}
