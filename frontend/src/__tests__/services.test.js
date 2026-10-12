import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import * as authService from "../services/authService";
import * as computerService from "../services/computerService";
import * as softwareService from "../services/softwareService";
import * as processService from "../services/processService";
import * as commandService from "../services/commandService";
import * as issueService from "../services/issueService";
import * as maintenanceService from "../services/maintenanceService";
import * as notificationService from "../services/notificationService";
import * as reportService from "../services/reportService";
import * as userService from "../services/userService";
import * as auditService from "../services/auditService";
import * as settingService from "../services/settingService";
import { setTokens, clearTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("Feature-Based Service Layer", () => {
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

  describe("authService", () => {
    it("delegates getCurrentUserProfile to /auth/me", async () => {
      const res = await authService.getCurrentUserProfile();
      expect(res.success).toBe(true);
      expect(lastFetchCall.url).toContain("/api/auth/me");
    });

    it("exposes token getters and session checks", () => {
      expect(authService.isAuthenticated()).toBe(true);
      expect(authService.getAccessToken()).toBeTruthy();
      expect(authService.getRefreshToken()).toBeTruthy();
    });

    it("delegates login and stores tokens", async () => {
      const nowSec = Math.floor(Date.now() / 1000);
      const token = createFakeJwt({ exp: nowSec + 1000, sub: "2" });
      globalThis.fetch = vi.fn(async () => ({
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({
          access_token: token,
          refresh_token: token,
          token_type: "bearer",
        }),
      }));

      const res = await authService.login("testuser", "password123");
      expect(res.access_token).toBe(token);
      expect(authService.getAccessToken()).toBe(token);
    });

    it("delegates logout and clears tokens", () => {
      authService.logout();
      expect(authService.getAccessToken()).toBeNull();
      expect(authService.isAuthenticated()).toBe(false);
    });
  });

  describe("computerService", () => {
    it("getComputers calls /api/clients", async () => {
      await computerService.getComputers();
      expect(lastFetchCall.url).toContain("/api/clients");
      expect(lastFetchCall.options.method).toBeUndefined();
    });

    it("getComputer calls /api/clients/:id", async () => {
      await computerService.getComputer(42);
      expect(lastFetchCall.url).toContain("/api/clients/42");
    });

    it("getComputerMetrics handles limit as number or options object", async () => {
      await computerService.getComputerMetrics(1, 25);
      expect(lastFetchCall.url).toContain("/api/metrics/1?limit=25");

      const startDate = new Date("2026-01-01T00:00:00Z");
      await computerService.getComputerMetrics(1, {
        limit: 10,
        offset: 5,
        start_time: startDate,
      });
      expect(lastFetchCall.url).toContain("/api/metrics/1?");
      expect(lastFetchCall.url).toContain("limit=10");
      expect(lastFetchCall.url).toContain("offset=5");
      expect(lastFetchCall.url).toContain("start_time=2026-01-01T00%3A00%3A00.000Z");
    });

    it("getComputerUsage formats query parameters and dates", async () => {
      await computerService.getComputerUsage(3, { limit: 50 });
      expect(lastFetchCall.url).toContain("/api/clients/3/usage?limit=50");
    });
  });

  describe("softwareService", () => {
    it("getComputerSoftware calls /api/clients/:id/software", async () => {
      await softwareService.getComputerSoftware(7);
      expect(lastFetchCall.url).toContain("/api/clients/7/software");
    });
  });

  describe("processService", () => {
    it("getComputerProcesses calls /api/clients/:id/processes", async () => {
      await processService.getComputerProcesses(9);
      expect(lastFetchCall.url).toContain("/api/clients/9/processes");
    });
  });

  describe("commandService", () => {
    it("issueCommand calls POST /api/commands/:id with payload", async () => {
      const payload = { command_type: "restart", parameters: { force: true } };
      await commandService.issueCommand(12, payload);
      expect(lastFetchCall.url).toContain("/api/commands/12");
      expect(lastFetchCall.options.method).toBe("POST");
      expect(JSON.parse(lastFetchCall.options.body)).toEqual(payload);
    });

    it("getComputerCommands calls /api/commands/:id with pagination", async () => {
      await commandService.getComputerCommands(12, { limit: 10, offset: 20 });
      expect(lastFetchCall.url).toContain("/api/commands/12?limit=10&offset=20");
    });

    it("cancelCommand calls POST /api/commands/:id/cancel", async () => {
      await commandService.cancelCommand(99);
      expect(lastFetchCall.url).toContain("/api/commands/99/cancel");
      expect(lastFetchCall.options.method).toBe("POST");
    });

    it("getCommandDetails calls /api/commands/detail/:id", async () => {
      await commandService.getCommandDetails(55);
      expect(lastFetchCall.url).toContain("/api/commands/detail/55");
    });
  });

  describe("issueService", () => {
    it("getIssues handles filter query parameters", async () => {
      await issueService.getIssues({
        computer_id: 1,
        status: "Open",
        severity: "Critical",
        search: "kernel crash",
        limit: 10,
      });
      expect(lastFetchCall.url).toContain("/api/issues?");
      expect(lastFetchCall.url).toContain("computer_id=1");
      expect(lastFetchCall.url).toContain("status=open");
      expect(lastFetchCall.url).toContain("severity=critical");
      expect(lastFetchCall.url).toContain("search=kernel+crash");
      expect(lastFetchCall.url).toContain("limit=10");
    });

    it("getIssue calls /api/issues/:id", async () => {
      await issueService.getIssue(15);
      expect(lastFetchCall.url).toContain("/api/issues/15");
    });

    it("getIssueStats calls /api/issues/stats", async () => {
      await issueService.getIssueStats();
      expect(lastFetchCall.url).toContain("/api/issues/stats");

      await issueService.getIssueStats(4);
      expect(lastFetchCall.url).toContain("/api/issues/stats?computer_id=4");
    });

    it("createIssue sends POST /api/issues", async () => {
      const data = { title: "Bad display", computer_id: 2 };
      await issueService.createIssue(data);
      expect(lastFetchCall.url).toContain("/api/issues");
      expect(lastFetchCall.options.method).toBe("POST");
      expect(JSON.parse(lastFetchCall.options.body)).toEqual(data);
    });

    it("updateIssue sends PATCH /api/issues/:id", async () => {
      const data = { status: "in_progress" };
      await issueService.updateIssue(10, data);
      expect(lastFetchCall.url).toContain("/api/issues/10");
      expect(lastFetchCall.options.method).toBe("PATCH");
      expect(JSON.parse(lastFetchCall.options.body)).toEqual(data);
    });

    it("resolveIssue sends POST /api/issues/:id/resolve", async () => {
      await issueService.resolveIssue(10, "Replaced cable");
      expect(lastFetchCall.url).toContain("/api/issues/10/resolve");
      expect(lastFetchCall.options.method).toBe("POST");
      expect(JSON.parse(lastFetchCall.options.body)).toEqual({
        resolution_notes: "Replaced cable",
      });
    });

    it("deleteIssue sends DELETE /api/issues/:id", async () => {
      await issueService.deleteIssue(10);
      expect(lastFetchCall.url).toContain("/api/issues/10");
      expect(lastFetchCall.options.method).toBe("DELETE");
    });
  });

  describe("maintenanceService", () => {
    it("getMaintenanceRecords handles status and type mapping", async () => {
      await maintenanceService.getMaintenanceRecords({
        status: "In Progress",
        type: "Preventive",
        search: "checkup",
      });
      expect(lastFetchCall.url).toContain("/api/maintenance?");
      expect(lastFetchCall.url).toContain("status=in_progress");
      expect(lastFetchCall.url).toContain("type=preventive");
      expect(lastFetchCall.url).toContain("search=checkup");
    });

    it("createMaintenanceRecord sends POST /api/maintenance", async () => {
      const record = { title: "Oil fans", computer_id: 3 };
      await maintenanceService.createMaintenanceRecord(record);
      expect(lastFetchCall.url).toContain("/api/maintenance");
      expect(lastFetchCall.options.method).toBe("POST");
      expect(JSON.parse(lastFetchCall.options.body)).toEqual(record);
    });

    it("completeMaintenanceRecord sends POST /api/maintenance/:id/complete", async () => {
      await maintenanceService.completeMaintenanceRecord(8, { notes: "Done" });
      expect(lastFetchCall.url).toContain("/api/maintenance/8/complete");
      expect(lastFetchCall.options.method).toBe("POST");
    });

    it("deleteMaintenanceRecord sends DELETE /api/maintenance/:id", async () => {
      await maintenanceService.deleteMaintenanceRecord(8);
      expect(lastFetchCall.url).toContain("/api/maintenance/8");
      expect(lastFetchCall.options.method).toBe("DELETE");
    });
  });

  describe("notificationService", () => {
    it("getNotifications handles category and severity filters", async () => {
      await notificationService.getNotifications({
        category: "System",
        severity: "Critical",
        unread_only: true,
      });
      expect(lastFetchCall.url).toContain("/api/notifications?");
      expect(lastFetchCall.url).toContain("category=system");
      expect(lastFetchCall.url).toContain("severity=critical");
      expect(lastFetchCall.url).toContain("unread_only=true");
    });

    it("markNotificationRead sends PATCH /api/notifications/:id/read", async () => {
      await notificationService.markNotificationRead(77);
      expect(lastFetchCall.url).toContain("/api/notifications/77/read");
      expect(lastFetchCall.options.method).toBe("PATCH");
    });

    it("markAllNotificationsRead sends POST /api/notifications/read-all", async () => {
      await notificationService.markAllNotificationsRead();
      expect(lastFetchCall.url).toContain("/api/notifications/read-all");
      expect(lastFetchCall.options.method).toBe("POST");

      await notificationService.markAllNotificationsRead(5);
      expect(lastFetchCall.url).toContain("/api/notifications/read-all?computer_id=5");
    });

    it("clearReadNotifications sends DELETE /api/notifications/clear-read", async () => {
      await notificationService.clearReadNotifications();
      expect(lastFetchCall.url).toContain("/api/notifications/clear-read");
      expect(lastFetchCall.options.method).toBe("DELETE");
    });
  });

  describe("reportService", () => {
    it("getReportOverview calls /api/reports/overview", async () => {
      await reportService.getReportOverview();
      expect(lastFetchCall.url).toContain("/api/reports/overview");
    });

    it("getUtilizationReport formats filters", async () => {
      await reportService.getUtilizationReport({
        period: "weekly",
        from_date: "2026-01-01",
        to_date: "2026-01-07",
      });
      expect(lastFetchCall.url).toContain("/api/reports/utilization?");
      expect(lastFetchCall.url).toContain("period=weekly");
      expect(lastFetchCall.url).toContain("from_date=2026-01-01");
      expect(lastFetchCall.url).toContain("to_date=2026-01-07");
    });

    it("getSoftwareReport formats search and pagination", async () => {
      await reportService.getSoftwareReport({ search: "chrome", page: 2, limit: 20 });
      expect(lastFetchCall.url).toContain("/api/reports/software?");
      expect(lastFetchCall.url).toContain("search=chrome");
      expect(lastFetchCall.url).toContain("page=2");
      expect(lastFetchCall.url).toContain("limit=20");
    });

    it("getIssueReport formats filters", async () => {
      await reportService.getIssueReport({ severity: "high", status: "open" });
      expect(lastFetchCall.url).toContain("/api/reports/issues?");
      expect(lastFetchCall.url).toContain("severity=high");
      expect(lastFetchCall.url).toContain("status=open");
    });

    it("getMaintenanceReport formats filters", async () => {
      await reportService.getMaintenanceReport({ status: "completed" });
      expect(lastFetchCall.url).toContain("/api/reports/maintenance?");
      expect(lastFetchCall.url).toContain("status=completed");
    });

    it("getCommandReport formats filters", async () => {
      await reportService.getCommandReport({ command_type: "restart" });
      expect(lastFetchCall.url).toContain("/api/reports/commands?");
      expect(lastFetchCall.url).toContain("command_type=restart");
    });

    it("getAuditReport formats filters", async () => {
      await reportService.getAuditReport({ action: "LOGIN" });
      expect(lastFetchCall.url).toContain("/api/reports/audit?");
      expect(lastFetchCall.url).toContain("action=LOGIN");
    });
  });

  describe("userService", () => {
    it("getUsers formats search and filters", async () => {
      await userService.getUsers({ role: "admin", search: "alice" });
      expect(lastFetchCall.url).toContain("/api/users?");
      expect(lastFetchCall.url).toContain("role=admin");
      expect(lastFetchCall.url).toContain("search=alice");
    });

    it("createUser sends POST /api/users", async () => {
      const user = { username: "bob", email: "bob@lab.com" };
      await userService.createUser(user);
      expect(lastFetchCall.url).toContain("/api/users");
      expect(lastFetchCall.options.method).toBe("POST");
      expect(JSON.parse(lastFetchCall.options.body)).toEqual(user);
    });

    it("updateUser sends PATCH /api/users/:id", async () => {
      const update = { is_active: false };
      await userService.updateUser(12, update);
      expect(lastFetchCall.url).toContain("/api/users/12");
      expect(lastFetchCall.options.method).toBe("PATCH");
      expect(JSON.parse(lastFetchCall.options.body)).toEqual(update);
    });

    it("deleteUser sends DELETE /api/users/:id", async () => {
      await userService.deleteUser(12);
      expect(lastFetchCall.url).toContain("/api/users/12");
      expect(lastFetchCall.options.method).toBe("DELETE");
    });

    it("manages roles and permissions", async () => {
      await userService.getRoles();
      expect(lastFetchCall.url).toContain("/api/roles");

      await userService.createRole({ name: "Editor" });
      expect(lastFetchCall.url).toContain("/api/roles");
      expect(lastFetchCall.options.method).toBe("POST");

      await userService.updateRole(4, { description: "Updated" });
      expect(lastFetchCall.url).toContain("/api/roles/4");
      expect(lastFetchCall.options.method).toBe("PATCH");

      await userService.deleteRole(4);
      expect(lastFetchCall.url).toContain("/api/roles/4");
      expect(lastFetchCall.options.method).toBe("DELETE");

      await userService.getPermissions();
      expect(lastFetchCall.url).toContain("/api/permissions");

      await userService.updateRolePermissions(4, [1, 2, 3]);
      expect(lastFetchCall.url).toContain("/api/roles/4/permissions");
      expect(lastFetchCall.options.method).toBe("PUT");
      expect(JSON.parse(lastFetchCall.options.body)).toEqual({
        permissions: [1, 2, 3],
      });
    });
  });

  describe("auditService", () => {
    it("getAuditLogs formats filtering query parameters", async () => {
      await auditService.getAuditLogs({
        action: "UPDATE",
        target_type: "CLIENT",
        user_id: 5,
        limit: 25,
      });
      expect(lastFetchCall.url).toContain("/api/audit-logs?");
      expect(lastFetchCall.url).toContain("action=UPDATE");
      expect(lastFetchCall.url).toContain("target_type=CLIENT");
      expect(lastFetchCall.url).toContain("user_id=5");
      expect(lastFetchCall.url).toContain("limit=25");
    });

    it("getAuditLogDetails calls /api/audit-logs/:id", async () => {
      await auditService.getAuditLogDetails(100);
      expect(lastFetchCall.url).toContain("/api/audit-logs/100");
    });
  });

  describe("settingService", () => {
    it("getSettings calls /api/settings or /api/settings/:category", async () => {
      await settingService.getSettings();
      expect(lastFetchCall.url).toContain("/api/settings");

      await settingService.getSettings("security");
      expect(lastFetchCall.url).toContain("/api/settings/security");
    });

    it("updateSettings sends PATCH /api/settings", async () => {
      const patch = { session_timeout: 30 };
      await settingService.updateSettings(patch);
      expect(lastFetchCall.url).toContain("/api/settings");
      expect(lastFetchCall.options.method).toBe("PATCH");
      expect(JSON.parse(lastFetchCall.options.body)).toEqual(patch);
    });

    it("resetSettings sends POST /api/settings/reset", async () => {
      await settingService.resetSettings(["session_timeout"]);
      expect(lastFetchCall.url).toContain("/api/settings/reset");
      expect(lastFetchCall.options.method).toBe("POST");
      expect(JSON.parse(lastFetchCall.options.body)).toEqual({
        keys: ["session_timeout"],
      });
    });
  });
});
