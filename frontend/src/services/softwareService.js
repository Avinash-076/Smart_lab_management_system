/**
 * Software Inventory Service
 *
 * Handles installed application and package catalog queries,
 * filtering, pagination, software summary statistics, and CSV export.
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
 * Fetch paginated and filtered software inventory for a computer.
 *
 * @param {string|number} id - Computer ID
 * @param {Object} options - Query filters and pagination
 * @returns {Promise<{data: Array, totalCount: number}>}
 */
export async function getComputerSoftware(id, options = {}) {
  const {
    search,
    publisher,
    architecture,
    date_range,
    sort_by = "name",
    sort_order = "asc",
    limit = 10,
    offset = 0,
    includeHeaders = true,
  } = options;

  const qs = buildQueryString({
    search,
    publisher,
    architecture,
    date_range,
    sort_by,
    sort_order,
    limit,
    offset,
  });

  const res = await fetchWithAuth(`/clients/${id}/software${qs}`, {
    includeHeaders: true,
  });

  const totalHeader = res.headers?.get("x-total-count");
  const totalCount = totalHeader !== null ? parseInt(totalHeader, 10) : (Array.isArray(res.data) ? res.data.length : 0);

  if (includeHeaders) {
    return {
      data: res.data || [],
      totalCount: isNaN(totalCount) ? (res.data?.length || 0) : totalCount,
      headers: res.headers,
    };
  }

  return res.data || [];
}

/**
 * Fetch software summary metrics and analytics for a computer.
 *
 * @param {string|number} id - Computer ID
 * @param {Object} filters - Optional search/publisher/architecture/date_range filters
 * @returns {Promise<Object>}
 */
export async function getComputerSoftwareSummary(id, filters = {}) {
  const qs = buildQueryString(filters);
  return fetchWithAuth(`/clients/${id}/software/summary${qs}`);
}

/**
 * Fetch fleet-wide software summary metrics and analytics.
 *
 * @returns {Promise<Object>}
 */
export async function getFleetSoftwareSummary() {
  return fetchWithAuth("/software/fleet/summary");
}

/**
 * Fetch paginated and filtered fleet software inventory.
 *
 * @param {Object} options - Query filters and pagination
 * @returns {Promise<{data: Array, totalCount: number}>}
 */
export async function getFleetSoftware(options = {}) {
  const {
    search,
    publisher,
    computer_id,
    os_name,
    sort_by = "name",
    sort_order = "asc",
    limit = 10,
    offset = 0,
    includeHeaders = true,
  } = options;

  const qs = buildQueryString({
    search,
    publisher,
    computer_id,
    os_name,
    sort_by,
    sort_order,
    limit,
    offset,
  });

  const res = await fetchWithAuth(`/software/fleet${qs}`, {
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
 * Helper to export software inventory to a CSV file.
 *
 * @param {Array} softwareItems - List of software items
 * @param {string} [computerName] - Computer name for the filename
 */
export function exportSoftwareToCsv(softwareItems = [], computerName = "computer") {
  if (!softwareItems || !softwareItems.length) return;

  const headers = [
    "#",
    "Application Name",
    "Publisher",
    "Version",
    "Installation Date",
    "Installation Path",
    "Architecture",
  ];

  const escapeCsv = (str) => {
    if (str === null || str === undefined) return '""';
    const escaped = String(str).replace(/"/g, '""');
    return `"${escaped}"`;
  };

  const rows = softwareItems.map((item, idx) => [
    idx + 1,
    escapeCsv(item.name || "—"),
    escapeCsv(item.publisher || "—"),
    escapeCsv(item.version || "—"),
    escapeCsv(item.install_date ? item.install_date.split("T")[0] : "—"),
    escapeCsv(item.install_location || "—"),
    escapeCsv(item.architecture || "—"),
  ]);

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
  link.setAttribute("download", `software_inventory_${sanitizedName}_${dateStr}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Helper to export fleet software inventory to CSV file.
 *
 * @param {Array} softwareItems - List of fleet software items
 * @param {string} [prefix] - Filename prefix
 */
export function exportFleetSoftwareToCsv(softwareItems = [], prefix = "lab_fleet") {
  if (!softwareItems || !softwareItems.length) return;

  const headers = [
    "#",
    "Software Name",
    "Version",
    "Publisher",
    "Installed On (Computers)",
    "Operating System",
    "First Detected",
    "Architecture",
  ];

  const escapeCsv = (str) => {
    if (str === null || str === undefined) return '""';
    const escaped = String(str).replace(/"/g, '""');
    return `"${escaped}"`;
  };

  const rows = softwareItems.map((item, idx) => [
    idx + 1,
    escapeCsv(item.name || "—"),
    escapeCsv(item.version || "—"),
    escapeCsv(item.publisher || "—"),
    escapeCsv(
      item.installed_count && item.total_computers
        ? `${item.installed_count} / ${item.total_computers}`
        : item.installed_count || "—"
    ),
    escapeCsv(item.os_display || "Windows 10/11"),
    escapeCsv(item.install_date ? item.install_date.split("T")[0] : "—"),
    escapeCsv(item.architecture || "64-bit"),
  ]);

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
  const dateStr = new Date().toISOString().split("T")[0];
  link.setAttribute("href", url);
  link.setAttribute("download", `software_inventory_${prefix}_${dateStr}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

