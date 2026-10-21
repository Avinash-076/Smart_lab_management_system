/**
 * Authentication Service
 *
 * Handles user authentication operations, session lifecycle,
 * token management, and profile inspection.
 */

import {
  fetchWithAuth,
  login as apiLogin,
  refreshToken as apiRefreshToken,
  logout as apiLogout,
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  parseJwt,
  isTokenExpired,
  isAuthenticated,
  subscribeAuthChange,
  registerLogoutHandler,
} from "./api";

export {
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  parseJwt,
  isTokenExpired,
  isAuthenticated,
  subscribeAuthChange,
  registerLogoutHandler,
};

export async function login(username, password) {
  return apiLogin(username, password);
}

export async function refreshToken() {
  return apiRefreshToken();
}

export function logout() {
  return apiLogout();
}

export async function getCurrentUserProfile() {
  return fetchWithAuth("/auth/me");
}

export async function changePassword(currentPassword, newPassword) {
  return fetchWithAuth("/auth/change-password", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      current_password: currentPassword,
      new_password: newPassword,
    }),
  });
}

