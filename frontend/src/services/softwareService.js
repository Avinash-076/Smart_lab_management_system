/**
 * Software Inventory Service
 *
 * Handles installed application and package catalog queries.
 */

import { fetchWithAuth } from "./api";

export async function getComputerSoftware(id) {
  return fetchWithAuth(`/clients/${id}/software`);
}
