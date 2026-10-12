/**
 * User & Role Management Service
 *
 * Handles administrative user provisioning, user profiles, RBAC roles,
 * and permission assignments.
 */

import { fetchWithAuth } from "./api";
import { getCurrentUserProfile } from "./authService";

export { getCurrentUserProfile };

export async function getUsers(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.search) params.set("search", options.search);
    if (options.role_id) params.set("role_id", options.role_id);
    if (options.role) params.set("role", options.role);
    if (options.status) params.set("status", options.status);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/users${query}`);
}

export async function getUserDetails(userId) {
  return fetchWithAuth(`/users/${userId}`);
}

export async function createUser(userData) {
  return fetchWithAuth("/users", {
    method: "POST",
    body: JSON.stringify(userData),
  });
}

export async function updateUser(userId, userData) {
  return fetchWithAuth(`/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(userData),
  });
}

export async function deleteUser(userId) {
  return fetchWithAuth(`/users/${userId}`, {
    method: "DELETE",
  });
}

export async function getRoles() {
  return fetchWithAuth("/roles");
}

export async function getRoleDetails(roleId) {
  return fetchWithAuth(`/roles/${roleId}`);
}

export async function createRole(roleData) {
  return fetchWithAuth("/roles", {
    method: "POST",
    body: JSON.stringify(roleData),
  });
}

export async function updateRole(roleId, roleData) {
  return fetchWithAuth(`/roles/${roleId}`, {
    method: "PATCH",
    body: JSON.stringify(roleData),
  });
}

export async function deleteRole(roleId) {
  return fetchWithAuth(`/roles/${roleId}`, {
    method: "DELETE",
  });
}

export async function getPermissions() {
  return fetchWithAuth("/permissions");
}

export async function updateRolePermissions(roleId, permissions) {
  return fetchWithAuth(`/roles/${roleId}/permissions`, {
    method: "PUT",
    body: JSON.stringify({ permissions }),
  });
}
