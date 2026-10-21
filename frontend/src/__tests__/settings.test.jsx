import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderToString } from "react-dom/server";

import SettingsHeader from "../features/settings/components/SettingsHeader/SettingsHeader";
import SettingsTabs from "../features/settings/components/SettingsTabs/SettingsTabs";
import LaboratoryPanel from "../features/settings/components/LaboratoryPanel/LaboratoryPanel";
import MonitoringPanel from "../features/settings/components/MonitoringPanel/MonitoringPanel";
import NotificationsPanel from "../features/settings/components/NotificationsPanel/NotificationsPanel";
import AgentPanel from "../features/settings/components/AgentPanel/AgentPanel";
import ResetConfirmModal from "../features/settings/components/ResetConfirmModal/ResetConfirmModal";
import Settings from "../features/settings/pages/Settings";

import {
  SETTING_CATEGORIES,
  DEFAULT_SETTINGS,
  validateSettings,
  isFormDataDirty,
  hasCategoryDirty,
} from "../features/settings/utils/settingUtils";

import {
  getSettings,
  updateSettings,
  resetSettings,
  getAgentConfig,
} from "../services/settingService";
import { setTokens, clearTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("Settings Module - Catalog & Validation Utilities", () => {
  it("exports valid setting categories and complete defaults", () => {
    expect(SETTING_CATEGORIES.length).toBe(6);
    expect(SETTING_CATEGORIES.map((c) => c.id)).toEqual([
      "all",
      "general",
      "monitoring",
      "notifications",
      "agent",
      "security",
    ]);

    expect(DEFAULT_SETTINGS.lab_name).toBe("Computer Laboratory");
    expect(DEFAULT_SETTINGS.cpu_threshold).toBe(85);
    expect(DEFAULT_SETTINGS.ram_threshold).toBe(85);
    expect(DEFAULT_SETTINGS.disk_threshold).toBe(90);
    expect(DEFAULT_SETTINGS.heartbeat_interval).toBe(30);
    expect(DEFAULT_SETTINGS.disk_alerts).toBe(true);
    expect(DEFAULT_SETTINGS.offline_alerts).toBe(true);
    expect(DEFAULT_SETTINGS.issue_alerts).toBe(true);
    expect(DEFAULT_SETTINGS.software_alerts).toBe(false);
    expect(DEFAULT_SETTINGS.auto_start_agent).toBe(true);
    expect(DEFAULT_SETTINGS.collect_processes).toBe(true);
    expect(DEFAULT_SETTINGS.collect_software).toBe(true);
    expect(DEFAULT_SETTINGS.data_retention_days).toBe(30);
  });

  it("validates empty lab name as an error", () => {
    const invalid = { ...DEFAULT_SETTINGS, lab_name: "   " };
    const errors = validateSettings(invalid);
    expect(errors.lab_name).toBeDefined();
    expect(errors.lab_name).toContain("must be at least 1 character");
  });

  it("validates out-of-range thresholds", () => {
    const invalidCpu = { ...DEFAULT_SETTINGS, cpu_threshold: 150 };
    expect(validateSettings(invalidCpu).cpu_threshold).toContain("cannot exceed 100 %");

    const invalidRam = { ...DEFAULT_SETTINGS, ram_threshold: 5 };
    expect(validateSettings(invalidRam).ram_threshold).toContain("must be at least 10 %");

    const invalidDisk = { ...DEFAULT_SETTINGS, disk_threshold: "not_a_number" };
    expect(validateSettings(invalidDisk).disk_threshold).toBeDefined();

    const invalidHeartbeat = { ...DEFAULT_SETTINGS, heartbeat_interval: 2 };
    expect(validateSettings(invalidHeartbeat).heartbeat_interval).toContain("must be at least 5 s");

    const invalidRetention = { ...DEFAULT_SETTINGS, data_retention_days: 0 };
    expect(validateSettings(invalidRetention).data_retention_days).toContain("must be at least 1 days");
  });

  it("passes validation with canonical default settings", () => {
    const errors = validateSettings(DEFAULT_SETTINGS);
    expect(Object.keys(errors).length).toBe(0);
  });

  it("detects dirty form states and category modifications correctly", () => {
    const initial = { ...DEFAULT_SETTINGS };
    const modified = { ...DEFAULT_SETTINGS, lab_name: "New Lab", cpu_threshold: 70 };

    expect(isFormDataDirty(initial, initial)).toBe(false);
    expect(isFormDataDirty(modified, initial)).toBe(true);

    expect(hasCategoryDirty("general", modified, initial)).toBe(true);
    expect(hasCategoryDirty("monitoring", modified, initial)).toBe(true);
    expect(hasCategoryDirty("notifications", modified, initial)).toBe(false);
    expect(hasCategoryDirty("agent", modified, initial)).toBe(false);
  });
});

describe("Settings Module - Component Rendering", () => {
  it("renders SettingsHeader in clean state", () => {
    const html = renderToString(
      <SettingsHeader
        isDirty={false}
        canManageSettings={true}
        saving={false}
        resetting={false}
        loading={false}
        lastUpdated="2026-10-19T20:00:00Z"
        onSave={() => {}}
        onOpenResetModal={() => {}}
        onDiscard={() => {}}
        message=""
        onDismissMessage={() => {}}
        error=""
        onDismissError={() => {}}
        hasValidationErrors={false}
      />
    );

    expect(html).toContain("All Settings Saved");
    expect(html).toContain("Save Changes");
    expect(html).toContain("Reset Defaults");
  });

  it("renders SettingsHeader with dirty state and alert banners", () => {
    const html = renderToString(
      <SettingsHeader
        isDirty={true}
        canManageSettings={true}
        saving={false}
        resetting={false}
        loading={false}
        lastUpdated={null}
        onSave={() => {}}
        onOpenResetModal={() => {}}
        onDiscard={() => {}}
        message="Settings updated successfully."
        onDismissMessage={() => {}}
        error="Invalid configuration values."
        onDismissError={() => {}}
        hasValidationErrors={true}
      />
    );

    expect(html).toContain("Unsaved Changes");
    expect(html).toContain("Discard");
    expect(html).toContain("Settings updated successfully.");
    expect(html).toContain("Invalid configuration values.");
  });

  it("renders SettingsHeader in read-only mode for non-admin users", () => {
    const html = renderToString(
      <SettingsHeader
        isDirty={false}
        canManageSettings={false}
        saving={false}
        resetting={false}
        loading={false}
        lastUpdated={null}
        onSave={() => {}}
        onOpenResetModal={() => {}}
        onDiscard={() => {}}
        message=""
        onDismissMessage={() => {}}
        error=""
        onDismissError={() => {}}
        hasValidationErrors={false}
      />
    );

    expect(html).toContain("Read-Only Mode");
  });

  it("renders SettingsTabs with category buttons and dirty indicators", () => {
    const dirtyCounts = { all: 2, general: 1, monitoring: 1, notifications: 0, agent: 0 };
    const html = renderToString(
      <SettingsTabs
        activeTab="monitoring"
        onSelectTab={() => {}}
        categoryDirtyCounts={dirtyCounts}
      />
    );

    expect(html).toContain("All Settings");
    expect(html).toContain("Laboratory Info");
    expect(html).toContain("Monitoring &amp; Telemetry");
    expect(html).toContain("Notifications &amp; Alerts");
    expect(html).toContain("Client Agent");
    // Tab badges for modified categories
    expect(html).toContain("settings-tab-dirty-badge");
  });

  it("renders LaboratoryPanel with current values and error hints", () => {
    const fieldErrors = { lab_name: "Facility name cannot be empty" };
    const html = renderToString(
      <LaboratoryPanel
        formData={{ ...DEFAULT_SETTINGS, lab_name: "" }}
        fieldErrors={fieldErrors}
        onChange={() => {}}
        disabled={false}
      />
    );

    expect(html).toContain("Laboratory Configuration");
    expect(html).toContain("Facility name cannot be empty");
    expect(html).toContain("LAN / Ethernet");
  });

  it("renders MonitoringPanel with thresholds and unit badges", () => {
    const html = renderToString(
      <MonitoringPanel
        formData={DEFAULT_SETTINGS}
        fieldErrors={{}}
        onChange={() => {}}
        disabled={false}
      />
    );

    expect(html).toContain("Monitoring &amp; Alert Thresholds");
    expect(html).toContain("CPU Alert Threshold");
    expect(html).toContain("RAM Alert Threshold");
    expect(html).toContain("Disk Alert Threshold");
    expect(html).toContain("Agent Heartbeat Interval");
    expect(html).toContain("%");
    expect(html).toContain("s");
  });

  it("renders NotificationsPanel with toggle switches", () => {
    const html = renderToString(
      <NotificationsPanel
        formData={DEFAULT_SETTINGS}
        onChange={() => {}}
        disabled={false}
      />
    );

    expect(html).toContain("Notifications &amp; Alert Subscriptions");
    expect(html).toContain("Low Disk Space Alerts");
    expect(html).toContain("Computer Offline Alerts");
    expect(html).toContain("Issue Tracking Notifications");
    expect(html).toContain("Software Change Alerts");
    expect(html).toContain("settings-toggle-switch");
  });

  it("renders AgentPanel with client configuration options", () => {
    const html = renderToString(
      <AgentPanel
        formData={DEFAULT_SETTINGS}
        fieldErrors={{}}
        onChange={() => {}}
        disabled={false}
      />
    );

    expect(html).toContain("Client Agent &amp; Data Retention");
    expect(html).toContain("Start Agent on System Boot");
    expect(html).toContain("Collect Running Processes");
    expect(html).toContain("Collect Software Inventory");
    expect(html).toContain("Data Retention Period");
    expect(html).toContain("days");
  });

  it("renders ResetConfirmModal with confirmation options", () => {
    const html = renderToString(
      <ResetConfirmModal
        isOpen={true}
        onClose={() => {}}
        onConfirmReset={() => {}}
        activeTab="monitoring"
        resetting={false}
      />
    );

    expect(html).toContain("Reset Settings to Factory Defaults");
    expect(html).toContain("Choose Reset Scope:");
    expect(html).toContain("Monitoring &amp; Telemetry");
    expect(html).toContain("All System Settings");
    expect(html).toContain("Restore Defaults");
  });

  it("renders Settings page with full structure", () => {
    const html = renderToString(<Settings />);
    expect(html).toContain("settings-page-wrapper");
    expect(html).toContain("settings-toolbar");
    expect(html).toContain("settings-tabs-container");
    expect(html).toContain("Loading application configuration...");
  });
});

describe("Settings Module - Service API Integration", () => {
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
        json: async () => ({
          success: true,
          url: String(url),
          items: [],
          categories: ["general", "monitoring"],
          settings_map: { lab_name: "Test Lab", cpu_threshold: 80 },
          heartbeat_interval: 30,
        }),
      };
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    clearTokens();
  });

  it("calls getSettings with appropriate endpoint", async () => {
    const res = await getSettings();
    expect(lastFetchCall).not.toBeNull();
    expect(lastFetchCall.url).toContain("/api/settings");
    expect(res.settings_map.lab_name).toBe("Test Lab");
  });

  it("calls updateSettings via PATCH with JSON body", async () => {
    const res = await updateSettings({ cpu_threshold: 80 });
    expect(lastFetchCall).not.toBeNull();
    expect(lastFetchCall.url).toContain("/api/settings");
    expect(lastFetchCall.options.method).toBe("PATCH");
    expect(lastFetchCall.options.body).toBe(JSON.stringify({ cpu_threshold: 80 }));
    expect(res.settings_map.cpu_threshold).toBe(80);
  });

  it("calls resetSettings via POST with target keys", async () => {
    await resetSettings(["lab_name"]);
    expect(lastFetchCall).not.toBeNull();
    expect(lastFetchCall.url).toContain("/api/settings/reset");
    expect(lastFetchCall.options.method).toBe("POST");
    expect(lastFetchCall.options.body).toBe(JSON.stringify({ keys: ["lab_name"] }));
  });

  it("calls getAgentConfig endpoint", async () => {
    const config = await getAgentConfig();
    expect(lastFetchCall).not.toBeNull();
    expect(lastFetchCall.url).toContain("/api/settings/agent-config");
    expect(config.heartbeat_interval).toBe(30);
  });
});
