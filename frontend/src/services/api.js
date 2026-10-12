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

  return data;
}

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

export async function getComputerSoftware(id) {
  return fetchWithAuth(`/clients/${id}/software`);
}

export async function getComputerProcesses(id) {
  return fetchWithAuth(`/clients/${id}/processes`);
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

export async function getIssues(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.status && options.status !== "All Status") {
      const statusMap = {
        Open: "open",
        "In Progress": "in_progress",
        Resolved: "resolved",
      };
      params.set("status", statusMap[options.status] || options.status);
    }
    if (options.severity && options.severity !== "All Priority") {
      const severityMap = {
        Low: "low",
        Medium: "medium",
        High: "high",
        Critical: "critical",
      };
      params.set("severity", severityMap[options.severity] || options.severity.toLowerCase());
    }
    if (options.search) params.set("search", options.search.trim());
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/issues${query}`);
}

export async function getIssue(id) {
  return fetchWithAuth(`/issues/${id}`);
}

export async function getIssueStats(computerId = null) {
  const query = computerId ? `?computer_id=${computerId}` : "";
  return fetchWithAuth(`/issues/stats${query}`);
}

export async function getComputerIssues(computerId, options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.status) params.set("status", options.status);
    if (options.severity) params.set("severity", options.severity);
    if (options.search) params.set("search", options.search);
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.offset !== undefined) params.set("offset", options.offset);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/clients/${computerId}/issues${query}`);
}

export async function createIssue(data) {
  return fetchWithAuth("/issues", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
}

export async function updateIssue(id, data) {
  return fetchWithAuth(`/issues/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });
}

export async function resolveIssue(id, resolutionNotes = null) {
  return fetchWithAuth(`/issues/${id}/resolve`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      resolution_notes: resolutionNotes,
    }),
  });
}
export async function deleteIssue(id) {
  return fetchWithAuth(`/issues/${id}`, {
    method: "DELETE",
  });
}

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

/* =====================================================
   REMOTE COMMANDS (V5.1)
===================================================== */

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

/* =====================================================
   AUDIT LOGS (V5.3)
===================================================== */

export async function getAuditLogs(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    if (options.action) params.set("action", options.action);
    if (options.target_type) params.set("target_type", options.target_type);
    if (options.target_id !== undefined && options.target_id !== null && options.target_id !== "") {
      params.set("target_id", options.target_id);
    }
    if (options.user_id !== undefined && options.user_id !== null && options.user_id !== "") {
      params.set("user_id", options.user_id);
    }
    if (options.result) params.set("result", options.result);
    if (options.search) params.set("search", options.search);
    if (options.date_from) params.set("date_from", options.date_from);
    if (options.date_to) params.set("date_to", options.date_to);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/audit-logs${query}`);
}

export async function getAuditLogDetails(logId) {
  return fetchWithAuth(`/audit-logs/${logId}`);
}

/* =====================================================
   USER & ROLE MANAGEMENT (V6.1)
===================================================== */

export async function getCurrentUserProfile() {
  return fetchWithAuth("/auth/me");
}

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

/* =====================================================
   REPORTS & ANALYTICS (V6.2)
===================================================== */

export async function getReportOverview() {
  return fetchWithAuth("/reports/overview");
}

export async function getUtilizationReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.period) params.set("period", options.period);
    if (options.from_date) params.set("from_date", options.from_date);
    if (options.to_date) params.set("to_date", options.to_date);
    if (options.computer_id) params.set("computer_id", options.computer_id);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/utilization${query}`);
}

export async function getSoftwareReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.search) params.set("search", options.search.trim());
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/software${query}`);
}

export async function getIssueReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.severity) params.set("severity", options.severity);
    if (options.status) params.set("status", options.status);
    if (options.from_date) params.set("from_date", options.from_date);
    if (options.to_date) params.set("to_date", options.to_date);
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/issues${query}`);
}

export async function getMaintenanceReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.status) params.set("status", options.status);
    if (options.maintenance_type) params.set("maintenance_type", options.maintenance_type);
    if (options.from_date) params.set("from_date", options.from_date);
    if (options.to_date) params.set("to_date", options.to_date);
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/maintenance${query}`);
}

export async function getCommandReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.computer_id) params.set("computer_id", options.computer_id);
    if (options.command_type) params.set("command_type", options.command_type);
    if (options.status) params.set("status", options.status);
    if (options.from_date) params.set("from_date", options.from_date);
    if (options.to_date) params.set("to_date", options.to_date);
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/commands${query}`);
}

export async function getAuditReport(options = {}) {
  let query = "";
  if (options && typeof options === "object") {
    const params = new URLSearchParams();
    if (options.action) params.set("action", options.action);
    if (options.user_id) params.set("user_id", options.user_id);
    if (options.result) params.set("result", options.result);
    if (options.from_date) params.set("from_date", options.from_date);
    if (options.to_date) params.set("to_date", options.to_date);
    if (options.page !== undefined) params.set("page", options.page);
    if (options.limit !== undefined) params.set("limit", options.limit);
    const qs = params.toString();
    if (qs) query = `?${qs}`;
  }
  return fetchWithAuth(`/reports/audit${query}`);
}

export async function downloadReportCSV(reportType, options = {}) {
  let token = getAccessToken();

  // Proactive check: refresh token if expired
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

  const params = new URLSearchParams();
  params.set("report_type", reportType || "computer");
  if (options.period) params.set("period", options.period);
  if (options.from_date) params.set("from_date", options.from_date);
  if (options.to_date) params.set("to_date", options.to_date);
  if (options.computer_id) params.set("computer_id", options.computer_id);
  if (options.search) params.set("search", options.search.trim());
  if (options.status) params.set("status", options.status);
  if (options.severity) params.set("severity", options.severity);
  if (options.maintenance_type) params.set("maintenance_type", options.maintenance_type);
  if (options.command_type) params.set("command_type", options.command_type);
  if (options.action) params.set("action", options.action);
  if (options.result) params.set("result", options.result);

  const queryStr = params.toString();
  const endpoint = `/reports/export${queryStr ? `?${queryStr}` : ""}`;
  const url = buildApiUrl(endpoint);

  let response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  } catch (netErr) {
    throw new ApiError(`Network error: ${netErr.message || "Failed to download report"}`, 0, null, netErr);
  }

  // Reactive retry on 401
  if (response.status === 401) {
    try {
      const newToken = await refreshToken();
      response = await fetch(url, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${newToken}`,
        },
      });
    } catch {
      clearTokens();
      throw new ApiError("Session expired. Please log in again.", 401);
    }
  }

  if (!response.ok) {
    let errorDetail = `Failed to export report CSV (HTTP ${response.status})`;
    try {
      const err = await response.json();
      errorDetail = err.detail || errorDetail;
    } catch {
      // ignore non-json errors
    }
    if (response.status === 401) {
      clearTokens();
    }
    throw new ApiError(errorDetail, response.status);
  }

  const blob = await response.blob();
  let filename = `SLMS-${reportType || "export"}-Report.csv`;
  const disposition = response.headers.get("Content-Disposition");
  if (disposition && disposition.includes("filename=")) {
    const match = disposition.match(/filename="?([^";]+)"?/);
    if (match && match[1]) filename = match[1].trim();
  }

  if (typeof window !== "undefined" && window.URL && window.URL.createObjectURL) {
    const downloadUrl = window.URL.createObjectURL(blob);
    try {
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } finally {
      window.URL.revokeObjectURL(downloadUrl);
    }
  }

  return filename;
}

/* =====================================================
   SETTINGS & CONFIGURATION MANAGEMENT
===================================================== */

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

