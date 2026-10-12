/**
 * Remote Command Execution Service
 *
 * Handles issuing remote system commands (lock, restart, shutdown, message),
 * tracking delivery status, and cancelling commands.
 */

import { fetchWithAuth } from "./api";

export async function issueCommand(computerId, commandData) {
  return fetchWithAuth(`/commands/${computerId}`, {
    method: "POST",
    body: JSON.stringify(commandData),
  });
}

export async function getComputerCommands(computerId, options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/commands/${computerId}${query}`);
}

export async function cancelCommand(commandId) {
  return fetchWithAuth(`/commands/${commandId}/cancel`, {
    method: "POST",
  });
}

export async function getCommandDetails(commandId) {
  return fetchWithAuth(`/commands/detail/${commandId}`);
}
