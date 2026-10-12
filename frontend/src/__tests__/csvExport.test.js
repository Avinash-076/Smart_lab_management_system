import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { downloadReportCSV } from "../services/reportService";
import { setTokens, clearTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("CSV Report Export", () => {
  let originalFetch;
  let mockStorage = {};
  let createdUrls = [];
  let revokedUrls = [];
  let clickedElements = [];

  beforeEach(() => {
    mockStorage = {};
    createdUrls = [];
    revokedUrls = [];
    clickedElements = [];

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

    // Mock window and document for headless environment
    const mockWindow = {
      URL: {
        createObjectURL: vi.fn((blob) => {
          const url = `blob:http://localhost/${Math.random().toString(36).slice(2)}`;
          createdUrls.push({ url, blob });
          return url;
        }),
        revokeObjectURL: vi.fn((url) => {
          revokedUrls.push(url);
        }),
      },
    };
    vi.stubGlobal("window", mockWindow);

    const mockDoc = {
      createElement: vi.fn((tagName) => {
        const el = {
          tagName,
          href: "",
          download: "",
          click: vi.fn(() => {
            clickedElements.push({
              href: el.href,
              download: el.download,
            });
          }),
        };
        return el;
      }),
      body: {
        appendChild: vi.fn(),
        removeChild: vi.fn(),
      },
    };
    vi.stubGlobal("document", mockDoc);

    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    clearTokens();
  });

  it("uses the configured API base URL, Bearer authorization, and preserves all query filters", async () => {
    const nowSec = Math.floor(Date.now() / 1000);
    const token = createFakeJwt({ exp: nowSec + 900, sub: "1" });
    setTokens(token, "refresh");

    let requestedUrl = null;
    let authHeader = null;

    globalThis.fetch = vi.fn().mockImplementation(async (url, init) => {
      requestedUrl = url;
      authHeader = init?.headers?.Authorization;
      return {
        ok: true,
        status: 200,
        headers: {
          get: (header) =>
            header.toLowerCase() === "content-disposition"
              ? 'attachment; filename="SLMS-issues-custom.csv"'
              : null,
        },
        blob: async () => new Blob(["col1,col2\nval1,val2"], { type: "text/csv" }),
      };
    });

    const options = {
      period: "custom",
      from_date: "2026-10-01T00:00:00Z",
      to_date: "2026-10-12T23:59:59Z",
      computer_id: 5,
      search: "printer",
      status: "open",
      severity: "high",
    };

    const filename = await downloadReportCSV("issues", options);

    expect(filename).toBe("SLMS-issues-custom.csv");
    expect(authHeader).toBe(`Bearer ${token}`);
    expect(requestedUrl).toContain("/api/reports/export");
    expect(requestedUrl).toContain("report_type=issues");
    expect(requestedUrl).toContain("period=custom");
    expect(requestedUrl).toContain("from_date=2026-10-01T00%3A00%3A00Z");
    expect(requestedUrl).toContain("to_date=2026-10-12T23%3A59%3A59Z");
    expect(requestedUrl).toContain("computer_id=5");
    expect(requestedUrl).toContain("search=printer");
    expect(requestedUrl).toContain("status=open");
    expect(requestedUrl).toContain("severity=high");

    // Check anchor click and URL cleanup
    expect(clickedElements.length).toBe(1);
    expect(clickedElements[0].download).toBe("SLMS-issues-custom.csv");
    expect(revokedUrls.length).toBe(1);
    expect(revokedUrls[0]).toBe(createdUrls[0].url);
  });

  it("extracts filename accurately and falls back safely when header is absent", async () => {
    const nowSec = Math.floor(Date.now() / 1000);
    setTokens(createFakeJwt({ exp: nowSec + 900, sub: "1" }), "ref");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: {
        get: () => null, // No content-disposition
      },
      blob: async () => new Blob(["test"], { type: "text/csv" }),
    });

    const filename = await downloadReportCSV("software");
    expect(filename).toBe("SLMS-software-Report.csv");
    expect(clickedElements[0].download).toBe("SLMS-software-Report.csv");
    expect(revokedUrls.length).toBe(1);
  });

  it("handles server errors and extracts error detail", async () => {
    const nowSec = Math.floor(Date.now() / 1000);
    setTokens(createFakeJwt({ exp: nowSec + 900, sub: "1" }), "ref");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 403,
      json: async () => ({
        detail: "Your role does not have permission to export reports",
      }),
    });

    await expect(downloadReportCSV("audit")).rejects.toThrow(
      /Your role does not have permission to export reports/
    );
  });

  it("retries on 401 using refreshed access token", async () => {
    const nowSec = Math.floor(Date.now() / 1000);
    const expiredToken = createFakeJwt({ exp: nowSec + 300, sub: "1" });
    const newToken = createFakeJwt({ exp: nowSec + 900, sub: "1" });
    const validRefresh = createFakeJwt({ exp: nowSec + 10000, sub: "1" });
    setTokens(expiredToken, validRefresh);

    globalThis.fetch = vi.fn().mockImplementation(async (url, init) => {
      if (url.includes("/auth/refresh")) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ access_token: newToken }),
        };
      }

      const auth = init?.headers?.Authorization || "";
      if (auth.includes(newToken)) {
        return {
          ok: true,
          status: 200,
          headers: { get: () => null },
          blob: async () => new Blob(["data"]),
        };
      }

      return {
        ok: false,
        status: 401,
        json: async () => ({ detail: "Token expired" }),
      };
    });

    const filename = await downloadReportCSV("computer");
    expect(filename).toBe("SLMS-computer-Report.csv");
    expect(clickedElements.length).toBe(1);
  });
});
