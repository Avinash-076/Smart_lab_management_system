import { useState, useMemo } from "react";
import Icon from "../../../components/ui/Icon";
import { useSettings } from "../hooks/useSettings";
import { SETTINGS_CATALOG } from "../utils/settingUtils";

import SettingsHeader from "../components/SettingsHeader/SettingsHeader";
import SettingsTabs from "../components/SettingsTabs/SettingsTabs";
import LaboratoryPanel from "../components/LaboratoryPanel/LaboratoryPanel";
import MonitoringPanel from "../components/MonitoringPanel/MonitoringPanel";
import NotificationsPanel from "../components/NotificationsPanel/NotificationsPanel";
import AgentPanel from "../components/AgentPanel/AgentPanel";
import ResetConfirmModal from "../components/ResetConfirmModal/ResetConfirmModal";

import "./Settings.css";

function Settings() {
  const {
    formData,
    persistedData,
    fieldErrors,
    activeTab,
    setActiveTab,
    loading,
    saving,
    resetting,
    message,
    setMessage,
    error,
    setError,
    lastUpdated,
    canManageSettings,
    isDirty,
    handleFieldChange,
    handleSave,
    handleReset,
    handleDiscard,
  } = useSettings();

  const [resetModalOpen, setResetModalOpen] = useState(false);

  // Compute number of modified fields per category for tab indicators
  const categoryDirtyCounts = useMemo(() => {
    const counts = { all: 0, general: 0, monitoring: 0, notifications: 0, agent: 0 };
    for (const [key, meta] of Object.entries(SETTINGS_CATALOG)) {
      if (formData[key] !== persistedData[key]) {
        counts.all += 1;
        if (meta.category && counts[meta.category] !== undefined) {
          counts[meta.category] += 1;
        }
      }
    }
    return counts;
  }, [formData, persistedData]);

  const hasValidationErrors = Object.keys(fieldErrors).length > 0;

  const handleConfirmReset = async (categoryScope) => {
    setResetModalOpen(false);
    if (categoryScope && categoryScope !== "all") {
      const keysToReset = Object.entries(SETTINGS_CATALOG)
        .filter(([, meta]) => meta.category === categoryScope)
        .map(([key]) => key);
      await handleReset(keysToReset);
    } else {
      await handleReset(null);
    }
  };

  return (
    <div className="settings-page-wrapper" data-testid="settings-page">
      {/* Action Toolbar & Feedback Alerts (Replaces duplicate title header) */}
      <SettingsHeader
        isDirty={isDirty}
        canManageSettings={canManageSettings}
        saving={saving}
        resetting={resetting}
        loading={loading}
        lastUpdated={lastUpdated}
        onSave={handleSave}
        onOpenResetModal={() => setResetModalOpen(true)}
        onDiscard={handleDiscard}
        message={message}
        onDismissMessage={() => setMessage("")}
        error={error}
        onDismissError={() => setError("")}
        hasValidationErrors={hasValidationErrors}
      />

      {/* Category Navigation Tabs */}
      <SettingsTabs
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        categoryDirtyCounts={categoryDirtyCounts}
      />

      {/* Loading State */}
      {loading ? (
        <div className="settings-loading-card">
          <Icon type="refresh" size={28} className="settings-spin" />
          <p>Loading application configuration...</p>
        </div>
      ) : (
        <div className="settings-panels-flow">
          {/* Panel 1: Laboratory Configuration */}
          {(activeTab === "all" || activeTab === "general") && (
            <LaboratoryPanel
              formData={formData}
              fieldErrors={fieldErrors}
              onChange={handleFieldChange}
              disabled={!canManageSettings || saving || resetting}
            />
          )}

          {/* Panel 2: Monitoring & Alert Thresholds */}
          {(activeTab === "all" || activeTab === "monitoring") && (
            <MonitoringPanel
              formData={formData}
              fieldErrors={fieldErrors}
              onChange={handleFieldChange}
              disabled={!canManageSettings || saving || resetting}
            />
          )}

          {/* Panel 3: Notifications & Alert Subscriptions */}
          {(activeTab === "all" || activeTab === "notifications") && (
            <NotificationsPanel
              formData={formData}
              onChange={handleFieldChange}
              disabled={!canManageSettings || saving || resetting}
            />
          )}

          {/* Panel 4: Client Agent & Data Retention */}
          {(activeTab === "all" || activeTab === "agent") && (
            <AgentPanel
              formData={formData}
              fieldErrors={fieldErrors}
              onChange={handleFieldChange}
              disabled={!canManageSettings || saving || resetting}
            />
          )}
        </div>
      )}

      {/* Confirmation Modal for Resetting */}
      <ResetConfirmModal
        isOpen={resetModalOpen}
        onClose={() => setResetModalOpen(false)}
        onConfirmReset={handleConfirmReset}
        activeTab={activeTab}
        resetting={resetting}
      />
    </div>
  );
}

export default Settings;