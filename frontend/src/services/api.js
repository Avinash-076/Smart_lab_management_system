const API_BASE_URL = "http://127.0.0.1:8000/api";

let authStateListeners = [];
let refreshPromise = null;

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
  return localStorage.getItem("access_token");
}

export function getRefreshToken() {
  return localStorage.getItem("refresh_token");
}

export function setTokens(accessToken, refreshToken) {
  if (accessToken) {
    localStorage.setItem("access_token", accessToken);
  }
  if (refreshToken) {
    localStorage.setItem("refresh_token", refreshToken);
  }
}

export function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
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

export function isTokenExpired(token) {
  const decoded = parseJwt(token);
  if (!decoded || !decoded.exp) return true;
  // exp is Unix timestamp in seconds; Date.now() in ms. 5-second buffer for clock skew
  return decoded.exp * 1000 <= Date.now() + 5000;
}

export function isAuthenticated() {
  const token = getAccessToken();
  const rToken = getRefreshToken();
  if (token && !isTokenExpired(token)) return true;
  if (rToken && !isTokenExpired(rToken)) return true;
  return false;
}

export async function login(username, password) {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      username: username.trim(),
      password,
    }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Login failed");
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
    throw new Error("Session expired. Please log in again.");
  }

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          refresh_token: currentRefreshToken,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        clearTokens();
        throw new Error(data.detail || "Session expired");
      }

      setTokens(data.access_token, null);
      return data.access_token;
    } catch (error) {
      clearTokens();
      throw error;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

export function logout() {
  clearTokens();
}

export async function fetchWithAuth(endpoint, options = {}) {
  let token = getAccessToken();

  // If access token is expired/missing, attempt refresh before making the request
  if (!token || isTokenExpired(token)) {
    const rToken = getRefreshToken();
    if (rToken && !isTokenExpired(rToken)) {
      try {
        token = await refreshToken();
      } catch {
        clearTokens();
        throw new Error("Session expired. Please log in again.");
      }
    } else {
      clearTokens();
      throw new Error("Authentication required.");
    }
  }

  const headers = {
    ...options.headers,
    Authorization: `Bearer ${token}`,
  };

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`;

  let response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (netErr) {
    throw new Error(`Network error: ${netErr.message}`, { cause: netErr });
  }

  // Handle 401 Unauthorized with single retry after refreshing token
  if (response.status === 401 && !options._isRetry) {
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
      throw new Error("Session expired. Please log in again.");
    }
  }

  const data = await response.json().catch(() => null);

  if (!response.ok) {
    if (response.status === 401) {
      clearTokens();
    }
    throw new Error(data?.detail || `Request failed with status ${response.status}`);
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

