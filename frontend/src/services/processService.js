/**
 * Process Monitoring Service
 *
 * Handles real-time active system processes and task inspect queries.
 */

import { fetchWithAuth } from "./api";

export async function getComputerProcesses(id) {
  return fetchWithAuth(`/clients/${id}/processes`);
}
