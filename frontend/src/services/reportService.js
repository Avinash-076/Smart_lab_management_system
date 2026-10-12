/**
 * Reports & Analytics Service
 *
 * Handles generating metrics reports across utilization, software, issues,
 * maintenance, commands, and security audit logs, as well as CSV export.
 */

import {
  fetchWithAuth,
  getAccessToken,
  isTokenExpired,
  getRefreshToken,
  refreshToken,
  clearTokens,
  ApiError,
} from "./api";
import { buildApiUrl } from "./config";

export async function getReportOverview() {
  return fetchWithAuth("/reports/overview");
}

export async function getUtilizationReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.period) params.set("period", options.period);
    if (options.from_date) params.set("from_date", options.from_date);
    if (options.to_date) params.set("to_date", options.to_date);
    if (options.computer_id) params.set("computer_id", options.computer_id);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/utilization${query}`);
}

export async function getSoftwareReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.search) params.set("search", options.search.trim());
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/software${query}`);
}

export async function getIssueReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.severity) params.set("severity", options.severity);
    if (options.status) params.set("status", options.status);
    if (options.from_date) params.set("from_date", options.from_date);
    if (options.to_date) params.set("to_date", options.to_date);
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/issues${query}`);
}

export async function getMaintenanceReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.status) params.set("status", options.status);
    if (options.maintenance_type) params.set("maintenance_type", options.maintenance_type);
    if (options.from_date) params.set("from_date", options.from_date);
    if (options.to_date) params.set("to_date", options.to_date);
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/maintenance${query}`);
}

export async function getCommandReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.command_type) params.set("command_type", options.command_type);
    if (options.status) params.set("status", options.status);
    if (options.from_date) params.set("from_date", options.from_date);
    if (options.to_date) params.set("to_date", options.to_date);
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/commands${query}`);
}

export async function getAuditReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.action) params.set("action", options.action);
    if (options.user_id) params.set("user_id", options.user_id);
    if (options.result) params.set("result", options.result);
    if (options.from_date) params.set("from_date", options.from_date);
    if (options.to_date) params.set("to_date", options.to_date);
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/audit${query}`);
}

export async function downloadReportCSV(reportType, options = {}) {
  let token = getAccessToken();

  // Proactive check: refresh token if expired
  if (!token || isTokenExpired(token)) {
    const rToken = getRefreshToken();
    if (rToken && !isTokenExpired(rToken)) {
      try {
        token = await refreshToken();
      } catch {
        clearTokens();
        throw new ApiError("Session expired. Please log in again.", 401);
      }
    } else {
      clearTokens();
      throw new ApiError("Authentication required.", 401);
    }
  }

  const params = new URLSearchParams();
  params.set("report_type", reportType || "computer");
  if (options.period) params.set("period", options.period);
  if (options.from_date) params.set("from_date", options.from_date);
  if (options.to_date) params.set("to_date", options.to_date);
  if (options.computer_id) params.set("computer_id", options.computer_id);
  if (options.search) params.set("search", options.search.trim());
  if (options.status) params.set("status", options.status);
  if (options.severity) params.set("severity", options.severity);
  if (options.maintenance_type) params.set("maintenance_type", options.maintenance_type);
  if (options.command_type) params.set("command_type", options.command_type);
  if (options.action) params.set("action", options.action);
  if (options.result) params.set("result", options.result);

  const queryStr = params.toString();
  const endpoint = `/reports/export${queryStr ? `?${queryStr}` : ""}`;
  const url = buildApiUrl(endpoint);

  let response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch (netErr) {
    throw new ApiError(`Network error: ${netErr.message || "Failed to download report"}`, 0, null, netErr);
  }

  // Reactive retry on 401
  if (response.status === 401) {
    try {
      const newToken = await refreshToken();
      response = await fetch(url, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${newToken}`,
        },
      });
    } catch {
      clearTokens();
      throw new ApiError("Session expired. Please log in again.", 401);
    }
  }

  if (!response.ok) {
    let errorDetail = `Failed to export report CSV (HTTP ${response.status})`;
    try {
      const err = await response.json();
      errorDetail = err.detail || errorDetail;
    } catch {
      // ignore non-json errors
    }
    if (response.status === 401) {
      clearTokens();
    }
    throw new ApiError(errorDetail, response.status);
  }

  const blob = await response.blob();
  let filename = `SLMS-${reportType || "export"}-Report.csv`;
  const disposition = response.headers.get("Content-Disposition");
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) filename = match[1].trim();
  }

  if (typeof window !== "undefined" && window.URL && window.URL.createObjectURL) {
    const downloadUrl = window.URL.createObjectURL(blob);
    try {
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } finally {
      window.URL.revokeObjectURL(downloadUrl);
    }
  }

  return filename;
}
