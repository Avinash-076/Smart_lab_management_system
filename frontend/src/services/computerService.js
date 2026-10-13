/**
 * Computer Management Service
 *
 * Handles client computer queries, hardware telemetry metrics,
 * and system usage monitoring.
 */

import { fetchWithAuth } from "./api";

export async function getComputers() {
  return fetchWithAuth("/clients");
}

export async function getComputer(id) {
  return fetchWithAuth(`/clients/${id}`);
}

export async function getComputerMetrics(id, options = {}) {
  let query = "";
  if (typeof options === "number") {
    query = `?limit=${options}`;
  } else if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    if (options.start_time) {
      params.set(
        "start_time",
        options.start_time instanceof Date
          ? options.start_time.toISOString()
          : options.start_time
      );
    }
    if (options.end_time) {
      params.set(
        "end_time",
        options.end_time instanceof Date
          ? options.end_time.toISOString()
          : options.end_time
      );
    }
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/metrics/${id}${query}`);
}

export async function getComputerUsage(id, options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    if (options.start_time) {
      params.set(
        "start_time",
        options.start_time instanceof Date
          ? options.start_time.toISOString()
          : options.start_time
      );
    }
    if (options.end_time) {
      params.set(
        "end_time",
        options.end_time instanceof Date
          ? options.end_time.toISOString()
          : options.end_time
      );
    }
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/clients/${id}/usage${query}`);
}

export async function deleteComputer(id) {
  return fetchWithAuth(`/clients/${id}`, {
    method: "DELETE",
  });
}

export async function updateComputer(id, data) {
  return fetchWithAuth(`/clients/${id}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function generateEnrollmentKey() {
  return fetchWithAuth("/enrollment-keys", {
    method: "POST",
  });
}
