import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  createDashboardWebSocket,
  closeAllWebSockets,
} from "../services/websocketManager";
import { setTokens, clearTokens, logout } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

// Mock WebSocket implementation for unit tests
class MockWebSocket {
  static instances = [];

  constructor(url) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    this.close = vi.fn((code, reason) => {
      this.readyState = 3; // CLOSED
      if (this.onclose) {
        this.onclose({ code: code || 1000, reason });
      }
    });
    MockWebSocket.instances.push(this);

    // Simulate async connection success
    setTimeout(() => {
      if (this.readyState === 0) {
        this.readyState = 1; // OPEN
        if (this.onopen) this.onopen();
      }
    }, 5);
  }
}

describe("WebSocket Compatibility & Lifecycle", () => {
  let mockStorage = {};

  beforeEach(() => {
    mockStorage = {};
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket);

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
  });

  afterEach(() => {
    closeAllWebSockets();
    clearTokens();
    vi.restoreAllMocks();
  });

  it("connects to configured WebSocket endpoint with access token and not refresh token", async () => {
    const nowSec = Math.floor(Date.now() / 1000);
    const access = createFakeJwt({ exp: nowSec + 900, sub: "1", type: "access" });
    const refresh = createFakeJwt({ exp: nowSec + 28800, sub: "1", type: "refresh" });
    setTokens(access, refresh);

    let status = null;
    const client = createDashboardWebSocket({
      onStatusChange: (s) => {
        status = s;
      },
    });

    // Wait for async connect
    await new Promise((r) => setTimeout(r, 15));

    expect(MockWebSocket.instances.length).toBe(1);
    const ws = MockWebSocket.instances[0];

    expect(ws.url).toContain("/ws/dashboard");
    expect(ws.url).toContain(`token=${encodeURIComponent(access)}`);
    expect(ws.url).not.toContain(encodeURIComponent(refresh));
    expect(status).toBe("connected");

    client.close();
  });

  it("proactively refreshes expired access token before WebSocket connection", async () => {
    const nowSec = Math.floor(Date.now() / 1000);
    const expiredAccess = createFakeJwt({ exp: nowSec - 50, sub: "1" });
    const validRefresh = createFakeJwt({ exp: nowSec + 10000, sub: "1" });
    const freshAccess = createFakeJwt({ exp: nowSec + 900, sub: "1" });

    setTokens(expiredAccess, validRefresh);

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: freshAccess }),
    });

    const client = createDashboardWebSocket();
    await new Promise((r) => setTimeout(r, 20));

    expect(MockWebSocket.instances.length).toBe(1);
    const ws = MockWebSocket.instances[0];
    expect(ws.url).toContain(`token=${encodeURIComponent(freshAccess)}`);

    client.close();
  });

  it("closes all active WebSocket connections on logout", async () => {
    const nowSec = Math.floor(Date.now() / 1000);
    setTokens(createFakeJwt({ exp: nowSec + 900, sub: "1" }), "ref");

    const client1 = createDashboardWebSocket();
    const client2 = createDashboardWebSocket();

    await new Promise((r) => setTimeout(r, 15));
    expect(MockWebSocket.instances.length).toBe(2);

    // Logout
    logout();

    expect(MockWebSocket.instances[0].close).toHaveBeenCalled();
    expect(MockWebSocket.instances[1].close).toHaveBeenCalled();

    client1.close();
    client2.close();
  });

  it("stops reconnecting on 4001 unauthorized rejection", async () => {
    const nowSec = Math.floor(Date.now() / 1000);
    setTokens(createFakeJwt({ exp: nowSec + 900, sub: "1" }), "ref");

    let finalStatus = null;
    const client = createDashboardWebSocket({
      onStatusChange: (s) => {
        finalStatus = s;
      },
    });

    await new Promise((r) => setTimeout(r, 15));
    const ws = MockWebSocket.instances[0];

    // Simulate backend closing socket due to auth failure (4001)
    ws.onclose({ code: 4001, reason: "Unauthorized" });

    await new Promise((r) => setTimeout(r, 25));
    // Should NOT have attempted reconnection
    expect(MockWebSocket.instances.length).toBe(1);
    expect(finalStatus).toBe("disconnected");

    client.close();
  });
});
