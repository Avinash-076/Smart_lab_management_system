/**
 * Settings Utilities & Validation Constants
 * Matches backend SETTINGS_CATALOG definition.
 */

export const SETTINGS_CATALOG = {
  lab_name: {
    category: "general",
    type: "string",
    default: "Computer Laboratory",
    minLen: 1,
    maxLen: 100,
    label: "Laboratory Name",
    description: "Facility display name shown across all client workstations.",
  },
  lab_location: {
    category: "general",
    type: "string",
    default: "Andhra Polytechnic",
    minLen: 0,
    maxLen: 150,
    label: "Laboratory Location",
    description: "Physical campus, building, or room number identifier.",
  },
  lab_network: {
    category: "general",
    type: "string",
    default: "LAN / Ethernet",
    minLen: 0,
    maxLen: 100,
    label: "Network Type",
    description: "Primary network interface topology for agent telemetry.",
    options: [
      "LAN / Ethernet",
      "Wi-Fi",
      "Hybrid (LAN + Wi-Fi)",
      "VLAN Isolated",
    ],
  },
  cpu_threshold: {
    category: "monitoring",
    type: "int",
    default: 85,
    min: 10,
    max: 100,
    unit: "%",
    label: "CPU Alert Threshold",
    description: "Trigger high CPU warning when node usage exceeds this percentage (10–100%).",
  },
  ram_threshold: {
    category: "monitoring",
    type: "int",
    default: 85,
    min: 10,
    max: 100,
    unit: "%",
    label: "RAM Alert Threshold",
    description: "Trigger memory warning when node RAM usage exceeds this percentage (10–100%).",
  },
  disk_threshold: {
    category: "monitoring",
    type: "int",
    default: 90,
    min: 10,
    max: 100,
    unit: "%",
    label: "Disk Alert Threshold",
    description: "Trigger storage warning when node disk usage exceeds this percentage (10–100%).",
  },
  heartbeat_interval: {
    category: "monitoring",
    type: "int",
    default: 30,
    min: 5,
    max: 300,
    unit: "s",
    label: "Agent Heartbeat Interval",
    description: "Frequency at which client agents report status and telemetry (5–300s).",
  },
  disk_alerts: {
    category: "notifications",
    type: "bool",
    default: true,
    label: "Low Disk Space Alerts",
    description: "Generate in-app notification when a computer exceeds the configured disk threshold.",
  },
  offline_alerts: {
    category: "notifications",
    type: "bool",
    default: true,
    label: "Computer Offline Alerts",
    description: "Generate in-app notification when a computer stops communicating beyond heartbeat window.",
  },
  issue_alerts: {
    category: "notifications",
    type: "bool",
    default: true,
    label: "Issue Tracking Notifications",
    description: "Generate in-app notification when a student or technician logs a new computer issue.",
  },
  software_alerts: {
    category: "notifications",
    type: "bool",
    default: false,
    label: "Software Change Alerts",
    description: "Generate in-app notification when newly installed or unauthorized software is detected.",
  },
  auto_start_agent: {
    category: "agent",
    type: "bool",
    default: true,
    label: "Start Agent on System Boot",
    description: "Configure client agent background service to launch automatically on workstation startup.",
  },
  collect_processes: {
    category: "agent",
    type: "bool",
    default: true,
    label: "Collect Running Processes",
    description: "Collect running process list and per-process memory consumption for forensic inspection.",
  },
  collect_software: {
    category: "agent",
    type: "bool",
    default: true,
    label: "Collect Software Inventory",
    description: "Periodically scan and sync installed software versions from client workstations.",
  },
  data_retention_days: {
    category: "agent",
    type: "int",
    default: 30,
    min: 1,
    max: 365,
    unit: "days",
    label: "Data Retention Period",
    description: "Duration to retain historical telemetry samples before automated pruning (1–365 days).",
  },
};

export const SETTING_CATEGORIES = [
  { id: "all", label: "All Settings", icon: "settings" },
  { id: "general", label: "Laboratory Info", icon: "computer" },
  { id: "monitoring", label: "Monitoring & Telemetry", icon: "issue" },
  { id: "notifications", label: "Notifications & Alerts", icon: "notification" },
  { id: "agent", label: "Client Agent", icon: "refresh" },
];

export const DEFAULT_SETTINGS = Object.fromEntries(
  Object.entries(SETTINGS_CATALOG).map(([key, meta]) => [key, meta.default])
);

/**
 * Validate all fields in form data.
 * Returns an object mapping field name to error message (if invalid).
 */
export function validateSettings(formData) {
  const errors = {};

  if (!formData) return errors;

  for (const [key, meta] of Object.entries(SETTINGS_CATALOG)) {
    const val = formData[key];

    if (meta.type === "string") {
      const s = String(val ?? "").trim();
      if (meta.minLen !== undefined && s.length < meta.minLen) {
        errors[key] = `${meta.label} must be at least ${meta.minLen} character${meta.minLen > 1 ? "s" : ""}.`;
      } else if (meta.maxLen !== undefined && s.length > meta.maxLen) {
        errors[key] = `${meta.label} cannot exceed ${meta.maxLen} characters.`;
      }
    } else if (meta.type === "int") {
      const num = Number(val);
      if (isNaN(num) || !Number.isInteger(num)) {
        errors[key] = `${meta.label} must be an integer.`;
      } else if (meta.min !== undefined && num < meta.min) {
        errors[key] = `${meta.label} must be at least ${meta.min}${meta.unit ? ` ${meta.unit}` : ""}.`;
      } else if (meta.max !== undefined && num > meta.max) {
        errors[key] = `${meta.label} cannot exceed ${meta.max}${meta.unit ? ` ${meta.unit}` : ""}.`;
      }
    }
  }

  return errors;
}

/**
 * Compare current formData with persistedData to detect if any field changed.
 */
export function isFormDataDirty(formData, persistedData) {
  if (!formData || !persistedData) return false;
  return Object.keys(SETTINGS_CATALOG).some(
    (key) => formData[key] !== persistedData[key]
  );
}

/**
 * Check if a specific category has any unsaved/dirty fields.
 */
export function hasCategoryDirty(category, formData, persistedData) {
  if (!formData || !persistedData) return false;
  return Object.entries(SETTINGS_CATALOG).some(
    ([key, meta]) => meta.category === category && formData[key] !== persistedData[key]
  );
}

