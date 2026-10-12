/**
 * Maintenance Management Service
 *
 * Handles scheduling, logging, updating, completing, and tracking
 * preventive and corrective maintenance records.
 */

import { fetchWithAuth } from "./api";

export async function getMaintenanceRecords(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.status && options.status !== "All Status") {
      const statusMap = {
        Scheduled: "scheduled",
        "In Progress": "in_progress",
        Completed: "completed",
        Cancelled: "cancelled",
      };
      params.set("status", statusMap[options.status] || options.status.toLowerCase());
    }
    if (options.type && options.type !== "All Types") {
      const typeMap = {
        Preventive: "preventive",
        Corrective: "corrective",
        Emergency: "emergency",
        Software: "software",
        Hardware: "hardware",
      };
      params.set("type", typeMap[options.type] || options.type.toLowerCase());
    }
    if (options.search) params.set("search", options.search.trim());
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/maintenance${query}`);
}

export async function getMaintenanceRecord(id) {
  return fetchWithAuth(`/maintenance/${id}`);
}

export async function getMaintenanceStats(computerId = null) {
  const query = computerId ? `?computer_id=${computerId}` : "";
  return fetchWithAuth(`/maintenance/stats${query}`);
}

export async function getComputerMaintenance(computerId, options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.status) params.set("status", options.status);
    if (options.type) params.set("type", options.type);
    if (options.search) params.set("search", options.search);
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/clients/${computerId}/maintenance${query}`);
}

export async function createMaintenanceRecord(data) {
  return fetchWithAuth("/maintenance", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
}

export async function updateMaintenanceRecord(id, data) {
  return fetchWithAuth(`/maintenance/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
}

export async function completeMaintenanceRecord(id, workPerformed = null, notes = null) {
  return fetchWithAuth(`/maintenance/${id}/complete`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      work_performed: workPerformed,
      notes: notes,
    }),
  });
}

export async function deleteMaintenanceRecord(id) {
  return fetchWithAuth(`/maintenance/${id}`, {
    method: "DELETE",
  });
}
