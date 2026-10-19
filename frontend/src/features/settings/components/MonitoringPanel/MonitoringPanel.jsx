import Icon from "../../../../components/ui/Icon";
import { SETTINGS_CATALOG } from "../../utils/settingUtils";
import "./MonitoringPanel.css";

function MonitoringPanel({ formData, fieldErrors, onChange, disabled }) {
  const cpuMeta = SETTINGS_CATALOG.cpu_threshold;
  const ramMeta = SETTINGS_CATALOG.ram_threshold;
  const diskMeta = SETTINGS_CATALOG.disk_threshold;
  const hbMeta = SETTINGS_CATALOG.heartbeat_interval;

  const handleNumberChange = (key, rawValue) => {
    if (rawValue === "") {
      onChange(key, "");
      return;
    }
    const parsed = parseInt(rawValue, 10);
    onChange(key, isNaN(parsed) ? rawValue : parsed);
  };

  return (
    <div className="settings-panel-card" data-testid="settings-monitoring-panel">
      <div className="settings-panel-header">
        <div className="settings-panel-icon-badge settings-panel-icon-badge--orange">
          <Icon type="issue" size={20} />
        </div>
        <div className="settings-panel-title-group">
          <h3 className="settings-panel-title">Monitoring & Alert Thresholds</h3>
          <p className="settings-panel-subtitle">
            Define fleet-wide resource utilization limits and client agent heartbeat intervals.
          </p>
        </div>
      </div>

      <div className="settings-panel-body">
        <div className="settings-form-grid">
          {/* CPU Threshold */}
          <div className={`settings-field-group ${fieldErrors.cpu_threshold ? "has-error" : ""}`}>
            <label htmlFor="setting-cpu-threshold" className="settings-field-label">
              {cpuMeta.label} ({cpuMeta.unit})
            </label>
            <div className="settings-input-unit-wrapper">
              <input
                id="setting-cpu-threshold"
                type="number"
                min={cpuMeta.min}
                max={cpuMeta.max}
                className="settings-text-input settings-input-with-unit"
                value={formData.cpu_threshold ?? ""}
                onChange={(e) => handleNumberChange("cpu_threshold", e.target.value)}
                disabled={disabled}
              />
              <span className="settings-unit-tag">{cpuMeta.unit}</span>
            </div>
            {fieldErrors.cpu_threshold ? (
              <span className="settings-field-error">{fieldErrors.cpu_threshold}</span>
            ) : (
              <small className="settings-field-hint">{cpuMeta.description}</small>
            )}
          </div>

          {/* RAM Threshold */}
          <div className={`settings-field-group ${fieldErrors.ram_threshold ? "has-error" : ""}`}>
            <label htmlFor="setting-ram-threshold" className="settings-field-label">
              {ramMeta.label} ({ramMeta.unit})
            </label>
            <div className="settings-input-unit-wrapper">
              <input
                id="setting-ram-threshold"
                type="number"
                min={ramMeta.min}
                max={ramMeta.max}
                className="settings-text-input settings-input-with-unit"
                value={formData.ram_threshold ?? ""}
                onChange={(e) => handleNumberChange("ram_threshold", e.target.value)}
                disabled={disabled}
              />
              <span className="settings-unit-tag">{ramMeta.unit}</span>
            </div>
            {fieldErrors.ram_threshold ? (
              <span className="settings-field-error">{fieldErrors.ram_threshold}</span>
            ) : (
              <small className="settings-field-hint">{ramMeta.description}</small>
            )}
          </div>

          {/* Disk Threshold */}
          <div className={`settings-field-group ${fieldErrors.disk_threshold ? "has-error" : ""}`}>
            <label htmlFor="setting-disk-threshold" className="settings-field-label">
              {diskMeta.label} ({diskMeta.unit})
            </label>
            <div className="settings-input-unit-wrapper">
              <input
                id="setting-disk-threshold"
                type="number"
                min={diskMeta.min}
                max={diskMeta.max}
                className="settings-text-input settings-input-with-unit"
                value={formData.disk_threshold ?? ""}
                onChange={(e) => handleNumberChange("disk_threshold", e.target.value)}
                disabled={disabled}
              />
              <span className="settings-unit-tag">{diskMeta.unit}</span>
            </div>
            {fieldErrors.disk_threshold ? (
              <span className="settings-field-error">{fieldErrors.disk_threshold}</span>
            ) : (
              <small className="settings-field-hint">{diskMeta.description}</small>
            )}
          </div>

          {/* Heartbeat Interval */}
          <div className={`settings-field-group ${fieldErrors.heartbeat_interval ? "has-error" : ""}`}>
            <label htmlFor="setting-heartbeat-interval" className="settings-field-label">
              {hbMeta.label} ({hbMeta.unit})
            </label>
            <div className="settings-input-unit-wrapper">
              <input
                id="setting-heartbeat-interval"
                type="number"
                min={hbMeta.min}
                max={hbMeta.max}
                className="settings-text-input settings-input-with-unit"
                value={formData.heartbeat_interval ?? ""}
                onChange={(e) => handleNumberChange("heartbeat_interval", e.target.value)}
                disabled={disabled}
              />
              <span className="settings-unit-tag">{hbMeta.unit}</span>
            </div>
            {fieldErrors.heartbeat_interval ? (
              <span className="settings-field-error">{fieldErrors.heartbeat_interval}</span>
            ) : (
              <small className="settings-field-hint">{hbMeta.description}</small>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default MonitoringPanel;
