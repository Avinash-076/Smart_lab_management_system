import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderToString } from "react-dom/server";
import SoftwareSummaryCards from "../features/computers/components/software/SoftwareSummaryCards";
import SoftwareFilters from "../features/computers/components/software/SoftwareFilters";
import SoftwareTypeDistribution from "../features/computers/components/software/SoftwareTypeDistribution";
import TopSoftwarePublishers from "../features/computers/components/software/TopSoftwarePublishers";
import InstalledSoftwareTable from "../features/computers/components/software/InstalledSoftwareTable";
import SoftwareTab from "../features/computers/components/software/SoftwareTab";
import {
  getComputerSoftware,
  getComputerSoftwareSummary,
  exportSoftwareToCsv,
} from "../services/softwareService";
import { setTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("Software Tab Component & Service Tests", () => {
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
          "x-total-count": "156",
        }),
        json: async () => [
          {
            id: 1,
            name: "Google Chrome",
            publisher: "Google LLC",
            version: "118.0.5993.117",
            install_date: "2026-10-10T10:00:00Z",
            install_location: "C:\\Program Files\\Google\\Chrome\\",
            architecture: "64-bit",
          },
        ],
      };
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllGlobals();
  });

  const sampleSummary = {
    total_installed: 156,
    recently_installed: 8,
    potentially_outdated: null,
    last_scan: "2026-10-14T10:18:00Z",
    categories: [
      { category: "System Utilities", count: 38, percentage: 24 },
      { category: "Web Browsers", count: 20, percentage: 13 },
      { category: "Development", count: 18, percentage: 12 },
      { category: "Multimedia", count: 16, percentage: 10 },
      { category: "Office & Productivity", count: 14, percentage: 9 },
      { category: "Security", count: 12, percentage: 8 },
      { category: "Others", count: 38, percentage: 24 },
    ],
    top_publishers: [
      { publisher: "Microsoft Corporation", count: 42, percentage: 27 },
      { publisher: "Google LLC", count: 18, percentage: 12 },
      { publisher: "Mozilla Foundation", count: 12, percentage: 8 },
      { publisher: "Intel Corporation", count: 8, percentage: 5 },
      { publisher: "Realtek Semiconductor", count: 6, percentage: 4 },
      { publisher: "Others", count: 70, percentage: 45 },
    ],
    available_publishers: ["Google LLC", "Microsoft Corporation", "Mozilla Foundation"],
    available_architectures: ["64-bit", "32-bit"],
  };

  const sampleSoftwareList = [
    {
      id: 1,
      name: "Google Chrome",
      publisher: "Google LLC",
      version: "118.0.5993.117",
      install_date: "2026-10-10T10:00:00Z",
      install_location: "C:\\Program Files\\Google\\Chrome\\",
      architecture: "64-bit",
    },
    {
      id: 2,
      name: "Microsoft Visual Studio Code",
      publisher: "Microsoft Corporation",
      version: "1.84.2",
      install_date: "2026-10-05T09:00:00Z",
      install_location: "C:\\Users\\LabUser\\AppData\\Local\\Programs\\Microsoft VS Code\\",
      architecture: "64-bit",
    },
    {
      id: 3,
      name: "Microsoft Edge",
      publisher: "Microsoft Corporation",
      version: "118.0.2088.76",
      install_date: "2026-09-28T12:00:00Z",
      install_location: "C:\\Program Files (x86)\\Microsoft\\Edge\\",
      architecture: "64-bit",
    },
  ];

  it("1. renders SoftwareSummaryCards with exact counts, scan time, and honest outdated status", () => {
    const html = renderToString(
      <SoftwareSummaryCards
        summary={sampleSummary}
        loading={false}
        onScanNow={() => {}}
        scanning={false}
      />
    );

    expect(html).toContain("Total Installed Applications");
    expect(html).toContain("156");
    expect(html).toContain("Recently Installed");
    expect(html).toContain("8");
    expect(html).toContain("Potentially Outdated");
    expect(html).toContain("Catalog feed unlinked");
    expect(html).toContain("Last Scan");
    expect(html).toContain("Scan Now");
  });

  it("2. renders SoftwareFilters toolbar with search input, dropdowns, apply and export", () => {
    const filters = { search: "Chrome", publisher: "Google LLC", date_range: "7d", architecture: "64-bit" };
    const html = renderToString(
      <SoftwareFilters
        filters={filters}
        availablePublishers={sampleSummary.available_publishers}
        availableArchitectures={sampleSummary.available_architectures}
        onApply={() => {}}
        onExport={() => {}}
        loading={false}
      />
    );

    expect(html).toContain("Search software (name, publisher, etc.)...");
    expect(html).toContain("Chrome");
    expect(html).toContain("Google LLC");
    expect(html).toContain("Last 7 Days");
    expect(html).toContain("64-bit");
    expect(html).toContain("Apply");
    expect(html).toContain("Export");
  });

  it("3. renders SoftwareTypeDistribution donut chart and legend categories", () => {
    const html = renderToString(
      <SoftwareTypeDistribution
        categories={sampleSummary.categories}
        totalApplications={sampleSummary.total_installed}
        loading={false}
      />
    );

    expect(html).toContain("Software Type Distribution");
    expect(html).toContain("Applications");
    expect(html).toContain("156");
    expect(html).toContain("System Utilities");
    expect(html).toContain("38");
    expect(html).toContain("24");
    expect(html).toContain("Web Browsers");
    expect(html).toContain("20");
    expect(html).toContain("13");
  });

  it("4. renders TopSoftwarePublishers list with brand badges and progress bars", () => {
    const html = renderToString(
      <TopSoftwarePublishers
        publishers={sampleSummary.top_publishers}
        totalApplications={sampleSummary.total_installed}
        loading={false}
      />
    );

    expect(html).toContain("Top Publishers");
    expect(html).toContain("Microsoft Corporation");
    expect(html).toContain("42");
    expect(html).toContain("27");
    expect(html).toContain("Google LLC");
    expect(html).toContain("18");
    expect(html).toContain("12");
    expect(html).toContain("publisher-bar-fill");
  });

  it("5. renders InstalledSoftwareTable with full columns, architecture badges, and pagination", () => {
    const html = renderToString(
      <InstalledSoftwareTable
        softwareList={sampleSoftwareList}
        totalCount={156}
        page={1}
        pageSize={10}
        onPageChange={() => {}}
        sortConfig={{ key: "name", direction: "asc" }}
        onSortChange={() => {}}
        loading={false}
      />
    );

    expect(html).toContain("Installed Software");
    expect(html).toContain("156");
    expect(html).toContain("Google Chrome");
    expect(html).toContain("Google LLC");
    expect(html).toContain("118.0.5993.117");
    expect(html).toContain("C:\\Program Files\\Google\\Chrome\\");
    expect(html).toContain("64-bit");
    expect(html).toContain("Showing");
    expect(html).toContain("1");
    expect(html).toContain("entries");
  });

  it("6. renders SoftwareTab coordinator component with all sections", () => {
    const html = renderToString(
      <SoftwareTab
        computerId={8}
        computer={{ id: 8, hostname: "LAB-PC-03" }}
      />
    );

    expect(html).toContain("software-tab-container");
    expect(html).toContain("software-analytics-grid");
    expect(html).toContain("Software Type Distribution");
    expect(html).toContain("Top Publishers");
    expect(html).toContain("Installed Software");
  });

  it("7. softwareService calls backend API with query parameters and total count", async () => {
    const result = await getComputerSoftware(8, {
      search: "vlc",
      publisher: "VideoLAN",
      architecture: "64-bit",
      date_range: "30d",
      sort_by: "name",
      sort_order: "asc",
      limit: 10,
      offset: 0,
    });

    expect(lastFetchCall.url).toContain("/clients/8/software");
    expect(lastFetchCall.url).toContain("search=vlc");
    expect(lastFetchCall.url).toContain("publisher=VideoLAN");
    expect(lastFetchCall.url).toContain("architecture=64-bit");
    expect(lastFetchCall.url).toContain("date_range=30d");
    expect(result.totalCount).toBe(156);
    expect(Array.isArray(result.data)).toBe(true);
    expect(result.data[0].name).toBe("Google Chrome");
  });

  it("8. softwareService calls software summary API correctly", async () => {
    await getComputerSoftwareSummary(8, {
      search: "edge",
    });

    expect(lastFetchCall.url).toContain("/clients/8/software/summary");
    expect(lastFetchCall.url).toContain("search=edge");
  });

  it("9. exports software inventory to CSV without error", () => {
    const blob = exportSoftwareToCsv(sampleSoftwareList, "LAB-PC-03");
    expect(blob).toBeDefined();
    expect(blob instanceof Blob).toBe(true);
  });
});
