/**
 * Computer feature utility functions
 */

/**
 * Checks if a computer operating system is Windows.
 */
export function isWindowsOS(computer) {
  if (!computer) return false;
  const osName = (computer.os_name || computer.os || "").toLowerCase();
  const osVersion = (computer.os_version || "").toLowerCase();
  return osName.includes("windows") || osVersion.includes("windows");
}

/**
 * Calculates computer metrics and percentages safely without division by zero.
 */
export function calculateComputerStats(computers = []) {
  const total = computers.length;
  const online = computers.filter(
    (c) => (c.status || "").toLowerCase() === "online"
  ).length;
  const offline = total - online;

  const windows = computers.filter(isWindowsOS).length;
  const otherOS = total - windows;

  const formatPct = (count) => {
    if (total === 0) return "0.00% of total";
    return `${((count / total) * 100).toFixed(2)}% of total`;
  };

  return {
    total,
    online,
    onlinePct: formatPct(online),
    offline,
    offlinePct: formatPct(offline),
    windows,
    windowsPct: formatPct(windows),
    otherOS,
    otherOSPct: formatPct(otherOS),
  };
}

/**
 * Resolves OS icon type and modifier CSS class based on OS name/version.
 */
export function getOsIconInfo(computer) {
  const os = (
    computer?.os_name
      ? `${computer.os_name} ${computer.os_version || ""}`
      : computer?.os || ""
  ).toLowerCase();

  if (os.includes("windows")) {
    return { type: "windows", className: "computer-table__os-icon--windows" };
  }
  if (
    os.includes("ubuntu") ||
    os.includes("debian") ||
    os.includes("linux") ||
    os.includes("fedora") ||
    os.includes("centos") ||
    os.includes("redhat")
  ) {
    return { type: "linux", className: "computer-table__os-icon--linux" };
  }
  if (
    os.includes("mac") ||
    os.includes("darwin") ||
    os.includes("apple") ||
    os.includes("sonoma")
  ) {
    return { type: "apple", className: "computer-table__os-icon--macos" };
  }
  return { type: "computer", className: "computer-table__os-icon--other" };
}

/**
 * Formats last seen timestamp into separate date and time strings.
 */
export function formatLastSeen(dateStr) {
  if (!dateStr) return { date: "Never", time: "" };
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return { date: String(dateStr), time: "" };

    const date = d.toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
    const time = d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });
    return { date, time };
  } catch {
    return { date: "Never", time: "" };
  }
}

/**
 * Calculates disk metrics safely.
 */
export function getDiskMetrics(pc) {
  const free =
    pc?.disk_free !== undefined
      ? Number(pc.disk_free)
      : pc?.free !== undefined
      ? Number(pc.free)
      : null;
  const total =
    pc?.disk_total !== undefined
      ? Number(pc.disk_total)
      : pc?.total !== undefined
      ? Number(pc.total)
      : null;

  if (
    total === null ||
    isNaN(total) ||
    total <= 0 ||
    free === null ||
    isNaN(free)
  ) {
    return null;
  }

  const used = Math.max(0, total - free);
  const usedPct = Math.min(100, Math.max(0, Math.round((used / total) * 100)));

  return {
    freeGB: free,
    totalGB: total,
    usedPct,
  };
}

/**
 * Generates an array of page numbers and ellipsis tokens.
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
