import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderToString } from "react-dom/server";
import FleetOverview from "../features/global-remote-control/components/FleetOverview/FleetOverview";
import TargetComputerTable from "../features/global-remote-control/components/TargetComputerTable/TargetComputerTable";
import CommandCenter from "../features/global-remote-control/components/CommandCenter/CommandCenter";
import ConfirmationModal from "../features/global-remote-control/components/CommandCenter/ConfirmationModal";
import ExecutionMonitor from "../features/global-remote-control/components/ExecutionMonitor/ExecutionMonitor";
import GlobalCommandHistory from "../features/global-remote-control/components/GlobalCommandHistory/GlobalCommandHistory";
import GlobalCommandDetailModal from "../features/global-remote-control/components/GlobalCommandHistory/GlobalCommandDetailModal";
import GlobalRemoteControlPage from "../features/global-remote-control/pages/GlobalRemoteControlPage";
import {
  getFleetOverview,
  issueBatchCommand,
  getGlobalCommands,
  exportGlobalCommandsToCsv,
} from "../services/commandService";
import { setTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

function cleanHtml(html) {
  return html.replace(/<!--.*?-->/g, "");
}

describe("Global Remote Control Feature Tests", () => {
  let originalFetch;
  let mockStorage = {};
  let lastFetchCall = null;
  let createdUrls = [];
  let clickedElements = [];

  beforeEach(() => {
    mockStorage = {};
    lastFetchCall = null;
    createdUrls = [];
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

    const mockWindow = {
      URL: {
        createObjectURL: vi.fn((blob) => {
          const url = `blob:http://localhost/${Math.random().toString(36).slice(2)}`;
          createdUrls.push({ url, blob });
          return url;
        }),
        revokeObjectURL: vi.fn(),
      },
    };
    vi.stubGlobal("window", mockWindow);
    globalThis.URL.createObjectURL = mockWindow.URL.createObjectURL;
    globalThis.URL.revokeObjectURL = mockWindow.URL.revokeObjectURL;

    const mockDoc = {
      createElement: vi.fn((tagName) => {
        const el = {
          tagName,
          attributes: {},
          setAttribute: (k, v) => {
            el.attributes[k] = v;
          },
          click: vi.fn(() => {
            clickedElements.push({ ...el });
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
    const nowSec = Math.floor(Date.now() / 1000);
    const validToken = createFakeJwt({ exp: nowSec + 3600, sub: "1" });
    setTokens(validToken, validToken);

    globalThis.fetch = vi.fn(async (url, options = {}) => {
      lastFetchCall = { url: String(url), options };
      if (String(url).includes("/commands/overview")) {
        return {
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => ({
            total_computers: 48,
            online_computers: 36,
            offline_computers: 12,
            commands_last_24h: 28,
            successful_commands_24h: 22,
            failed_commands_24h: 6,
          }),
        };
      }
      if (String(url).includes("/commands/batch")) {
        return {
          ok: true,
          status: 200,
          headers: new Headers({ "content-type": "application/json" }),
          json: async () => ({
            batch_id: "batch-123",
            command_type: "restart",
            total_targets: 2,
            successful_count: 2,
            failed_count: 0,
            results: [
              { computer_id: 1, command_id: 101, status: "pending", success: true },
              { computer_id: 2, command_id: 102, status: "pending", success: true },
            ],
          }),
        };
      }
      return {
        ok: true,
        status: 200,
        headers: new Headers({
          "content-type": "application/json",
          "x-total-count": "2",
        }),
        json: async () => [
          {
            id: 2847,
            computer_id: 1,
            computer_hostname: "LAB-PC-01",
            computer_ip: "192.168.1.101",
            command_type: "message",
            payload: "System will restart in 5 minutes",
            status: "executed",
            duration_seconds: 2.3,
            issued_by: 1,
            issued_by_username: "Admin User",
            created_at: "2026-10-14T17:25:00Z",
            result: { success: true, message: "Message delivered and displayed" },
          },
          {
            id: 2846,
            computer_id: 2,
            computer_hostname: "LAB-PC-02",
            computer_ip: "192.168.1.102",
            command_type: "lock",
            payload: null,
            status: "executed",
            duration_seconds: 2.1,
            issued_by: 1,
            issued_by_username: "Admin User",
            created_at: "2026-10-14T17:25:00Z",
            result: { success: true, message: "Workstation locked successfully" },
          },
        ],
      };
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  // 1. Fleet Overview Component
  it("renders FleetOverview with live metrics and percentage calculations", () => {
    const metrics = {
      total_computers: 48,
      online_computers: 36,
      offline_computers: 12,
      commands_last_24h: 28,
      successful_commands_24h: 22,
      failed_commands_24h: 6,
    };

    const html = cleanHtml(renderToString(<FleetOverview metrics={metrics} loading={false} />));

    expect(html).toContain("Total Computers");
    expect(html).toContain("48");
    expect(html).toContain("All registered computers");

    expect(html).toContain("Online");
    expect(html).toContain("36");
    expect(html).toContain("(75%)");

    expect(html).toContain("Offline");
    expect(html).toContain("12");
    expect(html).toContain("(25%)");

    expect(html).toContain("Commands (24h)");
    expect(html).toContain("28");
    expect(html).toContain("22 Success");
    expect(html).toContain("6 Failed");
  });

  // 2. Target Computer Table Component
  it("renders TargetComputerTable with computers, checkboxes, filters, and status badges", () => {
    const computers = [
      {
        id: 1,
        hostname: "lab-pc-01",
        ip_address: "192.168.1.101",
        status: "online",
        last_seen: new Date().toISOString(),
        lab_name: "Computer Lab A",
        location: "Building 1",
      },
      {
        id: 2,
        hostname: "lab-pc-02",
        ip_address: "192.168.1.102",
        status: "offline",
        last_seen: new Date(Date.now() - 3600000).toISOString(),
        lab_name: "Computer Lab A",
        location: "Building 1",
      },
    ];

    const selectedIds = new Set([1]);

    const html = cleanHtml(
      renderToString(
        <TargetComputerTable
          computers={computers}
          selectedIds={selectedIds}
          onToggleSelect={vi.fn()}
          onSelectAllVisible={vi.fn()}
          onClearSelection={vi.fn()}
          loading={false}
        />
      )
    );

    expect(html).toContain("Select Target Computers");
    expect(html).toContain("Choose one or more computers to execute commands");
    expect(html).toContain("Search by name, hostname or IP...");
    expect(html).toContain("All Status");
    expect(html).toContain("All Labs");
    expect(html).toContain("All Locations");
    expect(html).toContain("Reset");

    // Table rows
    expect(html).toContain("LAB-PC-01");
    expect(html).toContain("192.168.1.101");
    expect(html).toContain("Online");
    expect(html).toContain("Offline");
    expect(html).toContain("Computer Lab A");
    expect(html).toContain("Building 1");

    // Selection indicators
    expect(html).toContain("(1 selected)");
    expect(html).toContain("row-selected");
  });

  // 3. Command Center Component
  it("renders CommandCenter with selected summary and 4 command cards", () => {
    const selectedComputers = [
      { id: 1, hostname: "lab-pc-01", status: "online", ip_address: "192.168.1.101" },
      { id: 2, hostname: "lab-pc-02", status: "online", ip_address: "192.168.1.102" },
    ];

    const html = cleanHtml(
      renderToString(
        <CommandCenter
          selectedComputers={selectedComputers}
          onClearSelection={vi.fn()}
          onExecuteBatch={vi.fn()}
          isExecuting={false}
        />
      )
    );

    expect(html).toContain("Command Center");
    expect(html).toContain("2 computers selected");
    expect(html).toContain("Clear Selection");

    // 4 Action cards
    expect(html).toContain("Send Message");
    expect(html).toContain("Display a message on selected computers");
    expect(html).toContain("Type your message here...");
    expect(html).toContain("0/255");

    expect(html).toContain("Lock Workstation");
    expect(html).toContain("Lock Workstations");
    expect(html).toContain("This will immediately lock the selected workstations.");

    expect(html).toContain("Restart Computer");
    expect(html).toContain("Restart Computers");
    expect(html).toContain("This will restart the selected computers.");

    expect(html).toContain("Shutdown Computer");
    expect(html).toContain("Shutdown Computers");
    expect(html).toContain("This will shutdown the selected computers.");
  });

  it("renders CommandCenter with placeholder when 0 computers selected", () => {
    const html = cleanHtml(
      renderToString(
        <CommandCenter
          selectedComputers={[]}
          onClearSelection={vi.fn()}
          onExecuteBatch={vi.fn()}
          isExecuting={false}
        />
      )
    );

    expect(html).toContain("0 computers selected");
    expect(html).toContain("Select one or more computers from the table above");
    expect(html).toContain("card-disabled");
  });

  // 4. Confirmation Modal Component
  it("renders ConfirmationModal with targets list and action warning", () => {
    const targets = [
      { id: 1, hostname: "lab-pc-01", status: "online", ip_address: "192.168.1.101" },
      { id: 2, hostname: "lab-pc-02", status: "offline", ip_address: "192.168.1.102" },
    ];

    const html = cleanHtml(
      renderToString(
        <ConfirmationModal
          isOpen={true}
          commandType="restart"
          targets={targets}
          onConfirm={vi.fn()}
          onCancel={vi.fn()}
          loading={false}
        />
      )
    );

    expect(html).toContain("Confirm Computer Restart");
    expect(html).toContain("Restart Computers");
    expect(html).toContain("Target Computers (2)");
    expect(html).toContain("lab-pc-01");
    expect(html).toContain("lab-pc-02");
    expect(html).toContain("1 offline computer will receive this command");
    expect(html).toContain("Cancel");
  });

  // 5. Execution Monitor Component
  it("renders ExecutionMonitor with commands, duration, and auto-refresh toggle", () => {
    const commands = [
      {
        id: 2847,
        computer_id: 1,
        computer_hostname: "LAB-PC-01",
        command_type: "message",
        status: "executed",
        duration_seconds: 2.3,
        result: { success: true, message: "Message delivered and displayed" },
        created_at: "2026-10-14T17:25:00Z",
      },
    ];

    const html = cleanHtml(
      renderToString(
        <ExecutionMonitor
          commands={commands}
          loading={false}
          autoRefresh={true}
          onToggleAutoRefresh={vi.fn()}
          onViewDetails={vi.fn()}
          onNavigateToComputer={vi.fn()}
        />
      )
    );

    expect(html).toContain("Command Execution Monitor");
    expect(html).toContain("Real-time status of recently executed commands");
    expect(html).toContain("Auto refresh (10s)");
    expect(html).toContain("LAB-PC-01");
    expect(html).toContain("Send Message");
    expect(html).toContain("Success");
    expect(html).toContain("Message delivered and displayed");
    expect(html).toContain("2.3s");
  });

  // 6. Global Command History Component
  it("renders GlobalCommandHistory with filters, export button, and history table", () => {
    const commands = [
      {
        id: 2847,
        computer_id: 1,
        computer_hostname: "LAB-PC-01",
        command_type: "message",
        status: "executed",
        duration_seconds: 2.3,
        issued_by_username: "Admin User",
        created_at: "2026-10-14T17:25:00Z",
        result: { success: true, message: "Message displayed" },
      },
    ];

    const html = cleanHtml(
      renderToString(
        <GlobalCommandHistory
          commands={commands}
          totalCount={1}
          page={1}
          pageSize={10}
          onPageChange={vi.fn()}
          filters={{ dateRange: "last_7_days", commandType: "all", status: "all", search: "" }}
          onFilterChange={vi.fn()}
          onExportCsv={vi.fn()}
          loading={false}
          isExporting={false}
        />
      )
    );

    expect(html).toContain("Global Command History");
    expect(html).toContain("View and filter command history across all computers");
    expect(html).toContain("Export CSV");
    expect(html).toContain("#2847");
    expect(html).toContain("LAB-PC-01");
    expect(html).toContain("Admin User");
    expect(html).toContain("Success");
    expect(html).toContain("Showing 1 to 1 of 1 commands");
  });

  // 7. Global Command Detail Modal Component
  it("renders GlobalCommandDetailModal with command payload and output message", () => {
    const command = {
      id: 2847,
      computer_id: 1,
      computer_hostname: "LAB-PC-01",
      computer_ip: "192.168.1.101",
      command_type: "message",
      payload: "Scheduled system maintenance at 6 PM",
      status: "executed",
      duration_seconds: 2.3,
      issued_by_username: "Admin User",
      created_at: "2026-10-14T17:25:00Z",
      result: {
        success: true,
        message: "Message delivered and displayed",
        return_code: 0,
      },
    };

    const html = cleanHtml(
      renderToString(
        <GlobalCommandDetailModal command={command} onClose={vi.fn()} />
      )
    );

    expect(html).toContain("Command Details: #2847");
    expect(html).toContain("Send Message");
    expect(html).toContain("Command Executed Successfully");
    expect(html).toContain("LAB-PC-01");
    expect(html).toContain("192.168.1.101");
    expect(html).toContain("Scheduled system maintenance at 6 PM");
    expect(html).toContain("Message delivered and displayed");
    expect(html).toContain("Return Code:");
  });

  // 8. Service Integration Tests
  it("getFleetOverview calls /commands/overview", async () => {
    const res = await getFleetOverview();
    expect(lastFetchCall.url).toContain("/commands/overview");
    expect(res.total_computers).toBe(48);
    expect(res.online_computers).toBe(36);
  });

  it("issueBatchCommand posts to /commands/batch with target IDs and command type", async () => {
    const batchData = {
      computer_ids: [1, 2],
      command_type: "restart",
    };
    const res = await issueBatchCommand(batchData);
    expect(lastFetchCall.url).toContain("/commands/batch");
    expect(lastFetchCall.options.method).toBe("POST");
    expect(JSON.parse(lastFetchCall.options.body)).toEqual(batchData);
    expect(res.successful_count).toBe(2);
  });

  it("getGlobalCommands queries /commands with search and filter parameters", async () => {
    const res = await getGlobalCommands({
      command_type: "restart",
      status: "executed",
      search: "LAB-PC",
      limit: 10,
      offset: 0,
      includeHeaders: true,
    });
    expect(lastFetchCall.url).toContain("/commands?");
    expect(lastFetchCall.url).toContain("command_type=restart");
    expect(lastFetchCall.url).toContain("status=executed");
    expect(lastFetchCall.url).toContain("search=LAB-PC");
    expect(res.totalCount).toBe(2);
    expect(res.data.length).toBe(2);
  });

  it("exportGlobalCommandsToCsv fetches matching commands and triggers CSV download", async () => {
    await exportGlobalCommandsToCsv({ command_type: "restart" });
    expect(lastFetchCall.url).toContain("/commands?");
    expect(lastFetchCall.url).toContain("command_type=restart");
    expect(createdUrls.length).toBe(1);
    expect(clickedElements.length).toBe(1);
    expect(clickedElements[0].attributes.download).toContain("global_commands_history_");
  });

  // 9. Full GlobalRemoteControlPage Rendering
  it("renders full GlobalRemoteControlPage without crashing", () => {
    const html = cleanHtml(
      renderToString(
        <GlobalRemoteControlPage onViewComputer={vi.fn()} />
      )
    );

    expect(html).toContain("global-remote-page");
    expect(html).toContain("Total Computers");
    expect(html).toContain("Select Target Computers");
    expect(html).toContain("Command Center");
    expect(html).toContain("Command Execution Monitor");
    expect(html).toContain("Global Command History");
  });
});
