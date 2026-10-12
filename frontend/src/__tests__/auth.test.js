import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  login,
  logout,
  refreshToken,
  fetchWithAuth,
  getAccessToken,
  getRefreshToken,
  setTokens,
  clearTokens,
  isAuthenticated,
  isTokenExpired,
  subscribeAuthChange,
  registerLogoutHandler,
  ApiError,
} from "../services/api";

// Helper to create a fake JWT with a specified payload
function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  const signature = "fake-sig";
  return `${header}.${body}.${signature}`;
}

describe("Authentication & Session Service", () => {
  let originalFetch;
  let mockStorage = {};

  beforeEach(() => {
    mockStorage = {};
    vi.stubGlobal("localStorage", {
      getItem: (key) => mockStorage[key] || null,
      setItem: (key, val) => {
        mockStorage[key] = String(val);
      },
      removeItem: (key) => {
        delete mockStorage[key];
      },
      clear: () => {
        mockStorage = {};
      },
    });

    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    clearTokens();
  });

  describe("Token Management & Expiration", () => {
    it("detects expired vs valid tokens accurately", () => {
      const nowSec = Math.floor(Date.now() / 1000);
      const validToken = createFakeJwt({ exp: nowSec + 300, sub: "1" });
      const expiredToken = createFakeJwt({ exp: nowSec - 10, sub: "1" });

      expect(isTokenExpired(validToken)).toBe(false);
      expect(isTokenExpired(expiredToken)).toBe(true);
      expect(isTokenExpired("invalid.jwt.token")).toBe(true);
      expect(isTokenExpired(null)).toBe(true);
    });

    it("evaluates isAuthenticated based on access and refresh tokens", () => {
      const nowSec = Math.floor(Date.now() / 1000);
      const validToken = createFakeJwt({ exp: nowSec + 300, sub: "1" });
      const expiredToken = createFakeJwt({ exp: nowSec - 10, sub: "1" });

      // No tokens
      expect(isAuthenticated()).toBe(false);

      // Valid access token
      setTokens(validToken, null);
      expect(isAuthenticated()).toBe(true);

      // Expired access token, but valid refresh token
      setTokens(expiredToken, validToken);
      expect(isAuthenticated()).toBe(true);

      // Both expired
      setTokens(expiredToken, expiredToken);
      expect(isAuthenticated()).toBe(false);
    });

    it("clears all tokens and legacy 'token' key on clearTokens", () => {
      localStorage.setItem("token", "legacy-token");
      setTokens("access-1", "refresh-1");

      clearTokens();

      expect(getAccessToken()).toBeNull();
      expect(getRefreshToken()).toBeNull();
      expect(localStorage.getItem("token")).toBeNull();
    });
  });

  describe("Login", () => {
    it("successfully logs in, stores tokens, cleans legacy keys, and notifies listeners", async () => {
      const nowSec = Math.floor(Date.now() / 1000);
      const access = createFakeJwt({ exp: nowSec + 900, sub: "42", type: "access" });
      const refresh = createFakeJwt({ exp: nowSec + 28800, sub: "42", type: "refresh" });

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => ({
          access_token: access,
          refresh_token: refresh,
          token_type: "bearer",
        }),
      });

      let authNotified = null;
      const unsubscribe = subscribeAuthChange((state) => {
        authNotified = state;
      });

      localStorage.setItem("token", "old-legacy");
      const result = await login("admin", "secret123");

      expect(result.access_token).toBe(access);
      expect(getAccessToken()).toBe(access);
      expect(getRefreshToken()).toBe(refresh);
      expect(localStorage.getItem("token")).toBeNull();
      expect(authNotified).toBe(true);

      unsubscribe();
    });

    it("throws ApiError with detail on failed login", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Incorrect username or password" }),
      });

      const errPromise = login("admin", "wrongpassword");
      await expect(errPromise).rejects.toBeInstanceOf(ApiError);
      await expect(errPromise).rejects.toThrow(
        /Incorrect username or password/
      );
      expect(getAccessToken()).toBeNull();
    });

    it("handles network error during login without crashing", async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new Error("Failed to fetch"));

      await expect(login("admin", "secret")).rejects.toThrow(/Network error/);
    });
  });

  describe("Logout", () => {
    it("clears tokens, notifies listeners, and runs registered logout handlers", () => {
      setTokens("acc", "ref");

      let authNotified = null;
      let cleanupCalled = false;

      const unsubAuth = subscribeAuthChange((state) => {
        authNotified = state;
      });
      const unsubLogout = registerLogoutHandler(() => {
        cleanupCalled = true;
      });

      logout();

      expect(getAccessToken()).toBeNull();
      expect(getRefreshToken()).toBeNull();
      expect(authNotified).toBe(false);
      expect(cleanupCalled).toBe(true);

      unsubAuth();
      unsubLogout();
    });

    it("succeeds client-side even when backend is unavailable", () => {
      setTokens("acc", "ref");
      // logout does not require server connectivity
      expect(() => logout()).not.toThrow();
      expect(getAccessToken()).toBeNull();
    });

    it("is safe to call repeatedly", () => {
      expect(() => {
        logout();
        logout();
        logout();
      }).not.toThrow();
      expect(getAccessToken()).toBeNull();
    });
  });

  describe("Token Refresh & Concurrency", () => {
    it("proactively refreshes an expired access token before making request", async () => {
      const nowSec = Math.floor(Date.now() / 1000);
      const expiredAccess = createFakeJwt({ exp: nowSec - 20, sub: "1" });
      const validRefresh = createFakeJwt({ exp: nowSec + 10000, sub: "1" });
      const newAccess = createFakeJwt({ exp: nowSec + 900, sub: "1" });

      setTokens(expiredAccess, validRefresh);

      const fetchMock = vi.fn();
      // First call to /auth/refresh
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ access_token: newAccess, token_type: "bearer" }),
      });
      // Second call to actual endpoint /clients
      fetchMock.mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => [{ id: 1, hostname: "PC-01" }],
      });

      globalThis.fetch = fetchMock;

      const data = await fetchWithAuth("/clients");
      expect(data).toEqual([{ id: 1, hostname: "PC-01" }]);
      expect(getAccessToken()).toBe(newAccess);
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it("shares a single refresh operation across multiple simultaneous 401 requests", async () => {
      const nowSec = Math.floor(Date.now() / 1000);
      const currentAccess = createFakeJwt({ exp: nowSec + 500, sub: "1" });
      const validRefresh = createFakeJwt({ exp: nowSec + 10000, sub: "1" });
      const newAccess = createFakeJwt({ exp: nowSec + 900, sub: "1" });

      setTokens(currentAccess, validRefresh);

      let refreshCalls = 0;
      globalThis.fetch = vi.fn().mockImplementation(async (url, init) => {
        if (url.includes("/auth/refresh")) {
          refreshCalls++;
          // Simulate network latency for refresh
          await new Promise((r) => setTimeout(r, 20));
          return {
            ok: true,
            status: 200,
            json: async () => ({ access_token: newAccess }),
          };
        }

        // Check if caller sent the new token (retry) or old token (first attempt)
        const authHeader = init?.headers?.Authorization || "";
        if (authHeader.includes(newAccess)) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ success: true, url }),
          };
        }

        // Return 401 on old token
        return {
          ok: false,
          status: 401,
          json: async () => ({ detail: "Token expired" }),
        };
      });

      // Fire 3 simultaneous requests that all receive 401
      const [res1, res2, res3] = await Promise.all([
        fetchWithAuth("/clients/1"),
        fetchWithAuth("/clients/2"),
        fetchWithAuth("/clients/3"),
      ]);

      expect(res1.success).toBe(true);
      expect(res2.success).toBe(true);
      expect(res3.success).toBe(true);

      // Verify that exactly ONE refresh request was made to /auth/refresh!
      expect(refreshCalls).toBe(1);
      expect(getAccessToken()).toBe(newAccess);
    });

    it("retries original request no more than once on persistent 401", async () => {
      const nowSec = Math.floor(Date.now() / 1000);
      const currentAccess = createFakeJwt({ exp: nowSec + 500, sub: "1" });
      const validRefresh = createFakeJwt({ exp: nowSec + 10000, sub: "1" });
      const newAccess = createFakeJwt({ exp: nowSec + 900, sub: "1" });

      setTokens(currentAccess, validRefresh);

      let clientCalls = 0;
      globalThis.fetch = vi.fn().mockImplementation(async (url) => {
        if (url.includes("/auth/refresh")) {
          return {
            ok: true,
            status: 200,
            json: async () => ({ access_token: newAccess }),
          };
        }

        // The endpoint keeps returning 401 even after refresh
        clientCalls++;
        return {
          ok: false,
          status: 401,
          json: async () => ({ detail: "Unauthorized" }),
        };
      });

      await expect(fetchWithAuth("/clients")).rejects.toThrow(/Unauthorized/);
      // Initial call + exactly 1 retry = 2 calls max (no infinite loop)
      expect(clientCalls).toBe(2);
      expect(getAccessToken()).toBeNull(); // cleared on unrecoverable 401
    });

    it("clears tokens and notifies listeners when refresh fails", async () => {
      const nowSec = Math.floor(Date.now() / 1000);
      const expiredRefresh = createFakeJwt({ exp: nowSec - 100, sub: "1" });
      setTokens("acc", expiredRefresh);

      let authNotified = null;
      subscribeAuthChange((s) => {
        authNotified = s;
      });

      await expect(refreshToken()).rejects.toThrow(/Session expired/);
      expect(getAccessToken()).toBeNull();
      expect(getRefreshToken()).toBeNull();
      expect(authNotified).toBe(false);
    });

    it("does not clear tokens on 403 Forbidden responses", async () => {
      const nowSec = Math.floor(Date.now() / 1000);
      const validAccess = createFakeJwt({ exp: nowSec + 900, sub: "1" });
      setTokens(validAccess, "ref");

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({ detail: "Permission denied for MANAGE_USERS" }),
      });

      let authNotified = null;
      subscribeAuthChange((s) => {
        authNotified = s;
      });

      await expect(fetchWithAuth("/users")).rejects.toThrow(
        /Permission denied for MANAGE_USERS/
      );

      // 403 must NOT wipe tokens or trigger logout
      expect(getAccessToken()).toBe(validAccess);
      expect(authNotified).toBeNull();
    });
  });
});
