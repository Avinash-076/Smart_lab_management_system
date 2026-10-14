import { getApiBaseUrl, buildApiUrl } from "./config";

/**
 * Backward-compatible API_BASE_URL export pointing to the centralized config.
 */
export const API_BASE_URL = getApiBaseUrl();

/**
 * Standardized API Error class for frontend requests.
 * Preserves standard Error interface while distinguishing auth and authorization errors.
 */
export class ApiError extends Error {
  constructor(message, status = 0, detail = null, data = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail || message;
    this.data = data;
    this.isAuthError = status === 401;
    this.isForbidden = status === 403;
  }
}

let authStateListeners = [];
let refreshPromise = null;
let logoutHandlers = [];

/**
 * Registers a callback to be invoked when logout occurs (e.g. closing WebSockets).
 *
 * @param {Function} handler
 * @returns {Function} Unsubscribe callback
 */
export function registerLogoutHandler(handler) {
  if (typeof handler === "function") {
    logoutHandlers.push(handler);
  }
  return () => {
    logoutHandlers = logoutHandlers.filter((h) => h !== handler);
  };
}

export function subscribeAuthChange(listener) {
  authStateListeners.push(listener);
  return () => {
    authStateListeners = authStateListeners.filter((l) => l !== listener);
  };
}

function notifyAuthChange(isAuthenticated) {
  authStateListeners.forEach((listener) => {
    try {
      listener(isAuthenticated);
    } catch (e) {
      console.error("Auth listener error:", e);
    }
  });
}

export function getAccessToken() {
  try {
    return localStorage.getItem("access_token");
  } catch {
    return null;
  }
}

export function getRefreshToken() {
  try {
    return localStorage.getItem("refresh_token");
  } catch {
    return null;
  }
}

export function setTokens(accessToken, refreshToken) {
  try {
    if (accessToken) {
      localStorage.setItem("access_token", accessToken);
    }
    if (refreshToken) {
      localStorage.setItem("refresh_token", refreshToken);
    }
    // Clean up obsolete key if present from legacy implementations
    localStorage.removeItem("token");
  } catch (e) {
    console.error("Failed to store tokens in localStorage:", e);
  }
}

export function clearTokens() {
  try {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("token");
  } catch (e) {
    console.error("Failed to clear tokens from localStorage:", e);
  }
  notifyAuthChange(false);
}

export function parseJwt(token) {
  try {
    if (!token || typeof token !== "string") return null;
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload);
  } catch {
    return null;
  }
}

export function isTokenExpired(token, bufferSeconds = 5) {
  const decoded = parseJwt(token);
  if (!decoded || !decoded.exp) return true;
  // exp is Unix timestamp in seconds; Date.now() in ms
  return decoded.exp * 1000 <= Date.now() + bufferSeconds * 1000;
}

export function isAuthenticated() {
  const token = getAccessToken();
  const rToken = getRefreshToken();
  if (token && !isTokenExpired(token)) return true;
  if (rToken && !isTokenExpired(rToken)) return true;
  return false;
}

export async function login(username, password) {
  if (!username || typeof username !== "string" || !username.trim()) {
    throw new ApiError("Please enter your username.", 400);
  }
  if (!password || typeof password !== "string") {
    throw new ApiError("Please enter your password.", 400);
  }

  const url = buildApiUrl("/auth/login");
  let response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        username: username.trim(),
        password,
      }),
    });
  } catch (netErr) {
    throw new ApiError(`Network error: ${netErr.message || "Failed to reach server"}`, 0, null, netErr);
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    const message = data?.detail || `Login failed (HTTP ${response.status})`;
    throw new ApiError(message, response.status, data?.detail, data);
  }

  if (!data?.access_token || !data?.refresh_token) {
    throw new ApiError("Invalid response from server: Missing tokens.", 500);
  }

  setTokens(data.access_token, data.refresh_token);
  notifyAuthChange(true);
  return data;
}

export async function refreshToken() {
  if (refreshPromise) {
    return refreshPromise;
  }

  const currentRefreshToken = getRefreshToken();
  if (!currentRefreshToken || isTokenExpired(currentRefreshToken)) {
    clearTokens();
    throw new ApiError("Session expired. Please log in again.", 401);
  }

  refreshPromise = (async () => {
    try {
      const url = buildApiUrl("/auth/refresh");
      let response;
      try {
        response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            refresh_token: currentRefreshToken,
          }),
        });
      } catch (netErr) {
        throw new ApiError(`Network error during token refresh: ${netErr.message || "Failed to reach server"}`, 0, null, netErr);
      }

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        // Clear tokens on auth rejection (e.g. 401 Unauthorized / 400 Bad Request)
        if (response.status === 401 || response.status === 400 || response.status === 403) {
          clearTokens();
        }
        const message = data?.detail || `Session expired (HTTP ${response.status})`;
        throw new ApiError(message, response.status, data?.detail, data);
      }

      if (!data?.access_token) {
        clearTokens();
        throw new ApiError("Malformed response during token refresh", 500);
      }

      setTokens(data.access_token, data.refresh_token || null);
      return data.access_token;
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 400 || error.status === 403)) {
        clearTokens();
      }
      throw error;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export function logout() {
  refreshPromise = null;

  // Run registered cleanup handlers (such as closing all active WebSockets)
  logoutHandlers.forEach((handler) => {
    try {
      handler();
    } catch (e) {
      console.error("Logout handler error:", e);
    }
  });

  clearTokens();
}

export async function fetchWithAuth(endpoint, options = {}) {
  let token = getAccessToken();

  // 1. Proactive check: if access token is expired or missing, refresh before request
  if (!token || isTokenExpired(token)) {
    const rToken = getRefreshToken();
    if (rToken && !isTokenExpired(rToken)) {
      try {
        token = await refreshToken();
      } catch {
        clearTokens();
        throw new ApiError("Session expired. Please log in again.", 401);
      }
    } else {
      clearTokens();
      throw new ApiError("Authentication required.", 401);
    }
  }

  const headers = {
    ...options.headers,
    Authorization: `Bearer ${token}`,
  };

  const url = buildApiUrl(endpoint);

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (netErr) {
    throw new ApiError(`Network error: ${netErr.message || "Failed to reach server"}`, 0, null, netErr);
  }

  // 2. Reactive check: handle 401 Unauthorized with single retry after refreshing token
  if (response.status === 401 && !options._isRetry) {
    const method = (options.method || "GET").toUpperCase();
    const isIdempotent = ["GET", "HEAD", "PUT", "DELETE", "OPTIONS"].includes(method);

    // Prevent automatically retrying non-idempotent mutations if risky unless marked retrySafe
    if (!isIdempotent && !options.retrySafe) {
      clearTokens();
      const errData = await response.json().catch(() => null);
      throw new ApiError(errData?.detail || "Session expired. Please log in again.", 401, errData?.detail, errData);
    }

    try {
      const newToken = await refreshToken();
      const retryHeaders = {
        ...options.headers,
        Authorization: `Bearer ${newToken}`,
      };
      response = await fetch(url, {
        ...options,
        headers: retryHeaders,
        _isRetry: true,
      });
    } catch {
      clearTokens();
      throw new ApiError("Session expired. Please log in again.", 401);
    }
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401) {
      clearTokens();
    }
    const message = data?.detail || `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, data?.detail, data);
  }

  if (options.includeHeaders) {
    return { data, headers: response.headers };
  }

  return data;
}

