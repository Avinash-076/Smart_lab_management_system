import Icon from "../../../../components/ui/Icon";
import { SETTINGS_CATALOG } from "../../utils/settingUtils";
import "./AgentPanel.css";

function AgentToggleSwitch({ id, checked, onChange, disabled, label }) {
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

function AgentPanel({ formData, fieldErrors, onChange, disabled }) {
  const bootMeta = SETTINGS_CATALOG.auto_start_agent;
  const procMeta = SETTINGS_CATALOG.collect_processes;
  const swMeta = SETTINGS_CATALOG.collect_software;
  const retMeta = SETTINGS_CATALOG.data_retention_days;

  const handleRetentionChange = (rawValue) => {
    if (rawValue === "") {
      onChange("data_retention_days", "");
      return;
    }
    const parsed = parseInt(rawValue, 10);
    onChange("data_retention_days", isNaN(parsed) ? rawValue : parsed);
  };

  return (
    <div className="settings-panel-card" data-testid="settings-agent-panel">
      <div className="settings-panel-header">
        <div className="settings-panel-icon-badge settings-panel-icon-badge--green">
          <Icon type="computer" size={20} />
        </div>
        <div className="settings-panel-title-group">
          <h3 className="settings-panel-title">Client Agent & Data Retention</h3>
          <p className="settings-panel-subtitle">
            Configure telemetry collectors, agent lifecycle parameters, and historical data retention policies.
          </p>
        </div>
      </div>

      <div className="settings-panel-body">
        {/* Agent Behavior Toggles */}
        <div className="settings-toggle-list" style={{ marginBottom: "22px" }}>
          {/* Auto Start */}
          <div className="settings-toggle-row">
            <div className="settings-toggle-info">
              <span className="settings-toggle-title">{bootMeta.label}</span>
              <p className="settings-toggle-desc">{bootMeta.description}</p>
            </div>
            <AgentToggleSwitch
              id="setting-auto-start"
              checked={formData.auto_start_agent}
              onChange={(val) => onChange("auto_start_agent", val)}
              disabled={disabled}
              label={bootMeta.label}
            />
          </div>

          {/* Process Collection */}
          <div className="settings-toggle-row">
            <div className="settings-toggle-info">
              <span className="settings-toggle-title">{procMeta.label}</span>
              <p className="settings-toggle-desc">{procMeta.description}</p>
            </div>
            <AgentToggleSwitch
              id="setting-collect-processes"
              checked={formData.collect_processes}
              onChange={(val) => onChange("collect_processes", val)}
              disabled={disabled}
              label={procMeta.label}
            />
          </div>

          {/* Software Scan */}
          <div className="settings-toggle-row">
            <div className="settings-toggle-info">
              <span className="settings-toggle-title">{swMeta.label}</span>
              <p className="settings-toggle-desc">{swMeta.description}</p>
            </div>
            <AgentToggleSwitch
              id="setting-collect-software"
              checked={formData.collect_software}
              onChange={(val) => onChange("collect_software", val)}
              disabled={disabled}
              label={swMeta.label}
            />
          </div>
        </div>

        {/* Data Retention Period */}
        <div className="agent-retention-section">
          <div className={`settings-field-group ${fieldErrors.data_retention_days ? "has-error" : ""}`}>
            <label htmlFor="setting-data-retention" className="settings-field-label">
              {retMeta.label} ({retMeta.unit})
            </label>
            <div className="settings-input-unit-wrapper" style={{ maxWidth: "340px" }}>
              <input
                id="setting-data-retention"
                type="number"
                min={retMeta.min}
                max={retMeta.max}
                className="settings-text-input settings-input-with-unit"
                value={formData.data_retention_days ?? ""}
                onChange={(e) => handleRetentionChange(e.target.value)}
                disabled={disabled}
              />
              <span className="settings-unit-tag">{retMeta.unit}</span>
            </div>
            {fieldErrors.data_retention_days ? (
              <span className="settings-field-error">{fieldErrors.data_retention_days}</span>
            ) : (
              <small className="settings-field-hint">{retMeta.description}</small>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default AgentPanel;
