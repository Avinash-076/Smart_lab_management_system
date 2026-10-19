/**
 * Audit Log Service
 *
 * Handles querying administrative and security audit event records,
 * retrieving aggregated summary statistics, and exporting sanitized CSVs.
 */

import { fetchWithAuth, ApiError } from "./api";
import { buildApiUrl } from "./config";
import {
  getAccessToken,
  getRefreshToken,
  refreshToken,
  isTokenExpired,
  clearTokens,
} from "./authService";

export async function getAuditLogs(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.action) params.set("action", options.action);
    if (options.target_type) params.set("target_type", options.target_type);
    if (options.target_id !== undefined && options.target_id !== null && options.target_id !== "") {
      params.set("target_id", options.target_id);
    }
    if (options.user_id !== undefined && options.user_id !== null && options.user_id !== "") {
      params.set("user_id", options.user_id);
    }
    if (options.result) params.set("result", options.result);
    if (options.search) params.set("search", options.search.trim());
    if (options.date_from) params.set("date_from", options.date_from);
    if (options.date_to) params.set("date_to", options.date_to);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/audit-logs${query}`);
}

export async function getAuditLogDetails(logId) {
  return fetchWithAuth(`/audit-logs/${logId}`);
}

export async function getAuditStats() {
  return fetchWithAuth("/audit-logs/stats");
}

export async function downloadAuditLogsCSV(options = {}) {
  let token = getAccessToken();

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
  if (options.action) params.set("action", options.action);
  if (options.target_type) params.set("target_type", options.target_type);
  if (options.target_id !== undefined && options.target_id !== null && options.target_id !== "") {
    params.set("target_id", options.target_id);
  }
  if (options.user_id !== undefined && options.user_id !== null && options.user_id !== "") {
    params.set("user_id", options.user_id);
  }
  if (options.result) params.set("result", options.result);
  if (options.search) params.set("search", options.search.trim());
  if (options.date_from) params.set("date_from", options.date_from);
  if (options.date_to) params.set("date_to", options.date_to);
  if (options.limit) params.set("limit", options.limit);

  const queryStr = params.toString();
  const endpoint = `/audit-logs/export${queryStr ? `?${queryStr}` : ""}`;
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
    throw new ApiError(`Network error: ${netErr.message || "Failed to download audit logs"}`, 0, null, netErr);
  }

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
      throw new ApiError("Session expired during export.", 401);
    }
  }

  if (!response.ok) {
    let errDetail = "Failed to export audit logs CSV";
    try {
      const errJson = await response.json();
      errDetail = errJson.detail || errDetail;
    } catch {
      // Keep fallback
    }
    throw new ApiError(errDetail, response.status);
  }

  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition");
  let filename = `slms-audit-logs-${new Date().toISOString().slice(0, 10)}.csv`;
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) {
      filename = match[1];
    }
  }

  const blobUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = blobUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.URL.revokeObjectURL(blobUrl);

  return { success: true, filename };
}
