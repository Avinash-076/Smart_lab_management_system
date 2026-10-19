/**
 * Audit Log Utility Functions & Constants
 */

export const TARGET_RESOURCE_OPTIONS = [
  { value: "", label: "All Target Resources" },
  { value: "COMPUTER", label: "Computer" },
  { value: "COMMAND", label: "Remote Command" },
  { value: "USER", label: "User Account" },
  { value: "ROLE", label: "Security Role" },
  { value: "ISSUE", label: "Issue" },
  { value: "MAINTENANCE", label: "Maintenance Task" },
  { value: "SETTING", label: "System Setting" },
  { value: "AGENT_CREDENTIAL", label: "Agent Credential" },
];

export const OUTCOME_OPTIONS = [
  { value: "", label: "All Outcomes" },
  { value: "success", label: "Success Only" },
  { value: "failure", label: "Failures & Security Rejections" },
];

export function formatDate(isoString) {
  if (!isoString) return "—";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return String(isoString);
    return d.toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  } catch {
    return String(isoString);
  }
}

export function formatTimeOnly(isoString) {
  if (!isoString) return "";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true,
    });
  } catch {
    return "";
  }
}

export function getActionBadgeClass(action) {
  const act = (action || "").toUpperCase();
  if (act.includes("COMMAND") || act.includes("EXECUTE") || act.includes("REBOOT") || act.includes("SHUTDOWN")) {
    return "audit-badge-command";
  }
  if (act.includes("AUTH") || act.includes("LOGIN") || act.includes("TOKEN") || act.includes("LOGOUT")) {
    return "audit-badge-auth";
  }
  if (act.includes("USER") || act.includes("ROLE") || act.includes("PERMISSION")) {
    return "audit-badge-user";
  }
  if (act.includes("COMPUTER") || act.includes("AGENT") || act.includes("HEARTBEAT")) {
    return "audit-badge-agent";
  }
  if (act.includes("SETTING") || act.includes("CONFIG")) {
    return "audit-badge-setting";
  }
  if (act.includes("ISSUE") || act.includes("MAINTENANCE") || act.includes("ALERT")) {
    return "audit-badge-maintenance";
  }
  return "audit-badge-default";
}

export function getOutcomeBadgeClass(result) {
  const res = (result || "").toLowerCase();
  if (res === "success") return "audit-outcome-success";
  return "audit-outcome-failure";
}
