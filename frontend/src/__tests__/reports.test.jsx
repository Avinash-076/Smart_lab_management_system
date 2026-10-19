import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderToString } from "react-dom/server";
import ReportHeader from "../features/reports/components/ReportHeader/ReportHeader";
import ReportTypeSelector from "../features/reports/components/ReportTypeSelector/ReportTypeSelector";
import ReportSummaryCards from "../features/reports/components/ReportSummaryCards/ReportSummaryCards";
import ReportFilters from "../features/reports/components/ReportFilters/ReportFilters";
import ReportCharts from "../features/reports/components/ReportCharts/ReportCharts";
import ReportTables from "../features/reports/components/ReportTables/ReportTables";
import Reports from "../features/reports/pages/Reports";
import {
  formatDate,
  formatDuration,
  formatGigabytes,
  getStatusBadgeClass,
  getSeverityBadgeClass,
  REPORT_CATEGORIES,
} from "../features/reports/utils/reportUtils";
import {
  getInventoryReport,
  getUsageReport,
} from "../services/reportService";
import { setTokens, clearTokens } from "../services/api";

describe("Reports Module - Utilities & Helpers", () => {
  it("formats dates safely with fallback for null or invalid input", () => {
    expect(formatDate(null)).toBe("N/A");
    expect(formatDate("")).toBe("N/A");
    expect(formatDate("2026-10-19T10:00:00Z")).toContain("2026");
  });

  it("formats seconds into human readable duration strings", () => {
    expect(formatDuration(0)).toBe("0s");
    expect(formatDuration(-10)).toBe("0s");
    expect(formatDuration(45)).toBe("45s");
    expect(formatDuration(120)).toBe("2m");
    expect(formatDuration(3660)).toBe("1h 1m");
    expect(formatDuration(7200)).toBe("2h");
  });

  it("formats gigabytes and converts to terabytes when >= 1024 GB", () => {
    expect(formatGigabytes(null)).toBe("N/A");
    expect(formatGigabytes(16.0)).toBe("16.0 GB");
    expect(formatGigabytes(512)).toBe("512.0 GB");
    expect(formatGigabytes(1024)).toBe("1.00 TB");
    expect(formatGigabytes(2048)).toBe("2.00 TB");
  });

  it("maps status and severity codes to appropriate CSS badge class names", () => {
    expect(getStatusBadgeClass("online")).toBe("badge-success");
    expect(getStatusBadgeClass("completed")).toBe("badge-success");
    expect(getStatusBadgeClass("scheduled")).toBe("badge-warning");
    expect(getStatusBadgeClass("in_progress")).toBe("badge-warning");
    expect(getStatusBadgeClass("offline")).toBe("badge-danger");
    expect(getStatusBadgeClass("failed")).toBe("badge-danger");
    expect(getStatusBadgeClass("open")).toBe("badge-orange");

    expect(getSeverityBadgeClass("critical")).toBe("badge-danger");
    expect(getSeverityBadgeClass("high")).toBe("badge-orange");
    expect(getSeverityBadgeClass("medium")).toBe("badge-warning");
    expect(getSeverityBadgeClass("low")).toBe("badge-info");
    expect(getSeverityBadgeClass("unknown")).toBe("badge-neutral");
  });
});

describe("Reports Module - Component Rendering", () => {
  const mockOverview = {
    total_computers: 12,
    online_computers: 10,
    offline_computers: 2,
    total_software_records: 154,
    unique_software_count: 42,
    total_issues: 5,
    open_issues: 2,
    resolved_issues: 3,
    critical_issues: 1,
    total_maintenance: 8,
    pending_maintenance: 3,
    completed_maintenance: 5,
    overdue_maintenance: 1,
    total_commands: 24,
    executed_commands: 22,
    failed_commands: 2,
    total_audit_events: 90,
  };

  const sampleInventoryData = {
    total_computers: 2,
    online_computers: 1,
    offline_computers: 1,
    os_distribution: [
      { os_name: "Windows 11 Pro", count: 1, percentage: 50.0 },
      { os_name: "Ubuntu 24.04", count: 1, percentage: 50.0 },
    ],
    hardware_summary: {
      total_ram_gb: 48.0,
      total_storage_gb: 1536.0,
      avg_cores: 7.0,
      total_processors: 2,
    },
    page: 1,
    limit: 25,
    total_pages: 1,
    items: [
      {
        id: 1,
        hostname: "PC-LAB-01",
        ip_address: "192.168.1.101",
        mac_address: "00:11:22:33:44:55",
        os_name: "Windows",
        os_version: "11 Pro",
        status: "online",
        last_seen: "2026-10-19T10:00:00Z",
        registered_at: "2026-10-10T10:00:00Z",
        manufacturer: "Dell Inc.",
        model: "OptiPlex 7090",
        processor_name: "Intel Core i7-11700",
        processor_cores: 8,
        ram_total_gb: 16.0,
        storage_total_gb: 512.0,
      },
    ],
  };

  it("renders ReportHeader with title, badges, and action buttons", () => {
    const html = renderToString(
      <ReportHeader
        onRefresh={() => {}}
        onExport={() => {}}
        loading={false}
        exporting={false}
        lastRefreshedAt={new Date("2026-10-19T12:00:00Z")}
        successMsg="Export ready"
        errorMsg=""
        categoryLabel="Computer Inventory"
      />
    );
    expect(html).toContain("Reports &amp; Analytics");
    expect(html).toContain("Live Database Connected");
    expect(html).toContain("Export ready");
    expect(html).toContain("Refresh");
    expect(html).toContain("Export CSV");
  });

  it("renders ReportTypeSelector with all categories and counts", () => {
    const html = renderToString(
      <ReportTypeSelector
        activeCategory="inventory"
        onSelectCategory={() => {}}
        overview={mockOverview}
      />
    );
    REPORT_CATEGORIES.forEach((cat) => {
      const safeLabel = cat.label.replace(/&/g, "&amp;");
      expect(html).toContain(safeLabel);
    });
    expect(html).toContain("12"); // total computers badge
  });

  it("renders ReportSummaryCards for Computer Inventory", () => {
    const html = renderToString(
      <ReportSummaryCards
        category="inventory"
        reportData={sampleInventoryData}
        loading={false}
      />
    );
    expect(html).toContain("Total Computers");
    expect(html).toContain("Online Hosts");
    expect(html).toContain("Total Memory");
    expect(html).toContain("Total Storage");
    expect(html).toContain("48.0 GB");
  });

  it("renders ReportFilters with search, period, and computer controls", () => {
    const html = renderToString(
      <ReportFilters
        category="inventory"
        period="24h"
        setPeriod={() => {}}
        dateFrom=""
        setDateFrom={() => {}}
        dateTo=""
        setDateTo={() => {}}
        computerId=""
        setComputerId={() => {}}
        search="Dell"
        setSearch={() => {}}
        statusFilter="online"
        setStatusFilter={() => {}}
        severityFilter=""
        setSeverityFilter={() => {}}
        maintenanceTypeFilter=""
        setMaintenanceTypeFilter={() => {}}
        commandTypeFilter=""
        setCommandTypeFilter={() => {}}
        computersList={[{ id: 1, hostname: "PC-LAB-01", ip_address: "192.168.1.101" }]}
        resetFilters={() => {}}
        activeFiltersCount={2}
      />
    );
    expect(html).toContain("Search");
    expect(html).toContain("PC-LAB-01");
    expect(html).toContain("Reset");
    expect(html).toContain("2");
  });

  it("renders ReportCharts for Computer Inventory OS distribution and hardware summary", () => {
    const html = renderToString(
      <ReportCharts
        category="inventory"
        reportData={sampleInventoryData}
        loading={false}
      />
    );
    expect(html).toContain("Operating System Distribution");
    expect(html).toContain("Windows 11 Pro");
    expect(html).toContain("Ubuntu 24.04");
    expect(html).toContain("Hardware Aggregate Capacity");
    expect(html).toContain("Average Processor Cores");
  });

  it("renders ReportTables with headers, hostname, and specs", () => {
    const html = renderToString(
      <ReportTables
        category="inventory"
        reportData={sampleInventoryData}
        loading={false}
        page={1}
        onPageChange={() => {}}
      />
    );
    expect(html).toContain("Computer Hostname");
    expect(html).toContain("PC-LAB-01");
    expect(html).toContain("Dell Inc.");
    expect(html).toContain("OptiPlex 7090");
    expect(html).toContain("16.0 GB");
  });

  it("renders meaningful empty state when no report records match", () => {
    const emptyData = { total_computers: 0, items: [] };
    const html = renderToString(
      <ReportTables
        category="inventory"
        reportData={emptyData}
        loading={false}
        page={1}
        onPageChange={() => {}}
      />
    );
    expect(html).toContain("No Report Records Found");
  });

  it("renders full Reports page container without crashing", () => {
    const html = renderToString(<Reports />);
    expect(html).toContain("reports-page-wrapper");
    expect(html).toContain("Reports &amp; Analytics");
  });
});

describe("Reports Service - API Query Builders", () => {
  let originalFetch;
  let mockStorage = {};
  let lastFetchCall = null;

  function createFakeJwt(payload) {
    const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
    const body = btoa(JSON.stringify(payload));
    return `${header}.${body}.sig`;
  }

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
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ success: true, url: String(url) }),
      };
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    clearTokens();
  });

  it("builds correct URL search parameters for getInventoryReport", async () => {
    await getInventoryReport({
      computer_id: 5,
      status: "online",
      search: "Dell",
      page: 2,
      limit: 50,
    });

    expect(lastFetchCall).not.toBeNull();
    expect(lastFetchCall.url).toContain("/reports/inventory?");
    expect(lastFetchCall.url).toContain("computer_id=5");
    expect(lastFetchCall.url).toContain("status=online");
    expect(lastFetchCall.url).toContain("search=Dell");
    expect(lastFetchCall.url).toContain("page=2");
    expect(lastFetchCall.url).toContain("limit=50");
  });

  it("builds correct URL search parameters for getUsageReport", async () => {
    await getUsageReport({
      computer_id: 3,
      search: "chrome",
      from_date: "2026-10-01T00:00:00Z",
      to_date: "2026-10-15T00:00:00Z",
      page: 1,
      limit: 25,
    });

    expect(lastFetchCall).not.toBeNull();
    expect(lastFetchCall.url).toContain("/reports/usage?");
    expect(lastFetchCall.url).toContain("computer_id=3");
    expect(lastFetchCall.url).toContain("search=chrome");
    expect(lastFetchCall.url).toContain("from_date=2026-10-01T00%3A00%3A00Z");
    expect(lastFetchCall.url).toContain("to_date=2026-10-15T00%3A00%3A00Z");
  });
});
