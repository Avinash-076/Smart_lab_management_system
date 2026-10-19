import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderToString } from "react-dom/server";
import AuditHeader from "../features/audit/components/AuditHeader/AuditHeader";
import AuditStats from "../features/audit/components/AuditStats/AuditStats";
import AuditFilters from "../features/audit/components/AuditFilters/AuditFilters";
import AuditTable from "../features/audit/components/AuditTable/AuditTable";
import AuditDetailModal from "../features/audit/components/AuditDetailModal/AuditDetailModal";
import AuditLogs from "../features/audit/pages/AuditLogs";
import {
  formatDate,
  getActionBadgeClass,
  getOutcomeBadgeClass,
  TARGET_RESOURCE_OPTIONS,
  OUTCOME_OPTIONS,
} from "../features/audit/utils/auditUtils";
import {
  getAuditLogs,
  getAuditStats,
  getAuditLogDetails,
} from "../services/auditService";
import { setTokens, clearTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("Audit Logs Module - Utilities & Helpers", () => {
  it("formats dates safely with fallback for null or empty input", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("")).toBe("—");
    expect(formatDate("2026-10-19T10:00:00Z")).toContain("2026");
  });

  it("classifies action codes into semantic badge classes", () => {
    expect(getActionBadgeClass("ISSUE_COMMAND")).toBe("audit-badge-command");
    expect(getActionBadgeClass("AGENT_REBOOT")).toBe("audit-badge-command");
    expect(getActionBadgeClass("AGENT_AUTH")).toBe("audit-badge-auth");
    expect(getActionBadgeClass("USER_LOGIN")).toBe("audit-badge-auth");
    expect(getActionBadgeClass("CREATE_USER")).toBe("audit-badge-user");
    expect(getActionBadgeClass("UPDATE_ROLE")).toBe("audit-badge-user");
    expect(getActionBadgeClass("AGENT_REGISTER")).toBe("audit-badge-agent");
    expect(getActionBadgeClass("UPDATE_SETTING")).toBe("audit-badge-setting");
    expect(getActionBadgeClass("AGENT_ISSUE_RECOVERED")).toBe("audit-badge-agent");
    expect(getActionBadgeClass("RANDOM_CUSTOM_OP")).toBe("audit-badge-default");
  });

  it("classifies outcomes into success and failure classes", () => {
    expect(getOutcomeBadgeClass("success")).toBe("audit-outcome-success");
    expect(getOutcomeBadgeClass("failure")).toBe("audit-outcome-failure");
  });

  it("exports valid filter select options", () => {
    expect(TARGET_RESOURCE_OPTIONS.length).toBeGreaterThan(5);
    expect(OUTCOME_OPTIONS.length).toBe(3);
  });
});

describe("Audit Logs Module - Component Rendering", () => {
  it("renders AuditHeader with sr-only title, live status, and action buttons", () => {
    const html = renderToString(
      <AuditHeader
        onRefresh={() => {}}
        onExport={() => {}}
        loading={false}
        exporting={false}
        lastRefreshedAt={new Date("2026-10-19T12:00:00Z")}
        successMsg="Export ready"
        errorMsg=""
      />
    );
    expect(html).toContain("Audit Logs");
    expect(html).toContain("Live Audit Stream");
    expect(html).toContain("Refresh");
    expect(html).toContain("Export CSV");
    expect(html).toContain("Export ready");
    expect(html).toContain("sr-only");
  });

  it("renders AuditStats with formatted metric cards", () => {
    const mockStats = {
      total: 550,
      success: 520,
      failure: 30,
      commands: 42,
      last_24h: 18,
    };
    const html = renderToString(
      <AuditStats stats={mockStats} loading={false} />
    );
    expect(html).toContain("Total Events");
    expect(html).toContain("550");
    expect(html).toContain("Successful Operations");
    expect(html).toContain("520");
    expect(html).toContain("Security &amp; Failures");
    expect(html).toContain("30");
    expect(html).toContain("Remote Commands");
    expect(html).toContain("42");
    expect(html).toContain("18 in last 24h");
  });

  it("renders AuditFilters with search input, selects, and date filters", () => {
    const html = renderToString(
      <AuditFilters
        search="test-keyword"
        setSearch={() => {}}
        resultFilter="success"
        setResultFilter={() => {}}
        targetTypeFilter="COMPUTER"
        setTargetTypeFilter={() => {}}
        dateFrom="2026-10-01"
        setDateFrom={() => {}}
        dateTo="2026-10-19"
        setDateTo={() => {}}
        activeFiltersCount={3}
        onResetFilters={() => {}}
        setPage={() => {}}
      />
    );
    expect(html).toContain("Audit Event Explorer");
    expect(html).toContain("test-keyword");
    expect(html).toContain("Clear Filters");
    expect(html).toContain("All Target Resources");
    expect(html).toContain("All Outcomes");
  });

  it("renders AuditTable with headers, badge records, and pagination", () => {
    const mockLogs = [
      {
        id: 551,
        created_at: "2026-10-19T12:00:00Z",
        username: "admin",
        user_id: 1,
        action: "AGENT_AUTH",
        target_type: "agent_credential",
        target_id: 10,
        result: "success",
        ip_address: "192.168.1.100",
      },
      {
        id: 550,
        created_at: "2026-10-19T11:45:00Z",
        username: null,
        user_id: null,
        action: "REBOOT",
        target_type: "COMPUTER",
        target_id: 2,
        result: "failure",
        ip_address: null,
      },
    ];

    const html = renderToString(
      <AuditTable
        logs={mockLogs}
        totalCount={2}
        totalPages={1}
        page={1}
        setPage={() => {}}
        limit={25}
        setLimit={() => {}}
        loading={false}
        onInspect={() => {}}
      />
    );

    expect(html).toContain("#551");
    expect(html).toContain("admin");
    expect(html).toContain("AGENT_AUTH");
    expect(html).toContain("SYSTEM / AGENT");
    expect(html).toContain("REBOOT");
    expect(html).toContain("192.168.1.100");
    expect(html).toContain("Showing <strong>2</strong> of <strong>2</strong>");
  });

  it("renders meaningful empty state when no audit records match", () => {
    const html = renderToString(
      <AuditTable
        logs={[]}
        totalCount={0}
        totalPages={1}
        page={1}
        setPage={() => {}}
        limit={25}
        setLimit={() => {}}
        loading={false}
        onInspect={() => {}}
      />
    );
    expect(html).toContain("No audit records found");
    expect(html).toContain("Try adjusting your search keyword");
  });

  it("renders AuditDetailModal with structured fields and copy button", () => {
    const mockLog = {
      id: 551,
      created_at: "2026-10-19T12:00:00Z",
      username: "admin",
      user_id: 1,
      action: "AGENT_AUTH",
      target_type: "agent_credential",
      target_id: 10,
      result: "success",
      ip_address: "192.168.1.100",
    };

    const html = renderToString(
      <AuditDetailModal log={mockLog} onClose={() => {}} />
    );

    expect(html).toContain("Audit Event #");
    expect(html).toContain("551");
    expect(html).toContain("ACTION CODE");
    expect(html).toContain("OUTCOME");
    expect(html).toContain("ACTOR IDENTITY");
    expect(html).toContain("SOURCE IP ADDRESS");
    expect(html).toContain("RAW AUDIT RECORD (JSON)");
    expect(html).toContain("Copy JSON");
  });

  it("renders full AuditLogs page container without crashing", () => {
    const html = renderToString(<AuditLogs />);
    expect(html).toContain("audit-logs-page-wrapper");
    expect(html).toContain("Audit Event Explorer");
  });
});

describe("Audit Service - API Query Builders", () => {
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

  it("builds correct URL search parameters for getAuditLogs", async () => {
    await getAuditLogs({
      page: 2,
      limit: 50,
      action: "LOGIN",
      result: "failure",
      search: "192.168.1",
      date_from: "2026-10-01",
      date_to: "2026-10-19",
    });

    expect(lastFetchCall).not.toBeNull();
    expect(lastFetchCall.url).toContain("/api/audit-logs?");
    expect(lastFetchCall.url).toContain("page=2");
    expect(lastFetchCall.url).toContain("limit=50");
    expect(lastFetchCall.url).toContain("action=LOGIN");
    expect(lastFetchCall.url).toContain("result=failure");
    expect(lastFetchCall.url).toContain("search=192.168.1");
    expect(lastFetchCall.url).toContain("date_from=2026-10-01");
    expect(lastFetchCall.url).toContain("date_to=2026-10-19");
  });

  it("calls /api/audit-logs/stats for getAuditStats", async () => {
    await getAuditStats();
    expect(lastFetchCall).not.toBeNull();
    expect(lastFetchCall.url).toContain("/api/audit-logs/stats");
  });

  it("calls /api/audit-logs/:id for getAuditLogDetails", async () => {
    await getAuditLogDetails(42);
    expect(lastFetchCall).not.toBeNull();
    expect(lastFetchCall.url).toContain("/api/audit-logs/42");
  });
});
