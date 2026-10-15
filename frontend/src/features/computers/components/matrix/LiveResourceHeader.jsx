import { useState } from "react";
import Icon from "../../../../components/ui/Icon";
import "./LiveResourceHeader.css";

function LiveResourceHeader({
  timeRange = "1h",
  onTimeRangeChange,
  customRange = { start: "", end: "" },
  onCustomRangeChange,
  onApplyCustomRange,
  onRefresh,
  loading = false,
  isLive = true,
}) {
  const [showCustomPicker, setShowCustomPicker] = useState(false);
  const [localStart, setLocalStart] = useState(customRange.start || "");
  const [localEnd, setLocalEnd] = useState(customRange.end || "");
  const [pickerError, setPickerError] = useState("");

  const handlePresetClick = (preset) => {
    setShowCustomPicker(false);
    setPickerError("");
    if (onTimeRangeChange) {
      onTimeRangeChange(preset);
    }
  };

  const handleToggleCustom = () => {
    if (!showCustomPicker) {
      // Default to last 1 hour if empty
      const now = new Date();
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000);
      const toLocalIso = (d) => {
        const offset = d.getTimezoneOffset() * 60000;
        return new Date(d.getTime() - offset).toISOString().slice(0, 16);
      };
      if (!localStart) setLocalStart(toLocalIso(oneHourAgo));
      if (!localEnd) setLocalEnd(toLocalIso(now));
    }
    setShowCustomPicker(!showCustomPicker);
    setPickerError("");
  };

  const handleApplyCustom = () => {
    if (!localStart || !localEnd) {
      setPickerError("Please select both start and end time.");
      return;
    }
    const startDt = new Date(localStart);
    const endDt = new Date(localEnd);
    if (isNaN(startDt.getTime()) || isNaN(endDt.getTime())) {
      setPickerError("Invalid date/time format.");
      return;
    }
    if (startDt >= endDt) {
      setPickerError("Start time must be before end time.");
      return;
    }

    setPickerError("");
    if (onCustomRangeChange) {
      onCustomRangeChange({ start: localStart, end: localEnd });
    }
    if (onApplyCustomRange) {
      onApplyCustomRange({ start: startDt, end: endDt });
    }
    setShowCustomPicker(false);
  };

  return (
    <div className="live-resource-header">
      <div className="live-header-left">
        <div className="live-title-wrap">
          <div className="live-icon-badge" aria-hidden="true">
            <Icon type="nodes" size={18} />
          </div>
          <h2 className="live-section-title">Live Resource Usage</h2>
          {isLive && (
            <span className="live-status-pill">
              <span className="live-pulse-dot" />
              Live
            </span>
          )}
        </div>
      </div>

      <div className="live-header-right">
        <div className="time-filter-btn-group" role="group" aria-label="Time range selector">
          <button
            type="button"
            className={`time-filter-btn ${timeRange === "1h" && !showCustomPicker ? "active" : ""}`}
            onClick={() => handlePresetClick("1h")}
            disabled={loading}
          >
            1 Hour
          </button>
          <button
            type="button"
            className={`time-filter-btn ${timeRange === "6h" && !showCustomPicker ? "active" : ""}`}
            onClick={() => handlePresetClick("6h")}
            disabled={loading}
          >
            6 Hours
          </button>
          <button
            type="button"
            className={`time-filter-btn ${timeRange === "24h" && !showCustomPicker ? "active" : ""}`}
            onClick={() => handlePresetClick("24h")}
            disabled={loading}
          >
            24 Hours
          </button>
          <button
            type="button"
            className={`time-filter-btn custom-range-btn ${timeRange === "custom" || showCustomPicker ? "active" : ""}`}
            onClick={handleToggleCustom}
            disabled={loading}
          >
            <Icon type="calendar" size={14} />
            <span>Custom Range</span>
          </button>
        </div>

        {onRefresh && (
          <button
            type="button"
            className={`matrix-refresh-btn ${loading ? "spinning" : ""}`}
            onClick={onRefresh}
            title="Refresh metrics data"
            disabled={loading}
          >
            <Icon type="refresh" size={15} />
          </button>
        )}
      </div>

      {showCustomPicker && (
        <div className="custom-range-picker-popover" role="dialog" aria-label="Custom Date Range Picker">
          <div className="picker-title-row">
            <h4>Select Custom Range</h4>
            <button
              type="button"
              className="picker-close-btn"
              onClick={() => setShowCustomPicker(false)}
            >
              ×
            </button>
          </div>

          <div className="picker-inputs-grid">
            <div className="picker-field">
              <label htmlFor="custom-start-dt">From</label>
              <input
                id="custom-start-dt"
                type="datetime-local"
                value={localStart}
                onChange={(e) => setLocalStart(e.target.value)}
              />
            </div>
            <div className="picker-field">
              <label htmlFor="custom-end-dt">To</label>
              <input
                id="custom-end-dt"
                type="datetime-local"
                value={localEnd}
                onChange={(e) => setLocalEnd(e.target.value)}
              />
            </div>
          </div>

          {pickerError && <div className="picker-error-text">{pickerError}</div>}

          <div className="picker-actions-row">
            <button
              type="button"
              className="picker-cancel-btn"
              onClick={() => setShowCustomPicker(false)}
            >
              Cancel
            </button>
            <button
              type="button"
              className="picker-apply-btn"
              onClick={handleApplyCustom}
            >
              Apply Filter
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default LiveResourceHeader;
