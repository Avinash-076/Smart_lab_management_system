import { useState, useEffect } from "react";
import Icon from "../../../components/ui/Icon";
import { getSettings, updateSettings, resetSettings } from "../../../services/api";

// Reusable Toggle Component
function Toggle({ checked, onChange, disabled }) {
  return (
    <button
      type="button"
      className={`settings-toggle ${checked ? "active" : ""}`}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
      aria-label="Toggle setting"
    >
      <span />
    </button>
  );
}

/* =====================================================
   SETTINGS & CONFIGURATION MANAGEMENT COMPONENT
===================================================== */

function Settings() {
  // Form values matching backend catalog keys
  const [formData, setFormData] = useState({
    lab_name: "Computer Laboratory",
    lab_location: "Andhra Polytechnic",
    lab_network: "LAN / Ethernet",
    cpu_threshold: 85,
    ram_threshold: 85,
    disk_threshold: 90,
    heartbeat_interval: 30,
    disk_alerts: true,
    offline_alerts: true,
    issue_alerts: true,
    software_alerts: false,
    auto_start_agent: true,
    collect_processes: true,
    collect_software: true,
    data_retention_days: 30,
  });

  const [activeTab, setActiveTab] = useState("all");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    let active = true;
    async function initSettings() {
      try {
        const data = await getSettings();
        if (active && data && data.settings_map) {
          setFormData((prev) => ({
            ...prev,
            ...data.settings_map,
          }));
          if (data.items) {
            const latestItem = data.items.find((i) => i.updated_at);
            if (latestItem && latestItem.updated_at) {
              setLastUpdated(latestItem.updated_at);
            }
          }
          setLoading(false);
        }
      } catch (err) {
        if (active) {
          setError(err.message || "Failed to load system settings");
          setLoading(false);
        }
      }
    }

    initSettings();
    return () => {
      active = false;
    };
  }, []);

  // Update field in form state
  const handleFieldChange = (key, value) => {
    setFormData((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  // Save changes to backend
  const handleSave = async () => {
    setSaving(true);
    setError("");
    setMessage("");

    try {
      const res = await updateSettings(formData);
      if (res && res.settings_map) {
        setFormData((prev) => ({
          ...prev,
          ...res.settings_map,
        }));
      }
      setMessage("Configuration saved and applied successfully.");
      setLastUpdated(new Date().toISOString());
      setTimeout(() => {
        setMessage("");
      }, 4000);
    } catch (err) {
      setError(err.message || "Failed to save configuration settings");
    } finally {
      setSaving(false);
    }
  };

  // Reset to default settings
  const handleReset = async () => {
    if (!window.confirm("Are you sure you want to reset all settings to system defaults?")) {
      return;
    }

    setResetting(true);
    setError("");
    setMessage("");

    try {
      const res = await resetSettings();
      if (res && res.settings_map) {
        setFormData((prev) => ({
          ...prev,
          ...res.settings_map,
        }));
      }
      setMessage("All settings have been restored to system defaults.");
      setLastUpdated(new Date().toISOString());
      setTimeout(() => {
        setMessage("");
      }, 4000);
    } catch (err) {
      setError(err.message || "Failed to reset settings to defaults");
    } finally {
      setResetting(false);
    }
  };

  return (
    <div className="content">
      {/* PAGE HEADER */}
      <div className="page-top">
        <div>
          <h2>System Settings & Configuration</h2>
          <p>
            Configure laboratory metadata, telemetry thresholds, notification alerts, and client agent parameters.
          </p>
        </div>

        <div className="settings-actions">
          <button
            className="settings-reset"
            onClick={handleReset}
            disabled={saving || resetting || loading}
          >
            <Icon type="refresh" size={16} />
            {resetting ? "Resetting..." : "Reset Defaults"}
          </button>

          <button
            className="settings-save"
            onClick={handleSave}
            disabled={saving || resetting || loading}
          >
            <Icon type="check" size={16} />
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>

      {/* FEEDBACK TOASTS / ALERTS */}
      {message && (
        <div className="settings-success" style={{ marginBottom: "20px" }}>
          <Icon type="check" size={17} />
          {message}
        </div>
      )}

      {error && (
        <div className="settings-error" style={{
          backgroundColor: "rgba(239, 68, 68, 0.1)",
          border: "1px solid rgba(239, 68, 68, 0.3)",
          color: "#ef4444",
          padding: "12px 16px",
          borderRadius: "8px",
          marginBottom: "20px",
          display: "flex",
          alignItems: "center",
          gap: "10px"
        }}>
          <Icon type="issue" size={18} />
          <span>{error}</span>
        </div>
      )}

      {/* CATEGORY FILTER TABS */}
      <div className="nav-tabs" style={{ marginBottom: "20px" }}>
        <button
          className={`nav-tab ${activeTab === "all" ? "active" : ""}`}
          onClick={() => setActiveTab("all")}
        >
          All Settings
        </button>
        <button
          className={`nav-tab ${activeTab === "general" ? "active" : ""}`}
          onClick={() => setActiveTab("general")}
        >
          Laboratory Info
        </button>
        <button
          className={`nav-tab ${activeTab === "monitoring" ? "active" : ""}`}
          onClick={() => setActiveTab("monitoring")}
        >
          Monitoring & Telemetry
        </button>
        <button
          className={`nav-tab ${activeTab === "notifications" ? "active" : ""}`}
          onClick={() => setActiveTab("notifications")}
        >
          Notifications & Alerts
        </button>
        <button
          className={`nav-tab ${activeTab === "agent" ? "active" : ""}`}
          onClick={() => setActiveTab("agent")}
        >
          Client Agent
        </button>
      </div>

      {loading ? (
        <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
          <Icon type="refresh" size={24} className="spin" />
          <p style={{ marginTop: "10px" }}>Loading application configuration...</p>
        </div>
      ) : (
        <>
          {/* PANEL 1: LABORATORY CONFIGURATION */}
          {(activeTab === "all" || activeTab === "general") && (
            <div className="settings-panel">
              <div className="settings-panel-header">
                <div className="settings-section-icon blue">
                  <Icon type="computer" size={20} />
                </div>
                <div>
                  <h3>Laboratory Configuration</h3>
                  <p>Configure facility identity, location coordinates, and network topology.</p>
                </div>
              </div>

              <div className="settings-form-grid">
                <div className="settings-field">
                  <label>Laboratory Name</label>
                  <input
                    type="text"
                    value={formData.lab_name}
                    onChange={(e) => handleFieldChange("lab_name", e.target.value)}
                    placeholder="e.g. Computer Laboratory"
                  />
                  <small>Facility display name shown across all client workstations.</small>
                </div>

                <div className="settings-field">
                  <label>Laboratory Location</label>
                  <input
                    type="text"
                    value={formData.lab_location}
                    onChange={(e) => handleFieldChange("lab_location", e.target.value)}
                    placeholder="e.g. Andhra Polytechnic, Block C"
                  />
                  <small>Physical campus, building, or room number identifier.</small>
                </div>

                <div className="settings-field">
                  <label>Network Type</label>
                  <select
                    value={formData.lab_network}
                    onChange={(e) => handleFieldChange("lab_network", e.target.value)}
                  >
                    <option value="LAN / Ethernet">LAN / Ethernet</option>
                    <option value="Wi-Fi">Wi-Fi</option>
                    <option value="Hybrid (LAN + Wi-Fi)">Hybrid (LAN + Wi-Fi)</option>
                    <option value="VLAN Isolated">VLAN Isolated</option>
                  </select>
                  <small>Primary network interface topology for agent telemetry.</small>
                </div>
              </div>
            </div>
          )}

          {/* PANEL 2: MONITORING THRESHOLDS */}
          {(activeTab === "all" || activeTab === "monitoring") && (
            <div className="settings-panel">
              <div className="settings-panel-header">
                <div className="settings-section-icon orange">
                  <Icon type="issue" size={20} />
                </div>
                <div>
                  <h3>Monitoring & Alert Thresholds</h3>
                  <p>Define resource warning limits and expected client reporting intervals.</p>
                </div>
              </div>

              <div className="settings-form-grid">
                <div className="settings-field">
                  <label>CPU Alert Threshold (%)</label>
                  <input
                    type="number"
                    min="10"
                    max="100"
                    value={formData.cpu_threshold}
                    onChange={(e) => handleFieldChange("cpu_threshold", parseInt(e.target.value, 10) || 0)}
                  />
                  <small>Trigger high CPU warning when node usage exceeds this percentage (10–100%).</small>
                </div>

                <div className="settings-field">
                  <label>RAM Alert Threshold (%)</label>
                  <input
                    type="number"
                    min="10"
                    max="100"
                    value={formData.ram_threshold}
                    onChange={(e) => handleFieldChange("ram_threshold", parseInt(e.target.value, 10) || 0)}
                  />
                  <small>Trigger memory warning when node RAM usage exceeds this percentage (10–100%).</small>
                </div>

                <div className="settings-field">
                  <label>Disk Alert Threshold (%)</label>
                  <input
                    type="number"
                    min="10"
                    max="100"
                    value={formData.disk_threshold}
                    onChange={(e) => handleFieldChange("disk_threshold", parseInt(e.target.value, 10) || 0)}
                  />
                  <small>Trigger storage warning when node disk usage exceeds this percentage (10–100%).</small>
                </div>

                <div className="settings-field">
                  <label>Agent Heartbeat Interval (seconds)</label>
                  <input
                    type="number"
                    min="5"
                    max="300"
                    value={formData.heartbeat_interval}
                    onChange={(e) => handleFieldChange("heartbeat_interval", parseInt(e.target.value, 10) || 0)}
                  />
                  <small>Frequency at which client agents report status and telemetry (5–300s).</small>
                </div>
              </div>
            </div>
          )}

          {/* PANEL 3: NOTIFICATIONS */}
          {(activeTab === "all" || activeTab === "notifications") && (
            <div className="settings-panel">
              <div className="settings-panel-header">
                <div className="settings-section-icon purple">
                  <Icon type="notification" size={20} />
                </div>
                <div>
                  <h3>Notifications & Alert Subscriptions</h3>
                  <p>Choose which system events automatically trigger in-app alert banners.</p>
                </div>
              </div>

              <div className="settings-options">
                <div className="settings-option">
                  <div>
                    <strong>Low Disk Space Alerts</strong>
                    <p>Generate notification when a computer exceeds the configured disk threshold.</p>
                  </div>
                  <Toggle
                    checked={Boolean(formData.disk_alerts)}
                    onChange={(val) => handleFieldChange("disk_alerts", val)}
                  />
                </div>

                <div className="settings-option">
                  <div>
                    <strong>Computer Offline Alerts</strong>
                    <p>Generate notification when a computer stops communicating beyond heartbeat window.</p>
                  </div>
                  <Toggle
                    checked={Boolean(formData.offline_alerts)}
                    onChange={(val) => handleFieldChange("offline_alerts", val)}
                  />
                </div>

                <div className="settings-option">
                  <div>
                    <strong>Issue Tracking Notifications</strong>
                    <p>Generate notification when a student or technician logs a new computer issue.</p>
                  </div>
                  <Toggle
                    checked={Boolean(formData.issue_alerts)}
                    onChange={(val) => handleFieldChange("issue_alerts", val)}
                  />
                </div>

                <div className="settings-option">
                  <div>
                    <strong>Software Change Alerts</strong>
                    <p>Generate notification when newly installed or unauthorized software is detected.</p>
                  </div>
                  <Toggle
                    checked={Boolean(formData.software_alerts)}
                    onChange={(val) => handleFieldChange("software_alerts", val)}
                  />
                </div>
              </div>
            </div>
          )}

          {/* PANEL 4: CLIENT AGENT & DATA RETENTION */}
          {(activeTab === "all" || activeTab === "agent") && (
            <div className="settings-panel">
              <div className="settings-panel-header">
                <div className="settings-section-icon green">
                  <Icon type="computer" size={20} />
                </div>
                <div>
                  <h3>Client Agent & Data Retention</h3>
                  <p>Configure telemetry collectors and historical metric retention policies.</p>
                </div>
              </div>

              <div className="settings-options" style={{ marginBottom: "20px" }}>
                <div className="settings-option">
                  <div>
                    <strong>Start Agent on System Boot</strong>
                    <p>Configure client agent background service to launch automatically on workstation startup.</p>
                  </div>
                  <Toggle
                    checked={Boolean(formData.auto_start_agent)}
                    onChange={(val) => handleFieldChange("auto_start_agent", val)}
                  />
                </div>

                <div className="settings-option">
                  <div>
                    <strong>Collect Running Processes</strong>
                    <p>Collect running process list and per-process memory consumption for forensic inspection.</p>
                  </div>
                  <Toggle
                    checked={Boolean(formData.collect_processes)}
                    onChange={(val) => handleFieldChange("collect_processes", val)}
                  />
                </div>

                <div className="settings-option">
                  <div>
                    <strong>Collect Software Inventory</strong>
                    <p>Periodically scan and sync installed software versions from client workstations.</p>
                  </div>
                  <Toggle
                    checked={Boolean(formData.collect_software)}
                    onChange={(val) => handleFieldChange("collect_software", val)}
                  />
                </div>
              </div>

              <div className="settings-form-grid" style={{ borderTop: "1px solid var(--border-color)", paddingTop: "16px" }}>
                <div className="settings-field">
                  <label>Data Retention Period (Days)</label>
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={formData.data_retention_days}
                    onChange={(e) => handleFieldChange("data_retention_days", parseInt(e.target.value, 10) || 0)}
                  />
                  <small>Duration to retain historical telemetry samples before automated pruning (1–365 days).</small>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* FOOTER INFO */}
      {lastUpdated && (
        <div style={{ marginTop: "16px", fontSize: "12px", color: "var(--text-muted)", textAlign: "right" }}>
          Last modified: {new Date(lastUpdated).toLocaleString()}
        </div>
      )}
    </div>
  );
}

export default Settings;