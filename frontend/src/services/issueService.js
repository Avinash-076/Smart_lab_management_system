/**
 * Issue Management Service
 *
 * Handles reporting, tracking, updating, resolving, and deleting hardware
 * and software issues on client machines.
 */

import { fetchWithAuth } from "./api";

export async function getIssues(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.status && options.status !== "All Status") {
      const statusMap = {
        Open: "open",
        "In Progress": "in_progress",
        Resolved: "resolved",
      };
      params.set("status", statusMap[options.status] || options.status);
    }
    if (options.severity && options.severity !== "All Priority") {
      const severityMap = {
        Low: "low",
        Medium: "medium",
        High: "high",
        Critical: "critical",
      };
      params.set("severity", severityMap[options.severity] || options.severity.toLowerCase());
    }
    if (options.search) params.set("search", options.search.trim());
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/issues${query}`);
}

export async function getIssue(id) {
  return fetchWithAuth(`/issues/${id}`);
}

export async function getIssueStats(computerId = null) {
  const query = computerId ? `?computer_id=${computerId}` : "";
  return fetchWithAuth(`/issues/stats${query}`);
}

export async function getComputerIssues(computerId, options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.status) params.set("status", options.status);
    if (options.severity) params.set("severity", options.severity);
    if (options.search) params.set("search", options.search);
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/clients/${computerId}/issues${query}`);
}

export async function createIssue(data) {
  return fetchWithAuth("/issues", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
}

export async function updateIssue(id, data) {
  return fetchWithAuth(`/issues/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
}

export async function resolveIssue(id, resolutionNotes = null) {
  return fetchWithAuth(`/issues/${id}/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      resolution_notes: resolutionNotes,
    }),
  });
}

export async function deleteIssue(id) {
  return fetchWithAuth(`/issues/${id}`, {
    method: "DELETE",
  });
}
