import Icon from "../../../../components/ui/Icon";
import "./SettingsHeader.css";

function SettingsHeader({
  isDirty,
  canManageSettings,
  saving,
  resetting,
  loading,
  lastUpdated,
  onSave,
  onOpenResetModal,
  onDiscard,
  message,
  onDismissMessage,
  error,
  onDismissError,
  hasValidationErrors,
}) {
  return (
    <div className="settings-header-container" data-testid="settings-header">
      {/* Top Action Toolbar */}
      <div className="settings-toolbar">
        <div className="settings-toolbar-left">
          {isDirty ? (
            <div className="settings-status-badge settings-status-badge--dirty" title="You have modified settings that are not yet saved">
              <span className="settings-status-dot settings-status-dot--dirty" />
              <span>Unsaved Changes</span>
            </div>
          ) : (
            <div className="settings-status-badge settings-status-badge--clean" title="All settings are synchronized with database">
              <span className="settings-status-dot settings-status-dot--clean" />
              <span>All Settings Saved</span>
            </div>
          )}

          {!canManageSettings && (
            <div className="settings-status-badge settings-status-badge--readonly" title="You have read-only privileges">
              <Icon type="computer" size={14} />
              <span>Read-Only Mode</span>
            </div>
          )}

          {lastUpdated && (
            <div className="settings-timestamp-badge" title={`Last updated: ${new Date(lastUpdated).toLocaleString()}`}>
              <Icon type="refresh" size={13} />
              <span>Updated {new Date(lastUpdated).toLocaleDateString()} {new Date(lastUpdated).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
            </div>
          )}
        </div>

        <div className="settings-toolbar-right">
          {isDirty && (
            <button
              type="button"
              className="settings-btn settings-btn--discard"
              onClick={onDiscard}
              disabled={saving || resetting || loading}
              title="Discard all unsaved edits and revert to current saved values"
            >
              <Icon type="close" size={15} />
              <span>Discard Changes</span>
            </button>
          )}

          {canManageSettings && (
            <button
              type="button"
              className="settings-btn settings-btn--reset"
              onClick={onOpenResetModal}
              disabled={saving || resetting || loading}
              title="Reset configuration to factory defaults"
            >
              <Icon type="refresh" size={15} />
              <span>{resetting ? "Resetting..." : "Reset Defaults"}</span>
            </button>
          )}

          {canManageSettings && (
            <button
              type="button"
              className={`settings-btn settings-btn--save ${isDirty ? "settings-btn--pulse" : ""}`}
              onClick={onSave}
              disabled={!isDirty || saving || resetting || loading || hasValidationErrors}
              title={
                hasValidationErrors
                  ? "Please resolve validation errors first"
                  : !isDirty
                  ? "No changes to save"
                  : "Save all modified settings to database"
              }
            >
              <Icon type="check" size={16} />
              <span>{saving ? "Saving..." : "Save Changes"}</span>
            </button>
          )}
        </div>
      </div>

      {/* Success Alert Banner */}
      {message && (
        <div className="settings-alert-banner settings-alert-banner--success" role="alert">
          <div className="settings-alert-content">
            <Icon type="check" size={18} />
            <span>{message}</span>
          </div>
          <button
            type="button"
            className="settings-alert-close"
            onClick={onDismissMessage}
            aria-label="Dismiss alert"
          >
            <Icon type="close" size={14} />
          </button>
        </div>
      )}

      {/* Error Alert Banner */}
      {error && (
        <div className="settings-alert-banner settings-alert-banner--error" role="alert">
          <div className="settings-alert-content">
            <Icon type="issue" size={18} />
            <span>{error}</span>
          </div>
          <button
            type="button"
            className="settings-alert-close"
            onClick={onDismissError}
            aria-label="Dismiss error"
          >
            <Icon type="close" size={14} />
          </button>
        </div>
      )}

      {/* Read-only Information Banner if Viewer */}
      {!canManageSettings && (
        <div className="settings-alert-banner settings-alert-banner--info" role="status">
          <div className="settings-alert-content">
            <Icon type="computer" size={18} />
            <span>
              <strong>View Only:</strong> You are signed in with read-only access. You can review current configuration parameters, but <code>MANAGE_SETTINGS</code> permission is required to update them.
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default SettingsHeader;
