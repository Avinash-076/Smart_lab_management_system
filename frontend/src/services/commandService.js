/**
 * Remote Command Execution Service
 *
 * Handles issuing remote system commands (message, lock, restart, shutdown),
 * tracking delivery status, filtering, pagination, summary metrics, and CSV export.
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

export async function issueCommand(computerId, commandData) {
  return fetchWithAuth(`/commands/${computerId}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(commandData),
  });
}

export async function getComputerCommands(computerId, options = {}) {
  const {
    search,
    status,
    start_date,
    end_date,
    limit = 10,
    offset = 0,
    includeHeaders = true,
  } = options;

  const qs = buildQueryString({
    search,
    status,
    start_date,
    end_date,
    limit,
    offset,
  });

  const res = await fetchWithAuth(`/commands/${computerId}${qs}`, {
    includeHeaders: true,
  });

  const totalHeader = res.headers?.get("x-total-count");
  const totalCount =
    totalHeader !== null && totalHeader !== undefined
      ? parseInt(totalHeader, 10)
      : Array.isArray(res.data)
      ? res.data.length
      : 0;

  if (includeHeaders) {
    return {
      data: Array.isArray(res.data) ? res.data : [],
      totalCount: isNaN(totalCount) ? 0 : totalCount,
      headers: res.headers,
    };
  }

  return Array.isArray(res.data) ? res.data : [];
}

export async function getComputerCommandsSummary(computerId) {
  return fetchWithAuth(`/commands/${computerId}/summary`);
}

export async function cancelCommand(commandId, computerId) {
  const qs = computerId ? `?computer_id=${computerId}` : "";
  return fetchWithAuth(`/commands/${commandId}/cancel${qs}`, {
    method: "POST",
  });
}

export async function getCommandDetails(commandId, computerId) {
  const qs = computerId ? `?computer_id=${computerId}` : "";
  return fetchWithAuth(`/commands/detail/${commandId}${qs}`);
}

export async function exportCommandsToCsv(computerId, options = {}, computerName = "computer") {
  const res = await getComputerCommands(computerId, {
    ...options,
    limit: 1000,
    offset: 0,
    includeHeaders: true,
  });

  const items = res.data || [];
  const headers = [
    "#",
    "Command / Action",
    "Executed At",
    "Executed By",
    "Status",
    "Duration",
    "Payload",
    "Result Message",
  ];

  const escapeCsv = (str) => {
    if (str === null || str === undefined) return '""';
    const escaped = String(str).replace(/"/g, '""');
    return `"${escaped}"`;
  };

  const rows = items.map((cmd, idx) => {
    const executedAt = cmd.created_at
      ? new Date(cmd.created_at).toLocaleString()
      : "—";
    const duration =
      cmd.duration_seconds !== null && cmd.duration_seconds !== undefined
        ? `${cmd.duration_seconds}s`
        : "—";

    return [
      idx + 1,
      escapeCsv(cmd.command_type?.toUpperCase() || "—"),
      escapeCsv(executedAt),
      escapeCsv(cmd.issued_by_username || `User #${cmd.issued_by || "—"}`),
      escapeCsv(cmd.status || "—"),
      escapeCsv(duration),
      escapeCsv(cmd.payload || ""),
      escapeCsv(cmd.result?.message || ""),
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
  link.setAttribute("download", `commands_history_${sanitizedName}_${dateStr}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
