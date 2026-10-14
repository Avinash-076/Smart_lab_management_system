import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderToString } from "react-dom/server";
import CommandSummaryCards from "../features/computers/components/CommandSummaryCards";
import ExecuteCommandPanel from "../features/computers/components/ExecuteCommandPanel";
import RecentCommandActivity from "../features/computers/components/RecentCommandActivity";
import CommandHistoryFilters from "../features/computers/components/CommandHistoryFilters";
import CommandHistoryTable from "../features/computers/components/CommandHistoryTable";
import CommandDetailsPanel from "../features/computers/components/CommandDetailsPanel";
import RemoteControlTab from "../features/computers/components/RemoteControlTab";
import {
  getComputerCommands,
  getComputerCommandsSummary,
  issueCommand,
  cancelCommand,
  exportCommandsToCsv,
} from "../services/commandService";
import { setTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("Remote Control Tab & Command Components Tests", () => {
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
          "x-total-count": "5",
        }),
        json: async () => [
          {
            id: 1,
            computer_id: 9,
            command_type: "message",
            payload: "Hello lab users",
            status: "executed",
            created_at: "2026-10-14T10:18:24Z",
            issued_by_username: "LabUser",
            duration_seconds: 2.3,
            result: {
              success: true,
              message: "Message sent to 1 user session(s) successfully.",
              duration_seconds: 2.3,
            },
          },
        ],
      };
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders CommandSummaryCards with real metrics", () => {
    const summary = {
      total_commands: 186,
      successful_commands: 162,
      failed_commands: 24,
      success_rate: 87.1,
      failure_rate: 12.9,
      last_execution_at: "2026-10-14T10:18:24Z",
      recent_activities: [],
    };

    const html = renderToString(
      <CommandSummaryCards summary={summary} loading={false} onRunCommand={() => {}} />
    );

    expect(html).toContain("Total Commands");
    expect(html).toContain("186");
    expect(html).toContain("Successful");
    expect(html).toContain("162");
    expect(html).toContain("(87%)");
    expect(html).toContain("Failed");
    expect(html).toContain("24");
    expect(html).toContain("(13%)");
    expect(html).toContain("Last Execution");
    expect(html).toContain("Run Command");
  });

  it("renders ExecuteCommandPanel with all 4 command choices and online computer state", () => {
    const html = renderToString(
      <ExecuteCommandPanel
        isOnline={true}
        onExecute={() => {}}
        executing={false}
      />
    );

    expect(html).toContain("Execute Command");
    expect(html).toContain("Computer is online");
    expect(html).toContain("Send Message");
    expect(html).toContain("Lock Workstation");
    expect(html).toContain("Restart Computer");
    expect(html).toContain("Shutdown Computer");
    expect(html).toContain("Message Text");
    expect(html).toContain("Clear");
  });

  it("renders ExecuteCommandPanel offline state", () => {
    const html = renderToString(
      <ExecuteCommandPanel
        isOnline={false}
        onExecute={() => {}}
        executing={false}
      />
    );

    expect(html).toContain("Computer is offline");
  });

  it("renders RecentCommandActivity list with status indicators", () => {
    const activities = [
      {
        id: 1,
        command_type: "message",
        status: "executed",
        created_at: "2026-10-14T10:18:00Z",
        success: true,
      },
      {
        id: 2,
        command_type: "shutdown",
        status: "failed",
        created_at: "2026-10-13T21:15:00Z",
        success: false,
      },
    ];

    const html = renderToString(
      <RecentCommandActivity
        activities={activities}
        loading={false}
        onSelectCommand={() => {}}
      />
    );

    expect(html).toContain("Recent Activity (Last 24 Hours)");
    expect(html).toContain("Message command executed");
    expect(html).toContain("Shutdown command executed");
    expect(html).toContain("Success");
    expect(html).toContain("Failed");
  });

  it("renders CommandHistoryFilters controls", () => {
    const html = renderToString(
      <CommandHistoryFilters
        filters={{ search: "", status: "all", date_range: "30d" }}
        onFilterChange={() => {}}
        onApply={() => {}}
        onExport={() => {}}
        exporting={false}
      />
    );

    expect(html).toContain("Search commands, message text, or user...");
    expect(html).toContain("All Status");
    expect(html).toContain("Last 30 Days");
    expect(html).toContain("Apply");
    expect(html).toContain("Export");
  });

  it("renders CommandHistoryTable rows with real timestamps, users, duration, and status", () => {
    const commands = [
      {
        id: 101,
        command_type: "restart",
        status: "executed",
        created_at: "2026-10-14T08:45:12Z",
        issued_by_username: "Admin",
        duration_seconds: 4.1,
        result: {
          success: true,
          message: "Reboot sequence initiated.",
          duration_seconds: 4.1,
        },
      },
    ];

    const html = renderToString(
      <CommandHistoryTable
        commands={commands}
        loading={false}
        selectedCommandId={null}
        onSelectCommand={() => {}}
        onCancelCommand={() => {}}
        page={1}
        pageSize={5}
        totalCount={1}
      />
    );

    expect(html).toContain("Restart Computer");
    expect(html).toContain("Admin");
    expect(html).toContain("Success");
    expect(html).toContain("4.1s");
    expect(html).toContain("View");
  });

  it("renders CommandDetailsPanel with result and raw data tabs", () => {
    const command = {
      id: 50,
      command_type: "message",
      status: "executed",
      created_at: "2026-10-14T10:18:24Z",
      executed_at: "2026-10-14T10:18:26Z",
      issued_by_username: "LabUser",
      duration_seconds: 2.3,
      payload: "Lab closing in 15 mins",
      result: {
        success: true,
        message: "Message sent to 1 user session(s) successfully.",
        duration_seconds: 2.3,
      },
    };

    const html = renderToString(
      <CommandDetailsPanel
        command={command}
        onClose={() => {}}
        computer={{ hostname: "LAB-PC-03" }}
      />
    );

    expect(html).toContain("Command Details");
    expect(html).toContain("Command Executed Successfully");
    expect(html).toContain("Send Message");
    expect(html).toContain("LabUser");
    expect(html).toContain("2.3 seconds");
    expect(html).toContain("Message sent to 1 user session(s) successfully.");
    expect(html).toContain("Raw Data");
  });

  it("renders full RemoteControlTab layout", () => {
    const html = renderToString(
      <RemoteControlTab
        computerId={9}
        computer={{ id: 9, hostname: "LAB-PC-03", status: "online" }}
      />
    );

    expect(html).toContain("execute-command-panel");
    expect(html).toContain("Execute Command");
    expect(html).toContain("Recent Activity (Last 24 Hours)");
    expect(html).toContain("Command History");
  });

  it("calls getComputerCommandsSummary API service correctly", async () => {
    await getComputerCommandsSummary(9);
    expect(lastFetchCall.url).toContain("/api/commands/9/summary");
  });

  it("calls getComputerCommands API service with query filters", async () => {
    await getComputerCommands(9, {
      search: "reboot",
      status: "executed",
      page: 2,
      limit: 10,
    });
    expect(lastFetchCall.url).toContain("/api/commands/9");
    expect(lastFetchCall.url).toContain("search=reboot");
    expect(lastFetchCall.url).toContain("status=executed");
    expect(lastFetchCall.url).toContain("limit=10");
  });

  it("calls issueCommand API service correctly", async () => {
    await issueCommand(9, {
      command_type: "lock",
      payload: null,
    });
    expect(lastFetchCall.url).toContain("/api/commands/9");
    expect(lastFetchCall.options.method).toBe("POST");
    expect(lastFetchCall.options.body).toContain('"command_type":"lock"');
  });

  it("calls cancelCommand API service with computer_id parameter", async () => {
    await cancelCommand(42, 9);
    expect(lastFetchCall.url).toContain("/api/commands/42/cancel?computer_id=9");
    expect(lastFetchCall.options.method).toBe("POST");
  });

  it("calls getCommandDetails API service with computer_id parameter", async () => {
    const { getCommandDetails } = await import("../services/commandService");
    await getCommandDetails(42, 9);
    expect(lastFetchCall.url).toContain("/api/commands/detail/42?computer_id=9");
  });

  it("formats and exports CSV without crashing", () => {
    const commands = [
      {
        id: 1,
        command_type: "message",
        status: "executed",
        created_at: "2026-10-14T10:18:24Z",
        issued_by_username: "LabUser",
        duration_seconds: 2.3,
        result: {
          message: "Broadcasted",
        },
      },
    ];

    expect(() => {
      exportCommandsToCsv(commands, "LAB-PC-03");
    }).not.toThrow();
  });
});
