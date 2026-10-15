import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderToString } from "react-dom/server";
import HistoryFilters from "../features/computers/components/history/HistoryFilters";
import ApplicationUsageTrend from "../features/computers/components/history/ApplicationUsageTrend";
import TopApplicationsChart from "../features/computers/components/history/TopApplicationsChart";
import ApplicationUsageTable from "../features/computers/components/history/ApplicationUsageTable";
import HistoryTab from "../features/computers/components/history/HistoryTab";
import {
  getComputerUsage,
  getComputerUsageSummary,
} from "../services/computerService";
import { setTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("History Tab Component & Service Tests", () => {
  let originalFetch;
  let mockStorage = {};
  let lastFetchCall = null;

  beforeEach(() => {
    mockStorage = {};
    lastFetchCall = null;
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
    const nowSec = Math.floor(Date.now() / 1000);
    const validToken = createFakeJwt({ exp: nowSec + 3600, sub: "1" });
    setTokens(validToken, validToken);

    globalThis.fetch = vi.fn(async (url, options = {}) => {
      lastFetchCall = { url: String(url), options };
      return {
        ok: true,
        status: 200,
        headers: new Headers({
          "content-type": "application/json",
          "x-total-count": "48",
        }),
        json: async () => ({ success: true, url: String(url) }),
      };
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllGlobals();
  });

  const sampleIntervals = [
    { label: "08:00", duration_minutes: 25 },
    { label: "09:00", duration_minutes: 40 },
    { label: "10:00", duration_minutes: 55 },
    { label: "11:00", duration_minutes: 60 },
  ];

  const sampleTopApps = [
    {
      application_name: "Google Chrome",
      process_name: "chrome.exe",
      duration_seconds: 8100,
      formatted_duration: "2h 15m",
      percentage: 34,
    },
    {
      application_name: "Visual Studio Code",
      process_name: "Code.exe",
      duration_seconds: 4800,
      formatted_duration: "1h 20m",
      percentage: 20,
    },
    {
      application_name: "Others",
      process_name: "Others",
      duration_seconds: 5520,
      formatted_duration: "1h 32m",
      percentage: 22,
    },
  ];

  const sampleSessions = [
    {
      id: 1,
      application_name: "Google Chrome",
      process_name: "chrome.exe",
      user: "LabUser",
      start_time: "2026-10-13T10:05:00Z",
      end_time: "2026-10-13T10:18:00Z",
      duration_seconds: 780,
    },
    {
      id: 2,
      application_name: "Visual Studio Code",
      process_name: "Code.exe",
      user: "Student1",
      start_time: "2026-10-13T09:20:00Z",
      end_time: "2026-10-13T10:05:00Z",
      duration_seconds: 2700,
    },
  ];

  it("renders HistoryFilters with controls, users, applications, apply and export buttons", () => {
    const html = renderToString(
      <HistoryFilters
        timeRange="today"
        setTimeRange={() => {}}
        selectedUser="all"
        setSelectedUser={() => {}}
        selectedApp="all"
        setSelectedApp={() => {}}
        availableUsers={["LabUser", "Student1"]}
        availableApps={["chrome.exe", "Code.exe"]}
        onApply={() => {}}
        onExport={() => {}}
      />
    );

    expect(html).toContain("Time Range");
    expect(html).toContain("User");
    expect(html).toContain("Application");
    expect(html).toContain("Apply");
    expect(html).toContain("Export");
    expect(html).toContain("LabUser");
    expect(html).toContain("Student1");
    expect(html).toContain("chrome.exe");
    expect(html).toContain("Code.exe");
  });

  it("renders ApplicationUsageTrend with SVG bars and active time header", () => {
    const html = renderToString(
      <ApplicationUsageTrend
        intervals={sampleIntervals}
        totalActiveFormatted="6h 42m"
        isLoading={false}
      />
    );

    expect(html).toContain("Application Usage Trend");
    expect(html).toContain("Total Active Time:");
    expect(html).toContain("6h 42m");
    expect(html).toContain("08:00");
    expect(html).toContain("11:00");
    expect(html).toContain("<svg");
    expect(html).toContain("chart-bar");
  });

  it("renders TopApplicationsChart with donut chart, total time, and legend details", () => {
    const html = renderToString(
      <TopApplicationsChart
        topApps={sampleTopApps}
        totalActiveFormatted="6h 42m"
        totalActiveSeconds={18420}
        isLoading={false}
      />
    );

    expect(html).toContain("Top Applications by Usage Time");
    expect(html).toContain("6h 42m");
    expect(html).toContain("Total");
    expect(html).toContain("chrome.exe");
    expect(html).toContain("2h 15m");
    expect(html).toContain("(34%)");
    expect(html).toContain("Code.exe");
    expect(html).toContain("Others");
  });

  it("renders ApplicationUsageTable with brand icons, process names, user attribution, and pagination", () => {
    const html = renderToString(
      <ApplicationUsageTable
        sessions={sampleSessions}
        totalEntries={48}
        page={1}
        pageSize={10}
        onPageChange={() => {}}
        isLoading={false}
      />
    );

    expect(html).toContain("Application Usage History");
    expect(html).toContain("Google Chrome");
    expect(html).toContain("chrome.exe");
    expect(html).toContain("LabUser");
    expect(html).toContain("13m");
    expect(html).toContain("Visual Studio Code");
    expect(html).toContain("Code.exe");
    expect(html).toContain("Student1");
    expect(html).toContain("Showing");
    expect(html).toContain("of");
    expect(html).toContain("48");
    expect(html).toContain("entries");
    expect(html).toContain("pagination-controls");
  });

  it("renders HistoryTab root container with empty/loading state safely", () => {
    const html = renderToString(<HistoryTab computerId={8} />);
    expect(html).toContain("history-tab-container");
    expect(html).toContain("Application Usage Trend");
    expect(html).toContain("Top Applications by Usage Time");
    expect(html).toContain("Application Usage History");
  });

  it("calls getComputerUsageSummary with filters and parameters", async () => {
    await getComputerUsageSummary(8, {
      user: "LabUser",
      application: "chrome.exe",
    });

    expect(lastFetchCall).toBeTruthy();
    expect(lastFetchCall.url).toContain("/api/clients/8/usage/summary");
    expect(lastFetchCall.url).toContain("user=LabUser");
    expect(lastFetchCall.url).toContain("application=chrome.exe");
  });

  it("calls getComputerUsage with pagination and includeHeaders", async () => {
    const res = await getComputerUsage(8, {
      limit: 10,
      offset: 0,
      user: "LabUser",
      includeHeaders: true,
    });

    expect(lastFetchCall).toBeTruthy();
    expect(lastFetchCall.url).toContain("/api/clients/8/usage");
    expect(lastFetchCall.url).toContain("limit=10");
    expect(lastFetchCall.url).toContain("offset=0");
    expect(lastFetchCall.url).toContain("user=LabUser");
    expect(res.headers.get("x-total-count")).toBe("48");
  });
});
