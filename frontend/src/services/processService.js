/**
 * Process Monitoring Service
 *
 * Handles real-time active system processes, server-side filtering,
 * pagination, process summary metrics, status distributions, and CSV export.
 */

import { fetchWithAuth } from "./api";

function buildQueryString(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, val]) => {
    if (val !== undefined && val !== null && val !== "" && val !== "all") {
      query.append(key, val);
    }
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

/**
 * Fetch paginated and filtered running processes for a computer.
 *
 * @param {string|number} id - Computer ID
 * @param {Object} options - Query filters and pagination
 * @returns {Promise<{data: Array, totalCount: number, headers: Headers}|Array>}
 */
export async function getComputerProcesses(id, options = {}) {
  const {
    search,
    status,
    cpu_min,
    memory_min_mb,
    user,
    sort_by = "cpu_percent",
    sort_order = "desc",
    limit = 10,
    offset = 0,
    includeHeaders = true,
  } = options;

  const qs = buildQueryString({
    search,
    status,
    cpu_min,
    memory_min_mb,
    user,
    sort_by,
    sort_order,
    limit,
    offset,
  });

  const res = await fetchWithAuth(`/clients/${id}/processes${qs}`, {
    includeHeaders: true,
  });

  const totalHeader = res.headers?.get("x-total-count");
  const totalCount =
    totalHeader !== null
      ? parseInt(totalHeader, 10)
      : Array.isArray(res.data)
      ? res.data.length
      : 0;

  if (includeHeaders) {
    return {
      data: res.data || [],
      totalCount: isNaN(totalCount) ? res.data?.length || 0 : totalCount,
      headers: res.headers,
    };
  }

  return res.data || [];
}

/**
 * Fetch process summary metrics, status distribution, and top CPU consumers.
 *
 * @param {string|number} id - Computer ID
 * @param {Object} filters - Optional query filters
 * @returns {Promise<Object>}
 */
export async function getComputerProcessesSummary(id, filters = {}) {
  const qs = buildQueryString(filters);
  return fetchWithAuth(`/clients/${id}/processes/summary${qs}`);
}

/**
 * Backward-compatible rankings for Matrix tab.
 *
 * @param {string|number} id - Computer ID
 * @param {number} limit - Number of top ranked items
 * @returns {Promise<Object>}
 */
export async function getComputerProcessRankings(id, limit = 5) {
  return fetchWithAuth(`/clients/${id}/processes/rankings?limit=${limit}`);
}

/**
 * Export running process list to a CSV file.
 *
 * @param {Array} processItems - List of process items
 * @param {string} [computerName] - Computer name for the filename
 */
export function exportProcessesToCsv(processItems = [], computerName = "computer") {
  if (!processItems || !processItems.length) return;

  const headers = [
    "#",
    "Process Name",
    "PID",
    "Status",
    "CPU Usage (%)",
    "Memory Usage (MB)",
    "User",
    "Executable Path",
  ];

  const escapeCsv = (str) => {
    if (str === null || str === undefined) return '""';
    const escaped = String(str).replace(/"/g, '""');
    return `"${escaped}"`;
  };

  const rows = processItems.map((item, idx) => {
    const memStr =
      item.memory_mb !== null && item.memory_mb !== undefined
        ? `${Number(item.memory_mb).toFixed(1)} MB`
        : item.memory_percent !== undefined
        ? `${Number(item.memory_percent).toFixed(1)}%`
        : "—";

    return [
      idx + 1,
      escapeCsv(item.name || "—"),
      escapeCsv(item.pid ?? "—"),
      escapeCsv(item.status || "Running"),
      escapeCsv(item.cpu_percent !== undefined ? `${Number(item.cpu_percent).toFixed(1)}%` : "0.0%"),
      escapeCsv(memStr),
      escapeCsv(item.user || "—"),
      escapeCsv(item.executable_path || "—"),
    ];
  });

  const csvContent = [
    headers.join(","),
    ...rows.map((row) => row.join(",")),
  ].join("\r\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  if (typeof window === "undefined" || typeof document === "undefined") {
    return blob;
  }
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const sanitizedName = String(computerName).replace(/[^a-zA-Z0-9-_]/g, "_");
  const dateStr = new Date().toISOString().split("T")[0];
  link.setAttribute("href", url);
  link.setAttribute("download", `running_processes_${sanitizedName}_${dateStr}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
