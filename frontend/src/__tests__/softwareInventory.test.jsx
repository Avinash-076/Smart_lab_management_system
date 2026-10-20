import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderToString } from "react-dom/server";
import SoftwareHeader from "../features/software/components/SoftwareHeader/SoftwareHeader";
import SoftwareSummaryCards from "../features/software/components/SoftwareSummaryCards/SoftwareSummaryCards";
import SoftwareFilters from "../features/software/components/SoftwareFilters/SoftwareFilters";
import SoftwareCharts from "../features/software/components/SoftwareCharts/SoftwareCharts";
import SoftwareTable from "../features/software/components/SoftwareTable/SoftwareTable";
import SoftwareDetailModal from "../features/software/components/SoftwareDetailModal/SoftwareDetailModal";
import ExportReportModal from "../features/software/components/ExportReportModal/ExportReportModal";
import SoftwareInventory from "../features/software/pages/SoftwareInventory";
import {
  getFleetSoftware,
  getFleetSoftwareSummary,
  exportFleetSoftwareToCsv,
} from "../services/softwareService";
import { setTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("Redesigned Software Inventory Suite", () => {
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

  const sampleSummary = {
    total_software: 217,
    unique_software: 180,
    total_computers: 5,
    computers_with_software: 5,
    different_publishers: 68,
    most_common_software: {
      name: "Google Chrome",
      publisher: "Google LLC",
      count: 5,
    },
    top_software: [
      { name: "Google Chrome", publisher: "Google LLC", count: 5, color: "#3b82f6" },
      { name: "Microsoft Edge", publisher: "Microsoft Corporation", count: 5, color: "#06b6d4" },
      { name: "Microsoft Visual C++", publisher: "Microsoft Corporation", count: 5, color: "#8b5cf6" },
      { name: "Python", publisher: "Python Software Foundation", count: 3, color: "#f59e0b" },
      { name: "Java", publisher: "Oracle Corporation", count: 2, color: "#93c5fd" },
    ],
    by_os: [
      { os_name: "Windows 10", count: 142, percentage: 65.4, color: "#3b82f6" },
      { os_name: "Windows 11", count: 58, percentage: 26.7, color: "#10b981" },
      { os_name: "Other", count: 17, percentage: 7.8, color: "#8b5cf6" },
    ],
    top_publishers: [
      { publisher: "Microsoft", count: 70, color: "#3b82f6" },
      { publisher: "Google", count: 52, color: "#10b981" },
      { publisher: "Oracle", count: 18, color: "#8b5cf6" },
      { publisher: "Python", count: 16, color: "#f59e0b" },
      { publisher: "Others", count: 61, color: "#60a5fa" },
    ],
    available_publishers: ["Google LLC", "Microsoft Corporation", "Oracle Corporation"],
    available_os: ["Windows 10", "Windows 11"],
  };

  const sampleSoftwareItems = [
    {
      id: 1,
      name: "Google Chrome",
      version: "118.0.5993.117",
      publisher: "Google LLC",
      installed_count: 5,
      total_computers: 5,
      os_display: "Windows 10/11",
      install_date: "2026-10-10",
      install_location: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
      architecture: "64-bit",
      computers: [
        { id: 1, hostname: "LAB-PC-01", ip_address: "192.168.1.101", os: "Windows 11", status: "online", install_date: "2026-10-10" },
        { id: 2, hostname: "LAB-PC-02", ip_address: "192.168.1.102", os: "Windows 10", status: "online", install_date: "2026-10-10" },
      ],
    },
    {
      id: 2,
      name: "Microsoft Edge",
      version: "118.0.2088.76",
      publisher: "Microsoft Corporation",
      installed_count: 5,
      total_computers: 5,
      os_display: "Windows 10/11",
      install_date: "2026-10-09",
      architecture: "64-bit",
      computers: [],
    },
  ];

  it("1. SoftwareHeader renders title, subtitle, and action buttons", () => {
    const html = renderToString(
      <SoftwareHeader
        onRefresh={() => {}}
        onExportReport={() => {}}
        loading={false}
        lastRefreshedAt={new Date("2026-10-20T10:30:00Z")}
        successMsg="Export completed"
      />
    );

    expect(html).toContain("Software Inventory");
    expect(html).toContain("Track and analyze software installations");
    expect(html).toContain("Export Report");
    expect(html).toContain("Refresh");
    expect(html).toContain("Export completed");
  });

  it("2. SoftwareSummaryCards renders all 4 KPI cards matching reference image", () => {
    const html = renderToString(
      <SoftwareSummaryCards
        summary={sampleSummary}
        computersCount={5}
        totalRecords={217}
      />
    );

    expect(html).toContain("Total Software");
    expect(html).toContain("217");
    expect(html).toContain("Computers with Software");
    expect(html).toContain("5 / 5");
    expect(html).toContain("100%");
    expect(html).toContain("Different Publishers");
    expect(html).toContain("68");
    expect(html).toContain("Most Common Software");
    expect(html).toContain("Google Chrome");
    expect(html).toContain("Installed on 5 computers");
  });

  it("3. SoftwareFilters renders filter fields and action buttons", () => {
    const html = renderToString(
      <SoftwareFilters
        search="chrome"
        setSearch={() => {}}
        osFilter="All OS"
        setOsFilter={() => {}}
        publisherFilter="All Publishers"
        setPublisherFilter={() => {}}
        computerFilter="All Computers"
        setComputerFilter={() => {}}
        statusFilter="All Status"
        setStatusFilter={() => {}}
        computers={[{ id: 1, hostname: "LAB-PC-01" }]}
        availablePublishers={["Google LLC", "Microsoft Corporation"]}
        availableOs={["Windows 10", "Windows 11"]}
        onApply={() => {}}
        onReset={() => {}}
      />
    );

    expect(html).toContain("Software Filters");
    expect(html).toContain("Search");
    expect(html).toContain("Operating System");
    expect(html).toContain("Publisher");
    expect(html).toContain("Computer");
    expect(html).toContain("Installation Status");
    expect(html).toContain("Apply Filters");
    expect(html).toContain("Reset");
    expect(html).toContain("Google LLC");
    expect(html).toContain("LAB-PC-01");
  });

  it("4. SoftwareCharts renders 3 analytics cards with charts and distributions", () => {
    const html = renderToString(
      <SoftwareCharts
        summary={sampleSummary}
        totalComputers={5}
        totalRecords={217}
      />
    );

    // Top Software
    expect(html).toContain("Top Software by Installations");
    expect(html).toContain("Google Chrome");
    expect(html).toContain("Microsoft Edge");
    expect(html).toContain("Python");

    // OS distribution donut chart
    expect(html).toContain("Software by Operating System");
    expect(html).toContain("Windows 10");
    expect(html).toContain("65.4%");
    expect(html).toContain("Windows 11");
    expect(html).toContain("26.7%");

    // Top Publishers vertical bar chart
    expect(html).toContain("Top Publishers");
    expect(html).toContain("Microsoft");
    expect(html).toContain("70");
    expect(html).toContain("Google");
    expect(html).toContain("52");
    expect(html).toContain("Oracle");
    expect(html).toContain("18");
  });

  it("5. SoftwareTable renders columns, branded icons, version pills, and installed badge", () => {
    const html = renderToString(
      <SoftwareTable
        softwareList={sampleSoftwareItems}
        totalCount={217}
        page={1}
        pageSize={10}
        onPageChange={() => {}}
        onPageSizeChange={() => {}}
        sortConfig={{ key: "name", direction: "asc" }}
        onSortChange={() => {}}
        tableSearch=""
        setTableSearch={() => {}}
        viewMode="table"
        onToggleViewMode={() => {}}
        selectedSoftwareIds={new Set([1])}
        onToggleSelectAll={() => {}}
        onToggleSelectItem={() => {}}
        onClearSelection={() => {}}
        onInspect={() => {}}
        onExportCsv={() => {}}
        onExportItem={() => {}}
        loading={false}
      />
    );

    expect(html).toContain("Installed Software (217)");
    expect(html).toContain("Google Chrome");
    expect(html).toContain("118.0.5993.117");
    expect(html).toContain("Google LLC");
    expect(html).toContain("5 / 5");
    expect(html).toContain("Windows 10/11");
    expect(html).toContain("Showing");
    expect(html).toContain("1 software items selected");
  });

  it("6. SoftwareDetailModal renders installation targets and paths", () => {
    const html = renderToString(
      <SoftwareDetailModal
        software={sampleSoftwareItems[0]}
        onClose={() => {}}
        onViewComputer={() => {}}
      />
    );

    expect(html).toContain("Google Chrome");
    expect(html).toContain("118.0.5993.117");
    expect(html).toContain("Google LLC");
    expect(html).toContain("Install Location");
    expect(html).toContain("C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe");
    expect(html).toContain("LAB-PC-01");
    expect(html).toContain("192.168.1.101");
    expect(html).toContain("LAB-PC-02");
    expect(html).toContain("Close");
    expect(html).toContain("Export Application Details");
  });

  it("7. ExportReportModal renders format and scope options", () => {
    const html = renderToString(
      <ExportReportModal
        isOpen={true}
        onClose={() => {}}
        softwareList={sampleSoftwareItems}
        selectedSoftwareIds={new Set()}
        totalCount={2}
      />
    );

    expect(html).toContain("Export Software Report");
    expect(html).toContain("CSV Spreadsheet");
    expect(html).toContain("JSON Data");
    expect(html).toContain("All Loaded Records");
    expect(html).toContain("Download Report");
  });

  it("8. SoftwareInventory main page integrates all components and renders correctly", () => {
    const html = renderToString(<SoftwareInventory />);

    expect(html).toContain("Software Inventory");
    expect(html).toContain("Software Filters");
    expect(html).toContain("Top Software by Installations");
    expect(html).toContain("Software by Operating System");
    expect(html).toContain("Top Publishers");
    expect(html).toContain("Installed Software");
  });

  it("9. Services getFleetSoftware and getFleetSoftwareSummary call correct endpoints", async () => {
    let capturedUrl = "";
    globalThis.fetch = vi.fn(async (url) => {
      capturedUrl = String(url);
      return {
        ok: true,
        status: 200,
        headers: new Headers({
          "content-type": "application/json",
          "x-total-count": "217",
        }),
        json: async () => sampleSoftwareItems,
      };
    });

    const fleetRes = await getFleetSoftware({ search: "chrome", limit: 10 });
    expect(capturedUrl).toContain("/software/fleet");
    expect(capturedUrl).toContain("search=chrome");
    expect(fleetRes.totalCount).toBe(217);

    await getFleetSoftwareSummary();
    expect(capturedUrl).toContain("/software/fleet/summary");
  });

  it("10. exportFleetSoftwareToCsv creates downloadable blob without errors", () => {
    expect(() => {
      exportFleetSoftwareToCsv(sampleSoftwareItems, "test_export");
    }).not.toThrow();
  });
});
