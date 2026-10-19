import { useState, useEffect, useCallback, useMemo } from "react";
import { getSettings, updateSettings, resetSettings } from "../../../services/settingService";
import { getCurrentUserProfile } from "../../../services/authService";
import {
  DEFAULT_SETTINGS,
  validateSettings,
  isFormDataDirty,
} from "../utils/settingUtils";

export function useSettings() {
  const [formData, setFormData] = useState(DEFAULT_SETTINGS);
  const [persistedData, setPersistedData] = useState(DEFAULT_SETTINGS);
  const [activeTab, setActiveTab] = useState("all");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [canManageSettings, setCanManageSettings] = useState(true);

  // Field-level validation errors
  const [fieldErrors, setFieldErrors] = useState({});

  const [refreshIndex, setRefreshIndex] = useState(0);

  const reload = useCallback(() => {
    setLoading(true);
    setRefreshIndex((i) => i + 1);
  }, []);

  // Fetch initial settings and user permissions
  useEffect(() => {
    let isSubscribed = true;

    async function fetchData() {
      try {
        const [settingsRes, userProfile] = await Promise.all([
          getSettings().catch((err) => {
            throw err;
          }),
          getCurrentUserProfile().catch(() => null),
        ]);

        if (!isSubscribed) return;

        if (userProfile && Array.isArray(userProfile.permissions)) {
          setCanManageSettings(userProfile.permissions.includes("MANAGE_SETTINGS"));
        } else {
          setCanManageSettings(true);
        }

        if (settingsRes && settingsRes.settings_map) {
          const merged = {
            ...DEFAULT_SETTINGS,
            ...settingsRes.settings_map,
          };
          setFormData(merged);
          setPersistedData(merged);
          setFieldErrors({});

          if (settingsRes.items) {
            const latest = settingsRes.items.find((i) => i.updated_at);
            if (latest && latest.updated_at) {
              setLastUpdated(latest.updated_at);
            }
          }
        }
      } catch (err) {
        if (isSubscribed) {
          setError(err.message || "Failed to load system settings");
        }
      } finally {
        if (isSubscribed) {
          setLoading(false);
        }
      }
    }

    fetchData();

    return () => {
      isSubscribed = false;
    };
  }, [refreshIndex]);

  // Handle single field modification
  const handleFieldChange = useCallback((key, value) => {
    setFormData((prev) => {
      const next = { ...prev, [key]: value };
      const errors = validateSettings(next);
      setFieldErrors(errors);
      return next;
    });
    setError("");
  }, []);

  // Check if form is dirty
  const isDirty = useMemo(() => {
    return isFormDataDirty(formData, persistedData);
  }, [formData, persistedData]);

  // Save changes
  const handleSave = useCallback(async () => {
    if (!canManageSettings) {
      setError("You do not have permission to modify system settings.");
      return;
    }

    const errors = validateSettings(formData);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      setError("Please resolve the validation errors before saving.");
      return;
    }

    setSaving(true);
    setError("");
    setMessage("");

    try {
      const res = await updateSettings(formData);
      if (res && res.settings_map) {
        const merged = { ...DEFAULT_SETTINGS, ...res.settings_map };
        setFormData(merged);
        setPersistedData(merged);
      }
      setMessage("Configuration saved and applied successfully.");
      setLastUpdated(new Date().toISOString());
      setFieldErrors({});

      setTimeout(() => {
        setMessage("");
      }, 4000);
    } catch (err) {
      setError(err.message || "Failed to save configuration settings");
    } finally {
      setSaving(false);
    }
  }, [formData, canManageSettings]);

  // Reset to system defaults
  const handleReset = useCallback(async (keys = null) => {
    if (!canManageSettings) {
      setError("You do not have permission to reset system settings.");
      return;
    }

    setResetting(true);
    setError("");
    setMessage("");

    try {
      const res = await resetSettings(keys);
      if (res && res.settings_map) {
        const merged = { ...DEFAULT_SETTINGS, ...res.settings_map };
        setFormData(merged);
        setPersistedData(merged);
      }
      setMessage(
        keys
          ? "Selected settings have been restored to defaults."
          : "All settings have been restored to system defaults."
      );
      setLastUpdated(new Date().toISOString());
      setFieldErrors({});

      setTimeout(() => {
        setMessage("");
      }, 4000);
    } catch (err) {
      setError(err.message || "Failed to reset settings to defaults");
    } finally {
      setResetting(false);
    }
  }, [canManageSettings]);

  // Discard changes
  const handleDiscard = useCallback(() => {
    setFormData(persistedData);
    setFieldErrors({});
    setError("");
  }, [persistedData]);

  return {
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
    reload,
  };
}
