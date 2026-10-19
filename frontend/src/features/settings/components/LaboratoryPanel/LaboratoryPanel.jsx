import Icon from "../../../../components/ui/Icon";
import { SETTINGS_CATALOG } from "../../utils/settingUtils";
import "./LaboratoryPanel.css";

function LaboratoryPanel({ formData, fieldErrors, onChange, disabled }) {
  const nameMeta = SETTINGS_CATALOG.lab_name;
  const locMeta = SETTINGS_CATALOG.lab_location;
  const netMeta = SETTINGS_CATALOG.lab_network;

  return (
    <div className="settings-panel-card" data-testid="settings-laboratory-panel">
      <div className="settings-panel-header">
        <div className="settings-panel-icon-badge settings-panel-icon-badge--blue">
          <Icon type="computer" size={20} />
        </div>
        <div className="settings-panel-title-group">
          <h3 className="settings-panel-title">Laboratory Configuration</h3>
          <p className="settings-panel-subtitle">
            Configure facility identity, location coordinates, and network topology.
          </p>
        </div>
      </div>

      <div className="settings-panel-body">
        <div className="settings-form-grid">
          {/* Lab Name */}
          <div className={`settings-field-group ${fieldErrors.lab_name ? "has-error" : ""}`}>
            <label htmlFor="setting-lab-name" className="settings-field-label">
              {nameMeta.label} <span className="settings-required">*</span>
            </label>
            <input
              id="setting-lab-name"
              type="text"
              className="settings-text-input"
              value={formData.lab_name ?? ""}
              onChange={(e) => onChange("lab_name", e.target.value)}
              disabled={disabled}
              placeholder="e.g. Computer Laboratory A"
              maxLength={nameMeta.maxLen}
            />
            {fieldErrors.lab_name ? (
              <span className="settings-field-error">{fieldErrors.lab_name}</span>
            ) : (
              <small className="settings-field-hint">{nameMeta.description}</small>
            )}
          </div>

          {/* Lab Location */}
          <div className={`settings-field-group ${fieldErrors.lab_location ? "has-error" : ""}`}>
            <label htmlFor="setting-lab-location" className="settings-field-label">
              {locMeta.label}
            </label>
            <input
              id="setting-lab-location"
              type="text"
              className="settings-text-input"
              value={formData.lab_location ?? ""}
              onChange={(e) => onChange("lab_location", e.target.value)}
              disabled={disabled}
              placeholder="e.g. Andhra Polytechnic, Block C, Room 204"
              maxLength={locMeta.maxLen}
            />
            {fieldErrors.lab_location ? (
              <span className="settings-field-error">{fieldErrors.lab_location}</span>
            ) : (
              <small className="settings-field-hint">{locMeta.description}</small>
            )}
          </div>

          {/* Network Type */}
          <div className={`settings-field-group ${fieldErrors.lab_network ? "has-error" : ""}`}>
            <label htmlFor="setting-lab-network" className="settings-field-label">
              {netMeta.label}
            </label>
            <select
              id="setting-lab-network"
              className="settings-select-input"
              value={formData.lab_network ?? "LAN / Ethernet"}
              onChange={(e) => onChange("lab_network", e.target.value)}
              disabled={disabled}
            >
              {netMeta.options.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
            {fieldErrors.lab_network ? (
              <span className="settings-field-error">{fieldErrors.lab_network}</span>
            ) : (
              <small className="settings-field-hint">{netMeta.description}</small>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default LaboratoryPanel;
