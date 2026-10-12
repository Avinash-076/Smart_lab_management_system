/**
 * Audit Log Service
 *
 * Handles querying administrative and security audit event records.
 */

import { fetchWithAuth } from "./api";

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
    if (options.search) params.set("search", options.search);
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
