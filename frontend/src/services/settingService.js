/**
 * Settings & Configuration Management Service
 *
 * Handles reading, updating, and resetting lab environment system settings.
 */

import { fetchWithAuth } from "./api";

export async function getSettings(category) {
  const path = category ? `/settings/${category}` : "/settings";
  return fetchWithAuth(path);
}

export async function updateSettings(settingsMap) {
  return fetchWithAuth("/settings", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(settingsMap),
  });
}

export async function resetSettings(keys) {
  return fetchWithAuth("/settings/reset", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(keys ? { keys } : {}),
  });
}

export async function getAgentConfig() {
  return fetchWithAuth("/settings/agent-config");
}

