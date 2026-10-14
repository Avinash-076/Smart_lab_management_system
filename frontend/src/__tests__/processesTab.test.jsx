import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderToString } from "react-dom/server";
import ProcessSummaryCards from "../features/computers/components/ProcessSummaryCards";
import ProcessFilters from "../features/computers/components/ProcessFilters";
import ProcessStatusDistribution from "../features/computers/components/ProcessStatusDistribution";
import TopProcessesByCPU from "../features/computers/components/TopProcessesByCPU";
import RunningProcessesTable from "../features/computers/components/RunningProcessesTable";
import ProcessesTab from "../features/computers/components/ProcessesTab";
import {
  getComputerProcesses,
  getComputerProcessesSummary,
  exportProcessesToCsv,
} from "../services/processService";
import { setTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("Processes Tab Component & Service Tests", () => {
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
          "x-total-count": "124",
        }),
        json: async () => [
          {
            id: 1,
            pid: 4820,
            name: "chrome.exe",
            user: "LabUser",
            cpu_percent: 18.4,
            memory_percent: 5.2,
            memory_mb: 412.3,
            executable_path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            status: "running",
          },
        ],
      };
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  describe("ProcessSummaryCards", () => {
    it("renders 4 metric cards matching reference design", () => {
      const summary = {
        total_running: 124,
        total_cpu_percent: 28.0,
        total_memory_mb: 2867.2, // ~2.8 GB
        total_memory_percent: 46.0,
        last_scan: "2026-10-14T10:18:00Z",
      };

      const html = renderToString(
        <ProcessSummaryCards
          summary={summary}
          loading={false}
          onScanNow={() => {}}
          scanning={false}
        />
      );

      expect(html).toContain("Running Processes");
      expect(html).toContain("124");
      expect(html).toContain("CPU Usage");
      expect(html).toContain("28%");
      expect(html).toContain("Memory Usage");
      expect(html).toContain("2.8 GB (46%)");
      expect(html).toContain("Last Scan");
      expect(html).toContain("Scan Now");
    });

    it("handles zero and empty states cleanly", () => {
      const html = renderToString(
        <ProcessSummaryCards summary={null} loading={true} />
      );
      expect(html).toContain("Running Processes");
      expect(html).toContain("CPU Usage");
      expect(html).toContain("Memory Usage");
      expect(html).toContain("Last Scan");
    });
  });

  describe("ProcessFilters", () => {
    it("renders search input, status, CPU, memory, and user filters", () => {
      const filters = {
        search: "chrome",
        status: "running",
        cpu_usage: "all",
        memory_usage: "all",
        user: "all",
      };

      const html = renderToString(
        <ProcessFilters
          filters={filters}
          availableUsers={["LabUser", "SYSTEM", "DWM-1"]}
          availableStatuses={["running", "suspended"]}
          onApply={() => {}}
          onExport={() => {}}
          loading={false}
        />
      );

      expect(html).toContain("Search process name, PID, or path...");
      expect(html).toContain("Process Status");
      expect(html).toContain("CPU Usage");
      expect(html).toContain("Memory Usage");
      expect(html).toContain("User");
      expect(html).toContain("LabUser");
      expect(html).toContain("SYSTEM");
      expect(html).toContain("Apply");
      expect(html).toContain("Export");
    });
  });

  describe("ProcessStatusDistribution", () => {
    it("renders donut chart and status legend with counts and percentages", () => {
      const distribution = [
        { status: "Running", count: 102, percentage: 82.3 },
        { status: "Suspended", count: 8, percentage: 6.5 },
        { status: "Not Responding", count: 4, percentage: 3.2 },
        { status: "Zombie", count: 0, percentage: 0.0 },
        { status: "Others", count: 10, percentage: 8.0 },
      ];

      const html = renderToString(
        <ProcessStatusDistribution
          distribution={distribution}
          totalProcesses={124}
          loading={false}
        />
      );

      expect(html).toContain("Process Status Distribution");
      expect(html).toContain("124");
      expect(html).toContain("Processes");
      expect(html).toContain("Running");
      expect(html).toContain("102");
      expect(html).toContain("82");
      expect(html).toContain("process-legend-pct");
      expect(html).toContain("Suspended");
      expect(html).toContain("Not Responding");
      expect(html).toContain("Zombie");
      expect(html).toContain("Others");
    });

    it("handles empty distribution gracefully", () => {
      const html = renderToString(
        <ProcessStatusDistribution distribution={[]} totalProcesses={0} />
      );
      expect(html).toContain("0");
      expect(html).toContain("Processes");
    });
  });

  describe("TopProcessesByCPU", () => {
    it("renders horizontal progress bars and percentages", () => {
      const procs = [
        { pid: 4820, name: "chrome.exe", cpu_percent: 18.4 },
        { pid: 5612, name: "Code.exe", cpu_percent: 12.6 },
        { pid: 3216, name: "MsMpEng.exe", cpu_percent: 8.2 },
        { pid: 4180, name: "explorer.exe", cpu_percent: 5.1 },
        { pid: 1024, name: "dwm.exe", cpu_percent: 3.7 },
      ];

      const html = renderToString(
        <TopProcessesByCPU processes={procs} totalCpuPercent={70.0} loading={false} />
      );

      expect(html).toContain("Top Processes by CPU Usage");
      expect(html).toContain("chrome.exe");
      expect(html).toContain("18.4");
      expect(html).toContain("Code.exe");
      expect(html).toContain("12.6");
      expect(html).toContain("MsMpEng.exe");
      expect(html).toContain("explorer.exe");
      expect(html).toContain("dwm.exe");
    });

    it("handles empty top processes gracefully", () => {
      const html = renderToString(
        <TopProcessesByCPU processes={[]} totalCpuPercent={0} loading={false} />
      );
      expect(html).toContain("No active process CPU utilization recorded.");
    });
  });

  describe("RunningProcessesTable", () => {
    it("renders table headers, row numbers, process icons, and actions", () => {
      const processes = [
        {
          id: 1,
          pid: 4820,
          name: "chrome.exe",
          status: "running",
          cpu_percent: 18.4,
          memory_mb: 412.3,
          user: "LabUser",
          executable_path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        },
      ];

      const html = renderToString(
        <RunningProcessesTable
          processes={processes}
          totalCount={124}
          page={1}
          pageSize={10}
          onPageChange={() => {}}
          sortConfig={{ key: "cpu_percent", direction: "desc" }}
          onSortChange={() => {}}
          loading={false}
          error=""
        />
      );

      expect(html).toContain("Running Processes");
      expect(html).toContain("124");
      expect(html).toContain("Process Name");
      expect(html).toContain("PID");
      expect(html).toContain("Status");
      expect(html).toContain("CPU Usage");
      expect(html).toContain("Memory Usage");
      expect(html).toContain("User");
      expect(html).toContain("Executable Path");
      expect(html).toContain("Actions");
      expect(html).toContain("chrome.exe");
      expect(html).toContain("4820");
      expect(html).toContain("18.4");
      expect(html).toContain("412.3 MB");
      expect(html).toContain("LabUser");
      expect(html).toContain("Showing");
      expect(html).toContain("entries");
    });

    it("renders empty state when process list is empty", () => {
      const html = renderToString(
        <RunningProcessesTable
          processes={[]}
          totalCount={0}
          page={1}
          pageSize={10}
          onPageChange={() => {}}
          sortConfig={{ key: "cpu_percent", direction: "desc" }}
          onSortChange={() => {}}
          loading={false}
          error=""
        />
      );

      expect(html).toContain("No matching processes found");
    });
  });

  describe("ProcessesTab", () => {
    it("renders the coordinator component without throwing", () => {
      const html = renderToString(
        <ProcessesTab computerId={9} computer={{ id: 9, hostname: "LAB-PC-03" }} />
      );

      expect(html).toContain("process-filter-toolbar");
      expect(html).toContain("Process Status Distribution");
      expect(html).toContain("Top Processes by CPU Usage");
      expect(html).toContain("running-processes-table-card");
    });
  });

  describe("processService", () => {
    it("getComputerProcesses formats query parameters correctly", async () => {
      const res = await getComputerProcesses(9, {
        search: "chrome",
        status: "running",
        cpu_min: 5,
        memory_min_mb: 100,
        user: "LabUser",
        limit: 10,
        offset: 0,
      });

      expect(lastFetchCall.url).toContain("/api/clients/9/processes?");
      expect(lastFetchCall.url).toContain("search=chrome");
      expect(lastFetchCall.url).toContain("status=running");
      expect(lastFetchCall.url).toContain("cpu_min=5");
      expect(lastFetchCall.url).toContain("memory_min_mb=100");
      expect(lastFetchCall.url).toContain("user=LabUser");
      expect(res.totalCount).toBe(124);
      expect(res.data.length).toBe(1);
    });

    it("getComputerProcessesSummary calls summary endpoint", async () => {
      await getComputerProcessesSummary(9, { status: "running" });
      expect(lastFetchCall.url).toContain("/api/clients/9/processes/summary?status=running");
    });

    it("exportProcessesToCsv creates CSV content without crashing", () => {
      const sampleProcs = [
        {
          pid: 4820,
          name: "chrome.exe",
          status: "running",
          cpu_percent: 18.4,
          memory_mb: 412.3,
          user: "LabUser",
          executable_path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        },
      ];

      const blob = exportProcessesToCsv(sampleProcs, "LAB-PC-03");
      expect(blob).toBeDefined();
    });
  });
});
