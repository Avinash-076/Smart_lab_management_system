import { useState } from "react";
import Icon from "../../../../components/ui/Icon";
import { changePassword } from "../../../../services/authService";
import "./SecurityPanel.css";

function SecurityPanel() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSuccessMsg("");
    setErrorMsg("");

    if (!currentPassword) {
      setErrorMsg("Please enter your current password.");
      return;
    }

    if (!newPassword || newPassword.length < 6) {
      setErrorMsg("New password must be at least 6 characters long.");
      return;
    }

    if (newPassword.length > 128) {
      setErrorMsg("New password cannot exceed 128 characters.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setErrorMsg("New password and confirm password do not match.");
      return;
    }

    if (currentPassword === newPassword) {
      setErrorMsg("New password must be different from current password.");
      return;
    }

    try {
      setSubmitting(true);
      const res = await changePassword(currentPassword, newPassword);
      setSuccessMsg(res?.message || "Password updated successfully!");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setErrorMsg(err.detail || err.message || "Failed to update password. Please check your credentials.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="settings-panel-card" data-testid="settings-security-panel">
      <div className="settings-panel-header">
        <div className="settings-panel-icon-badge settings-panel-icon-badge--purple">
          <Icon type="shield" size={20} />
        </div>
        <div className="settings-panel-title-group">
          <h3 className="settings-panel-title">Account Security &amp; Password</h3>
          <p className="settings-panel-subtitle">
            Update your master administrator account password. Changes take effect immediately.
          </p>
        </div>
      </div>

      <div className="settings-panel-body">
        {successMsg && (
          <div className="security-alert security-alert--success" role="alert">
            <Icon type="check" size={18} />
            <span>{successMsg}</span>
            <button
              type="button"
              className="security-alert-close"
              onClick={() => setSuccessMsg("")}
              aria-label="Dismiss alert"
            >
              &times;
            </button>
          </div>
        )}

        {errorMsg && (
          <div className="security-alert security-alert--error" role="alert">
            <Icon type="issue" size={18} />
            <span>{errorMsg}</span>
            <button
              type="button"
              className="security-alert-close"
              onClick={() => setErrorMsg("")}
              aria-label="Dismiss alert"
            >
              &times;
            </button>
          </div>
        )}

        <form onSubmit={handleSubmit} className="security-password-form">
          <div className="security-form-grid">
            {/* Current Password */}
            <div className="settings-field-group">
              <label htmlFor="sec-current-password" className="settings-field-label">
                Current Password <span className="settings-required">*</span>
              </label>
              <div className="security-input-wrapper">
                <input
                  id="sec-current-password"
                  type={showCurrent ? "text" : "password"}
                  className="settings-text-input security-text-input"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  placeholder="Enter current password"
                  autoComplete="current-password"
                  disabled={submitting}
                />
                <button
                  type="button"
                  className="security-pw-toggle"
                  onClick={() => setShowCurrent(!showCurrent)}
                  tabIndex="-1"
                  aria-label={showCurrent ? "Hide password" : "Show password"}
                >
                  <Icon type={showCurrent ? "eyeOff" : "eye"} size={16} />
                </button>
              </div>
            </div>

            {/* New Password */}
            <div className="settings-field-group">
              <label htmlFor="sec-new-password" className="settings-field-label">
                New Password <span className="settings-required">*</span>
              </label>
              <div className="security-input-wrapper">
                <input
                  id="sec-new-password"
                  type={showNew ? "text" : "password"}
                  className="settings-text-input security-text-input"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 6 characters"
                  autoComplete="new-password"
                  disabled={submitting}
                />
                <button
                  type="button"
                  className="security-pw-toggle"
                  onClick={() => setShowNew(!showNew)}
                  tabIndex="-1"
                  aria-label={showNew ? "Hide password" : "Show password"}
                >
                  <Icon type={showNew ? "eyeOff" : "eye"} size={16} />
                </button>
              </div>
              <small className="settings-field-hint">
                Must be at least 6 characters long (max 128 characters).
              </small>
            </div>

            {/* Confirm New Password */}
            <div className="settings-field-group">
              <label htmlFor="sec-confirm-password" className="settings-field-label">
                Confirm New Password <span className="settings-required">*</span>
              </label>
              <div className="security-input-wrapper">
                <input
                  id="sec-confirm-password"
                  type={showConfirm ? "text" : "password"}
                  className="settings-text-input security-text-input"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter new password"
                  autoComplete="new-password"
                  disabled={submitting}
                />
                <button
                  type="button"
                  className="security-pw-toggle"
                  onClick={() => setShowConfirm(!showConfirm)}
                  tabIndex="-1"
                  aria-label={showConfirm ? "Hide password" : "Show password"}
                >
                  <Icon type={showConfirm ? "eyeOff" : "eye"} size={16} />
                </button>
              </div>
            </div>
          </div>

          <div className="security-action-footer">
            <button
              type="submit"
              className="security-submit-btn"
              disabled={submitting || !currentPassword || !newPassword || !confirmPassword}
            >
              {submitting ? (
                <>
                  <Icon type="refresh" size={16} className="settings-spin" />
                  <span>Updating Password...</span>
                </>
              ) : (
                <>
                  <Icon type="lock" size={16} />
                  <span>Update Password</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default SecurityPanel;
