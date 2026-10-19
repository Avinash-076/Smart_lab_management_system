import Icon from "../../../../components/ui/Icon";
import { SETTINGS_CATALOG } from "../../utils/settingUtils";
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
        </div>
      </div>
    </div>
  );
}

export default NotificationsPanel;
