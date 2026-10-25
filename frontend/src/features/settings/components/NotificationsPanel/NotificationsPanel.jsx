import { useState } from "react";
import Icon from "../../../../components/ui/Icon";
import { SETTINGS_CATALOG } from "../../utils/settingUtils";
import { initNotificationPermissions, sendNativeNotification } from "../../../../services/nativeNotification";
import "./NotificationsPanel.css";

function ToggleSwitch({ id, checked, onChange, disabled, label }) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={Boolean(checked)}
      aria-label={label}
      className={`settings-toggle-switch ${checked ? "is-active" : ""}`}
      onClick={() => !disabled && onChange(!checked)}
      disabled={disabled}
    >
      <span className="settings-toggle-slider" />
    </button>
  );
}

function NotificationsPanel({ formData, onChange, disabled }) {
  const [testSent, setTestSent] = useState(false);
  const diskMeta = SETTINGS_CATALOG.disk_alerts;
  const offMeta = SETTINGS_CATALOG.offline_alerts;
  const issueMeta = SETTINGS_CATALOG.issue_alerts;
  const swMeta = SETTINGS_CATALOG.software_alerts;

  return (
    <div className="settings-panel-card" data-testid="settings-notifications-panel">
      <div className="settings-panel-header">
        <div className="settings-panel-icon-badge settings-panel-icon-badge--purple">
          <Icon type="notification" size={20} />
        </div>
        <div className="settings-panel-title-group">
          <h3 className="settings-panel-title">Notifications & Alert Subscriptions</h3>
          <p className="settings-panel-subtitle">
            Choose which system events automatically trigger in-app notification banners.
          </p>
        </div>
      </div>

      <div className="settings-panel-body">
        <div className="settings-toggle-list">
          {/* Low Disk Alert */}
          <div className="settings-toggle-row">
            <div className="settings-toggle-info">
              <span className="settings-toggle-title">{diskMeta.label}</span>
              <p className="settings-toggle-desc">{diskMeta.description}</p>
            </div>
            <ToggleSwitch
              id="setting-disk-alerts"
              checked={formData.disk_alerts}
              onChange={(val) => onChange("disk_alerts", val)}
              disabled={disabled}
              label={diskMeta.label}
            />
          </div>

          {/* Computer Offline Alert */}
          <div className="settings-toggle-row">
            <div className="settings-toggle-info">
              <span className="settings-toggle-title">{offMeta.label}</span>
              <p className="settings-toggle-desc">{offMeta.description}</p>
            </div>
            <ToggleSwitch
              id="setting-offline-alerts"
              checked={formData.offline_alerts}
              onChange={(val) => onChange("offline_alerts", val)}
              disabled={disabled}
              label={offMeta.label}
            />
          </div>

          {/* Issue Tracking Alert */}
          <div className="settings-toggle-row">
            <div className="settings-toggle-info">
              <span className="settings-toggle-title">{issueMeta.label}</span>
              <p className="settings-toggle-desc">{issueMeta.description}</p>
            </div>
            <ToggleSwitch
              id="setting-issue-alerts"
              checked={formData.issue_alerts}
              onChange={(val) => onChange("issue_alerts", val)}
              disabled={disabled}
              label={issueMeta.label}
            />
          </div>

          {/* Software Change Alert */}
          <div className="settings-toggle-row">
            <div className="settings-toggle-info">
              <span className="settings-toggle-title">{swMeta.label}</span>
              <p className="settings-toggle-desc">{swMeta.description}</p>
            </div>
            <ToggleSwitch
              id="setting-software-alerts"
              checked={formData.software_alerts}
              onChange={(val) => onChange("software_alerts", val)}
              disabled={disabled}
              label={swMeta.label}
            />
          </div>

          {/* Test Windows Toast Notification */}
          <div className="settings-toggle-row" style={{ marginTop: "1rem", paddingTop: "1.25rem", borderTop: "1px solid rgba(255, 255, 255, 0.08)" }}>
            <div className="settings-toggle-info">
              <span className="settings-toggle-title">Windows Action Center Toast Testing</span>
              <p className="settings-toggle-desc">
                Trigger a sample high-priority alert to test native Windows 10/11 notifications.
              </p>
            </div>
            <button
              type="button"
              className="btn btn--secondary"
              id="btn-test-windows-notification"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.5rem 1rem",
                fontSize: "0.85rem",
                fontWeight: 600,
                borderRadius: "6px",
                cursor: "pointer",
                background: testSent ? "#10b981" : "var(--primary-color, #3b82f6)",
                color: "#fff",
                border: "none",
                transition: "all 0.2s ease"
              }}
              onClick={async () => {
                await initNotificationPermissions();
                await sendNativeNotification({
                  title: "🚨 SLMS Critical Alert - LAB-PC-04",
                  body: "Workstation LAB-PC-04 has reached 94% RAM usage (15.1 GB / 16 GB).",
                  severity: "critical",
                  computer: "LAB-PC-04",
                });
                setTestSent(true);
                setTimeout(() => setTestSent(false), 4000);
              }}
            >
              <Icon type="notification" size={16} />
              {testSent ? "Toast Dispatched!" : "Send Test Toast"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default NotificationsPanel;
