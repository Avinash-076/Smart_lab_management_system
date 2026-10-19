import { useState } from "react";
import Icon from "../../../../components/ui/Icon";
import { SETTING_CATEGORIES } from "../../utils/settingUtils";
import "./ResetConfirmModal.css";

function ResetConfirmModal({
  isOpen,
  onClose,
  onConfirmReset,
  activeTab,
  resetting,
}) {
  const [resetScope, setResetScope] = useState("all");

  if (!isOpen) return null;

  const currentTabObj = SETTING_CATEGORIES.find((c) => c.id === activeTab);
  const canResetCategory = activeTab && activeTab !== "all";

  const handleConfirm = () => {
    if (resetScope === "category" && canResetCategory) {
      onConfirmReset(activeTab);
    } else {
      onConfirmReset(null);
    }
  };

  return (
    <div className="settings-modal-backdrop" onClick={onClose} data-testid="reset-confirm-modal">
      <div className="settings-modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="settings-modal-header">
          <div className="settings-modal-title-group">
            <div className="settings-modal-icon-badge">
              <Icon type="refresh" size={20} />
            </div>
            <div>
              <h3 className="settings-modal-title">Reset Settings to Factory Defaults</h3>
              <p className="settings-modal-subtitle">
                Revert configuration keys back to system catalog defaults.
              </p>
            </div>
          </div>
          <button
            type="button"
            className="settings-modal-close-btn"
            onClick={onClose}
            disabled={resetting}
            aria-label="Close dialog"
          >
            <Icon type="close" size={18} />
          </button>
        </div>

        {/* Content */}
        <div className="settings-modal-body">
          <div className="settings-modal-warning-box">
            <Icon type="issue" size={20} />
            <p>
              This action will reset your persisted laboratory configuration. Unsaved custom values will be overwritten with the system default values.
            </p>
          </div>

          {canResetCategory && (
            <div className="settings-modal-scope-selector">
              <label className="settings-modal-scope-label">Choose Reset Scope:</label>

              <label className="settings-scope-option">
                <input
                  type="radio"
                  name="resetScope"
                  value="category"
                  checked={resetScope === "category"}
                  onChange={() => setResetScope("category")}
                />
                <div>
                  <strong>Only {currentTabObj?.label} Settings</strong>
                  <p>Reset only settings in the currently active tab.</p>
                </div>
              </label>

              <label className="settings-scope-option">
                <input
                  type="radio"
                  name="resetScope"
                  value="all"
                  checked={resetScope === "all"}
                  onChange={() => setResetScope("all")}
                />
                <div>
                  <strong>All System Settings</strong>
                  <p>Reset all laboratory, telemetry, alert, and agent parameters.</p>
                </div>
              </label>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="settings-modal-footer">
          <button
            type="button"
            className="settings-modal-cancel-btn"
            onClick={onClose}
            disabled={resetting}
          >
            Cancel
          </button>
          <button
            type="button"
            className="settings-modal-confirm-btn"
            onClick={handleConfirm}
            disabled={resetting}
          >
            <Icon type="refresh" size={15} />
            <span>{resetting ? "Restoring..." : "Restore Defaults"}</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default ResetConfirmModal;
