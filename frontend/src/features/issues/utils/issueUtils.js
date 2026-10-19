/**
 * Issue Management Utilities
 *
 * Provides formatting, structured payload extraction (telemetry/devices),
 * and status/priority badge metadata helpers.
 */

export function formatDateTime(dateStr) {
  if (!dateStr) return "N/A";
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
    return String(dateStr || "N/A");
  }
}

export function formatTimeOnly(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;
    return `${hours}:${minutes} ${ampm}`;
  } catch {
    return "";
  }
}

export function parseStructuredIssue(issue) {
  if (!issue) return null;
  const title = (issue.title || "").toLowerCase();
  const desc = issue.description || "";

  // 1. Unauthorized Peripheral / USB Device Detection
  if (
    title.includes("unauthorized") ||
    desc.includes("Hardware ID:") ||
    desc.includes("VID / PID:")
  ) {
    const lines = desc.split("\n").map((l) => l.trim());
    const data = {
      isDevice: true,
      deviceName: null,
      deviceClass: null,
      hardwareId: null,
      vidPid: null,
      firstObserved: null,
      riskLevel: null,
      manufacturer: null,
      serial: null,
    };

    for (const line of lines) {
      if (line.startsWith("Device:")) data.deviceName = line.replace("Device:", "").trim();
      else if (line.startsWith("Class:")) data.deviceClass = line.replace("Class:", "").trim();
      else if (line.startsWith("Hardware ID:")) data.hardwareId = line.replace("Hardware ID:", "").trim();
      else if (line.startsWith("VID / PID:")) data.vidPid = line.replace("VID / PID:", "").trim();
      else if (line.startsWith("First Observed:")) data.firstObserved = line.replace("First Observed:", "").trim();
      else if (line.startsWith("Risk Level:")) data.riskLevel = line.replace("Risk Level:", "").trim();
      else if (line.startsWith("Manufacturer:")) data.manufacturer = line.replace("Manufacturer:", "").trim();
      else if (line.startsWith("Serial:")) data.serial = line.replace("Serial:", "").trim();
    }

    // Fallback extraction from title if deviceName not explicitly labeled
    if (!data.deviceName && title.includes("unauthorized")) {
      data.deviceName = issue.title.replace(/^Unauthorized\s+/i, "");
    }

    return data;
  }

  // 2. Metric Alerts (CPU, RAM, Disk)
  if (
    title.includes("cpu") ||
    title.includes("memory") ||
    title.includes("ram") ||
    title.includes("disk")
  ) {
    const currentMatch = desc.match(/Current [^:]+:\s*([0-9.]+)%/i);
    const threshMatch = desc.match(/above the\s*([0-9.]+)%/i);
    const metricType = title.includes("cpu")
      ? "CPU"
      : title.includes("disk")
      ? "Disk"
      : "RAM";

    return {
      isMetric: true,
      currentValue: currentMatch ? parseFloat(currentMatch[1]) : null,
      threshold: threshMatch ? parseFloat(threshMatch[1]) : null,
      metricType,
    };
  }

  // 3. Network Disconnection
  if (title.includes("network") || title.includes("connection")) {
    return {
      isNetwork: true,
    };
  }

  return null;
}

export function getPriorityBadgeConfig(severity) {
  const s = (severity || "").toLowerCase();
  switch (s) {
    case "critical":
      return {
        label: "Critical",
        bg: "#FEE2E2",
        color: "#DC2626",
        border: "1px solid #FECACA",
      };
    case "high":
      return {
        label: "High",
        bg: "#FFEDD5",
        color: "#EA580C",
        border: "1px solid #FED7AA",
      };
    case "medium":
      return {
        label: "Medium",
        bg: "#FEF3C7",
        color: "#D97706",
        border: "1px solid #FDE68A",
      };
    case "low":
    default:
      return {
        label: "Low",
        bg: "#E0F2FE",
        color: "#0284C7",
        border: "1px solid #BAE6FD",
      };
  }
}

export function getStatusBadgeConfig(status) {
  const st = (status || "").toLowerCase();
  switch (st) {
    case "in_progress":
      return {
        label: "In Progress",
        bg: "#EFF6FF",
        color: "#2563EB",
        dotColor: "#2563EB",
        border: "1px solid #DBEAFE",
      };
    case "resolved":
      return {
        label: "Resolved",
        bg: "#DCFCE7",
        color: "#16A34A",
        dotColor: "#16A34A",
        border: "1px solid #BBF7D0",
      };
    case "open":
    default:
      return {
        label: "Open",
        bg: "#FEF3C7",
        color: "#D97706",
        dotColor: "#EA580C",
        border: "1px solid #FDE68A",
      };
  }
}

export function filterByDateRange(dateStr, rangeKey) {
  if (!rangeKey || rangeKey === "All Time") return true;
  if (!dateStr) return false;

  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return true;

  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = diffMs / (1000 * 60 * 60 * 24);

  if (rangeKey === "Today") {
    return (
      d.getDate() === now.getDate() &&
      d.getMonth() === now.getMonth() &&
      d.getFullYear() === now.getFullYear()
    );
  }
  if (rangeKey === "Last 7 Days") {
    return diffDays <= 7;
  }
  if (rangeKey === "Last 30 Days") {
    return diffDays <= 30;
  }
  if (rangeKey === "Last 90 Days") {
    return diffDays <= 90;
  }

  return true;
}

/**
 * Generates an array of page numbers and ellipsis tokens for pagination.
 */
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

/**
 * Exports issue list to CSV file download
 */
export function exportIssuesToCsv(issues = [], computerMap = new Map()) {
  if (!issues || issues.length === 0) return;

  const csvHeaders = [
    "Issue ID",
    "Computer",
    "Title",
    "Priority",
    "Status",
    "Reported At",
    "Description",
    "Resolved At",
    "Resolution Notes",
  ];

  const csvRows = issues.map((x) => {
    const compName =
      x.computer_hostname ||
      (computerMap && computerMap.get ? computerMap.get(x.computer_id) : "") ||
      `PC-${x.computer_id}`;
    return [
      x.id,
      compName,
      x.title || "",
      x.severity || "normal",
      x.status || "open",
      x.created_at || "",
      (x.description || "").replace(/\r?\n/g, " "),
      x.resolved_at || "",
      (x.resolution_notes || "").replace(/\r?\n/g, " "),
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
  link.download = `SLMS-Issues-${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}
