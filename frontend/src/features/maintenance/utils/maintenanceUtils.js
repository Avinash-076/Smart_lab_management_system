/**
 * Maintenance Feature Utility Functions
 *
 * Formats dates, badge visual tokens, pagination items, and handles CSV export.
 */

export function formatDateTime(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return String(dateStr);

    const months = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];
    const month = months[d.getMonth()];
    const day = d.getDate();
    const year = d.getFullYear();

    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;

    return `${month} ${day}, ${year}, ${hours}:${minutes} ${ampm}`;
  } catch {
    return String(dateStr || "—");
  }
}

export function formatDateOnly(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return String(dateStr);
    const months = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
    ];
    return `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
  } catch {
    return String(dateStr || "—");
  }
}

export function getTypeBadgeConfig(typeVal) {
  const t = (typeVal || "").toLowerCase();
  switch (t) {
    case "emergency":
      return {
        label: "Emergency",
        bg: "#FEE2E2",
        color: "#DC2626",
        border: "1px solid #FECACA",
      };
    case "corrective":
      return {
        label: "Corrective",
        bg: "#FFEDD5",
        color: "#EA580C",
        border: "1px solid #FED7AA",
      };
    case "hardware":
      return {
        label: "Hardware",
        bg: "#CCFBF1",
        color: "#0D9488",
        border: "1px solid #99F6E4",
      };
    case "software":
      return {
        label: "Software",
        bg: "#EEF2FF",
        color: "#4F46E5",
        border: "1px solid #C7D2FE",
      };
    case "preventive":
    default:
      return {
        label: "Preventive",
        bg: "#EFF6FF",
        color: "#2563EB",
        border: "1px solid #BFDBFE",
      };
  }
}

export function getStatusBadgeConfig(statusVal) {
  const st = (statusVal || "").toLowerCase();
  switch (st) {
    case "completed":
      return {
        label: "Completed",
        bg: "#DCFCE7",
        color: "#16A34A",
        dotColor: "#16A34A",
        border: "1px solid #BBF7D0",
      };
    case "in_progress":
      return {
        label: "In Progress",
        bg: "#FAF5FF",
        color: "#9333EA",
        dotColor: "#9333EA",
        border: "1px solid #E9D5FF",
      };
    case "cancelled":
      return {
        label: "Cancelled",
        bg: "#F1F5F9",
        color: "#64748B",
        dotColor: "#94A3B8",
        border: "1px solid #E2E8F0",
      };
    case "scheduled":
    default:
      return {
        label: "Scheduled",
        bg: "#FEF3C7",
        color: "#D97706",
        dotColor: "#EA580C",
        border: "1px solid #FDE68A",
      };
  }
}

export function formatStatusText(statusVal) {
  const st = (statusVal || "").toLowerCase();
  if (st === "in_progress") return "In Progress";
  if (st === "completed") return "Completed";
  if (st === "cancelled") return "Cancelled";
  return "Scheduled";
}

export function formatTypeText(typeVal) {
  const t = (typeVal || "").toLowerCase();
  if (!t) return "Preventive";
  return t.charAt(0).toUpperCase() + t.slice(1);
}

export function getPaginationItems(current, total) {
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }

  const items = [];

  if (current <= 4) {
    for (let i = 1; i <= 5; i++) items.push(i);
    items.push("...");
    items.push(total);
  } else if (current >= total - 3) {
    items.push(1);
    items.push("...");
    for (let i = total - 4; i <= total; i++) items.push(i);
  } else {
    items.push(1);
    items.push("...");
    items.push(current - 1);
    items.push(current);
    items.push(current + 1);
    items.push("...");
    items.push(total);
  }

  return items;
}

export function exportMaintenanceToCsv(records = [], computerMap = new Map()) {
  if (!records || records.length === 0) return;

  const csvHeaders = [
    "Record ID",
    "Computer",
    "Title",
    "Maintenance Type",
    "Status",
    "Technician",
    "Scheduled Date",
    "Started At",
    "Completed At",
    "Work Performed",
    "Notes",
    "Created At",
  ];

  const csvRows = records.map((rec) => {
    const compName =
      rec.computer_hostname ||
      (computerMap && computerMap.get ? computerMap.get(rec.computer_id) : "") ||
      `PC-${rec.computer_id}`;

    return [
      rec.id,
      compName,
      rec.title || "",
      formatTypeText(rec.maintenance_type),
      formatStatusText(rec.status),
      rec.technician_name || "Unassigned",
      rec.scheduled_at || "",
      rec.started_at || "",
      rec.completed_at || "",
      (rec.work_performed || "").replace(/\r?\n/g, " "),
      (rec.notes || "").replace(/\r?\n/g, " "),
      rec.created_at || "",
    ];
  });

  const csvContent = [
    csvHeaders.join(","),
    ...csvRows.map((row) =>
      row.map((val) => `"${String(val).replace(/"/g, '""')}"`).join(",")
    ),
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `SLMS-Maintenance-Records-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
