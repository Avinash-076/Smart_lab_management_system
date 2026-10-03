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

