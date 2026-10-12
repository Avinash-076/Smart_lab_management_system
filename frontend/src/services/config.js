/**
 * Centralized Application Configuration Service
 *
 * Provides a single source of truth for API and WebSocket URLs,
 * with validation, normalization, and safe URL resolution.
 */

const DEFAULT_DEV_API_BASE_URL = "http://127.0.0.1:8000/api";
const DEFAULT_DEV_WS_PATH = "/ws/dashboard";

/**
 * Validates and normalizes an API base URL.
 * - Ensures valid HTTP or HTTPS protocol
 * - Strips trailing slashes
 * - Ensures '/api' suffix is present without duplication
 *
 * @param {string} rawUrl
 * @returns {string} Normalized API base URL
 */
export function normalizeApiUrl(rawUrl) {
  if (!rawUrl || typeof rawUrl !== "string") {
    throw new Error(
      "Invalid API base URL: Expected a non-empty string URL (e.g. 'http://127.0.0.1:8000/api')."
    );
  }

  const trimmed = rawUrl.trim();
  let parsed;
  try {
    parsed = new URL(trimmed);
  } catch {
    throw new Error(
      `Invalid API base URL: '${trimmed}' is not a valid absolute URL.`
    );
  }

  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error(
      `Invalid API protocol '${parsed.protocol}'. API URL must use 'http:' or 'https:'.`
    );
  }

  // Remove trailing slashes from pathname
  let pathname = parsed.pathname.replace(/\/+$/, "");

  // Ensure /api suffix is present
  if (!pathname.endsWith("/api")) {
    pathname = pathname ? `${pathname}/api` : "/api";
  }

  return `${parsed.origin}${pathname}`;
}

/**
 * Validates and normalizes a WebSocket base URL.
 * - If rawWsUrl is provided: validates ws:// or wss:// protocol and normalizes
 * - If not provided: safely derives from the normalized API URL (http -> ws, https -> wss)
 *
 * @param {string|undefined|null} rawWsUrl
 * @param {string} apiBaseUrl - Normalized API base URL
 * @returns {string} Normalized WebSocket base URL
 */
export function normalizeWsUrl(rawWsUrl, apiBaseUrl) {
  if (rawWsUrl && typeof rawWsUrl === "string" && rawWsUrl.trim()) {
    const trimmed = rawWsUrl.trim();
    let parsed;
    try {
      parsed = new URL(trimmed);
    } catch {
      throw new Error(
        `Invalid WebSocket base URL: '${trimmed}' is not a valid absolute URL.`
      );
    }

    if (parsed.protocol !== "ws:" && parsed.protocol !== "wss:") {
      throw new Error(
        `Invalid WebSocket protocol '${parsed.protocol}'. WebSocket URL must use 'ws:' or 'wss:'.`
      );
    }

    let pathname = parsed.pathname.replace(/\/+$/, "");
    if (!pathname || pathname === "/") {
      pathname = DEFAULT_DEV_WS_PATH;
    } else if (!pathname.endsWith("/ws/dashboard")) {
      pathname = `${pathname}/ws/dashboard`;
    }

    return `${parsed.protocol}//${parsed.host}${pathname}`;
  }

  // Derive from API base URL
  const normalizedApi = normalizeApiUrl(apiBaseUrl);
  const parsedApi = new URL(normalizedApi);

  const wsProtocol = parsedApi.protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${parsedApi.host}${DEFAULT_DEV_WS_PATH}`;
}

/**
 * Resolves the configured API base URL from Vite environment variables
 * or falls back to local development default.
 *
 * @returns {string} Normalized API base URL
 */
export function getApiBaseUrl() {
  const envUrl =
    typeof import.meta !== "undefined" && import.meta.env
      ? import.meta.env.VITE_API_BASE_URL
      : undefined;

  return normalizeApiUrl(envUrl || DEFAULT_DEV_API_BASE_URL);
}

/**
 * Resolves the configured WebSocket base URL from Vite environment variables
 * or derives it safely from the API base URL.
 *
 * @returns {string} Normalized WebSocket base URL
 */
export function getWsBaseUrl() {
  const envWs =
    typeof import.meta !== "undefined" && import.meta.env
      ? import.meta.env.VITE_WS_BASE_URL
      : undefined;

  return normalizeWsUrl(envWs, getApiBaseUrl());
}

/**
 * Builds a full API endpoint URL using the configured API base URL,
 * safely avoiding duplicated '/api' path segments.
 *
 * @param {string} endpoint - Path such as '/clients' or '/api/reports/export'
 * @returns {string} Full resolved API URL
 */
export function buildApiUrl(endpoint) {
  if (!endpoint || typeof endpoint !== "string") {
    return getApiBaseUrl();
  }

  // If already a full URL, return as-is
  if (endpoint.startsWith("http://") || endpoint.startsWith("https://")) {
    return endpoint;
  }

  const base = getApiBaseUrl(); // Ends with /api
  let cleanPath = endpoint.trim();

  // Strip leading slash for easier checking
  if (cleanPath.startsWith("/")) {
    cleanPath = cleanPath.slice(1);
  }

  // Strip duplicated 'api/' prefix if caller passed '/api/...'
  if (cleanPath.startsWith("api/")) {
    cleanPath = cleanPath.slice(4);
  } else if (cleanPath === "api") {
    cleanPath = "";
  }

  return cleanPath ? `${base}/${cleanPath}` : base;
}
