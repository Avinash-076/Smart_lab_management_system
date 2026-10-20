import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderToString } from "react-dom/server";
import DashboardClock from "../features/dashboard/components/DashboardClock/DashboardClock";
import DashboardSummaryCards from "../features/dashboard/components/DashboardSummaryCards/DashboardSummaryCards";
import SystemOverviewCard from "../features/dashboard/components/SystemOverviewCard/SystemOverviewCard";
import ResourceUsageCard from "../features/dashboard/components/ResourceUsageCard/ResourceUsageCard";
import RecentAlertsCard from "../features/dashboard/components/RecentAlertsCard/RecentAlertsCard";
import LiveSystemTable from "../features/dashboard/components/LiveSystemTable/LiveSystemTable";
import QuickActionsCard from "../features/dashboard/components/QuickActionsCard/QuickActionsCard";
import ReportsAnalyticsCard from "../features/dashboard/components/ReportsAnalyticsCard/ReportsAnalyticsCard";
import DashboardCommandModals from "../features/dashboard/components/DashboardModals/DashboardCommandModals";
import Dashboard from "../features/dashboard/Dashboard";
import { setTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("Redesigned SLMS Dashboard Suite", () => {
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
    const nowSec = Math.floor(Date.now() / 1000);
    const validToken = createFakeJwt({ exp: nowSec + 3600, sub: "1" });
    setTokens(validToken, validToken);
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllGlobals();
  });

  const sampleComputers = [
    {
      id: 1,
      hostname: "PC-01",
      ip_address: "192.168.1.101",
      status: "online",
      os_name: "Windows 11",
      avg_cpu: 23,
      avg_ram: 45,
      avg_disk: 60,
      last_seen: new Date().toISOString(),
    },
    {
      id: 2,
      hostname: "PC-02",
      ip_address: "192.168.1.102",
      status: "online",
      os_name: "Windows 10",
      avg_cpu: 73,
      avg_ram: 88,
      avg_disk: 15,
      last_seen: new Date().toISOString(),
    },
    {
      id: 3,
      hostname: "PC-03",
      ip_address: "192.168.1.103",
      status: "offline",
      os_name: "Windows 10",
      avg_cpu: 0,
      avg_ram: 0,
      avg_disk: 0,
      last_seen: null,
    },
  ];

  const sampleAlerts = [
    {
      id: 101,
      computer_id: 2,
      computer_hostname: "PC-02",
      category: "ram",
      severity: "warning",
      message: "RAM usage exceeded threshold: 88%",
      created_at: new Date().toISOString(),
    },
    {
      id: 102,
      computer_id: 3,
      computer_hostname: "PC-03",
      category: "status",
      severity: "critical",
      message: "Computer is offline and not responding",
      created_at: new Date().toISOString(),
    },
  ];

  it("1. Renders DashboardClock component with formatted time", () => {
    const html = renderToString(<DashboardClock />);
    expect(html).toContain("dashboard-clock-card");
    expect(html).toContain("dashboard-clock-time");
    expect(html).toContain("dashboard-clock-date");
  });

  it("2. Renders DashboardSummaryCards with all 6 KPI cards", () => {
    const html = renderToString(
      <DashboardSummaryCards
        totalComputers={30}
        onlineComputers={28}
        offlineComputers={2}
        highRamCount={4}
        lowDiskCount={3}
        activeAlertsCount={10}
      />
    );
    expect(html).toContain("Total Computers");
    expect(html).toContain("30");
    expect(html).toContain("Online Computers");
    expect(html).toContain("28");
    expect(html).toContain("Offline Computers");
    expect(html).toContain("2");
    expect(html).toContain("High RAM Systems");
    expect(html).toContain("4");
    expect(html).toContain("Low Disk Systems");
    expect(html).toContain("3");
    expect(html).toContain("Active Alerts");
    expect(html).toContain("10");
  });

  it("3. Renders SystemOverviewCard with SVG Donut and breakdown", () => {
    const html = renderToString(
      <SystemOverviewCard
        totalComputers={30}
        onlineComputers={28}
        offlineComputers={2}
        highRamCount={4}
        lowDiskCount={3}
      />
    );
    expect(html).toContain("System Overview");
    expect(html).toContain("Total");
    expect(html).toContain("Computers");
    expect(html).toContain("Online");
    expect(html).toContain("Offline");
    expect(html).toContain("High RAM Usage");
    expect(html).toContain("Low Disk Space");
    expect(html).toContain("system-overview-donut-svg");
  });

  it("4. Renders ResourceUsageCard with 3 circular gauges and trendline", () => {
    const timeline = [
      { timestamp: "2026-10-20T10:00:00Z", avg_cpu: 35, avg_ram: 60, avg_disk: 40 },
      { timestamp: "2026-10-20T11:00:00Z", avg_cpu: 45, avg_ram: 70, avg_disk: 45 },
    ];
    const html = renderToString(
      <ResourceUsageCard
        avgCpu={42}
        avgRam={68}
        avgDisk={56}
        timeline={timeline}
        computers={sampleComputers}
        selectedSystemId="all"
      />
    );
    expect(html).toContain("Resource Usage Summary");
    expect(html).toContain("CPU Usage");
    expect(html).toContain("42%");
    expect(html).toContain("RAM Usage");
    expect(html).toContain("68%");
    expect(html).toContain("Disk Usage");
    expect(html).toContain("56%");
    expect(html).toContain("Real-time usage trends across all systems");
  });

  it("5. Renders RecentAlertsCard with alert rows and metadata", () => {
    const html = renderToString(
      <RecentAlertsCard alerts={sampleAlerts} />
    );
    expect(html).toContain("Recent Alerts");
    expect(html).toContain("PC-02");
    expect(html).toContain("RAM Alert");
    expect(html).toContain("PC-03");
  });

  it("6. Renders LiveSystemTable with rows, progress bars, and pagination", () => {
    const html = renderToString(
      <LiveSystemTable
        computers={sampleComputers}
        selectedIds={new Set([1])}
      />
    );
    expect(html).toContain("Live System Status");
    expect(html).toContain("PC-01");
    expect(html).toContain("PC-02");
    expect(html).toContain("192.168.1.101");
    expect(html).toContain("Online");
    expect(html).toContain("Offline");
    expect(html).toContain("Showing 1 to 3 of 3 computers");
  });

  it("7. Renders QuickActionsCard with 4 colored command tiles", () => {
    const html = renderToString(
      <QuickActionsCard selectedCount={2} />
    );
    expect(html).toContain("Quick Actions");
    expect(html).toContain("Restart");
    expect(html).toContain("Shutdown");
    expect(html).toContain("Lock");
    expect(html).toContain("Send Message");
    expect(html).toContain("Refresh All Systems");
    expect(html).toContain("2 selected");
  });

  it("8. Renders ReportsAnalyticsCard with 4 report tiles", () => {
    const html = renderToString(<ReportsAnalyticsCard />);
    expect(html).toContain("Reports &amp; Analytics");
    expect(html).toContain("Performance Report");
    expect(html).toContain("System Health Report");
    expect(html).toContain("Software Inventory");
    expect(html).toContain("Activity Report");
  });

  it("9. Renders DashboardCommandModals for target prompt and message", () => {
    const promptHtml = renderToString(
      <DashboardCommandModals
        modalType="select_prompt"
        actionType="restart"
      />
    );
    expect(promptHtml).toContain("Select Target Computers");
    expect(promptHtml).toContain("No computers are currently selected");

    const messageHtml = renderToString(
      <DashboardCommandModals
        modalType="send_message"
        actionType="message"
        selectedComputers={sampleComputers.slice(0, 2)}
      />
    );
    expect(messageHtml).toContain("Send Broadcast Message");
    expect(messageHtml).toContain("PC-01");
    expect(messageHtml).toContain("PC-02");
  });

  it("10. Renders full assembled Dashboard page", () => {
    globalThis.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes("/clients")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve(sampleComputers),
          headers: new Headers(),
        });
      }
      if (url.includes("/reports/utilization")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              metrics_summary: { avg_cpu_percent: 42, avg_ram_percent: 68, avg_disk_percent: 56 },
              timeline: [],
              computers: sampleComputers,
            }),
          headers: new Headers(),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve([]),
        headers: new Headers(),
      });
    });

    const html = renderToString(
      <Dashboard searchQuery="" />
    );
    expect(html).toContain("dashboard-page");
    expect(html).toContain("Summary Metrics");
    expect(html).toContain("System Analytics");
    expect(html).toContain("Monitoring and Actions");
  });
});
