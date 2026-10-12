/**
 * Notification & Alert Service
 *
 * Handles system alerts, unread counters, category filtering,
 * and marking alerts as read.
 */

import { fetchWithAuth } from "./api";

export async function getNotifications(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.category && options.category !== "All Categories") {
      params.set("category", options.category.toLowerCase());
    }
    if (options.severity && options.severity !== "All Severities") {
      params.set("severity", options.severity.toLowerCase());
    }
    if (options.unread_only !== undefined) params.set("unread_only", options.unread_only);
    if (options.is_read !== undefined) params.set("is_read", options.is_read);
    if (options.search) params.set("search", options.search.trim());
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/notifications${query}`);
}

export async function getNotificationStats(computerId = null) {
  const query = computerId ? `?computer_id=${computerId}` : "";
  return fetchWithAuth(`/notifications/stats${query}`);
}

export async function getComputerNotifications(computerId, options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.category) params.set("category", options.category);
    if (options.severity) params.set("severity", options.severity);
    if (options.unread_only !== undefined) params.set("unread_only", options.unread_only);
    if (options.is_read !== undefined) params.set("is_read", options.is_read);
    if (options.search) params.set("search", options.search);
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/clients/${computerId}/notifications${query}`);
}

export async function markNotificationRead(id) {
  return fetchWithAuth(`/notifications/${id}/read`, {
    method: "PATCH",
  });
}

export async function markAllNotificationsRead(computerId = null) {
  const query = computerId ? `?computer_id=${computerId}` : "";
  return fetchWithAuth(`/notifications/read-all${query}`, {
    method: "POST",
  });
}

export async function deleteNotification(id) {
  return fetchWithAuth(`/notifications/${id}`, {
    method: "DELETE",
  });
}

export async function clearReadNotifications(computerId = null) {
  const query = computerId ? `?computer_id=${computerId}` : "";
  return fetchWithAuth(`/notifications/clear-read${query}`, {
    method: "DELETE",
  });
}
