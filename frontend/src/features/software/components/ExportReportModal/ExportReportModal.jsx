import { useState } from "react";
import Icon from "../../../../components/ui/Icon";
import { exportFleetSoftwareToCsv } from "../../../../services/softwareService";
import "./ExportReportModal.css";

export default function ExportReportModal({
  isOpen,
  onClose,
  softwareList = [],
  selectedSoftwareIds = new Set(),
}) {
  const [format, setFormat] = useState("csv");
  const [scope, setScope] = useState("all");
  const [includeLocation, setIncludeLocation] = useState(true);
  const [includeArchitecture, setIncludeArchitecture] = useState(true);

  if (!isOpen) return null;

  const handleExport = () => {
    let itemsToExport = softwareList;
    if (scope === "selected") {
      itemsToExport = softwareList.filter((s) =>
        selectedSoftwareIds.has(s.id)
      );
    }

    if (format === "csv") {
      exportFleetSoftwareToCsv(itemsToExport, "software_report");
    } else if (format === "json") {
      const dataStr =
        "data:text/json;charset=utf-8," +
        encodeURIComponent(JSON.stringify(itemsToExport, null, 2));
      const downloadAnchor = document.createElement("a");
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute(
        "download",
        `software_inventory_report_${new Date().toISOString().split("T")[0]}.json`
      );
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } else {
      window.print();
    }

    onClose();
  };

  return (
    <div className="software-modal-overlay" onClick={onClose}>
      <div
        className="software-export-modal-container"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="software-modal-header">
          <div className="software-modal-title-wrap">
            <div className="software-export-icon-badge">
              <Icon type="download" size={20} />
            </div>
            <div>
              <h2 className="software-modal-title">Export Software Report</h2>
              <span className="software-modal-publisher">
                Generate and download inventory report
              </span>
            </div>
          </div>
          <button
            type="button"
            className="software-modal-close-btn"
            onClick={onClose}
          >
            ✕
          </button>
        </div>

        <div className="software-export-modal-body">
          {/* Format selection */}
          <div className="software-export-field-group">
            <label className="software-export-field-title">File Format</label>
            <div className="software-export-format-options">
              <label
                className={`software-export-format-card ${
                  format === "csv" ? "active" : ""
                }`}
              >
                <input
                  type="radio"
                  name="format"
                  value="csv"
                  checked={format === "csv"}
                  onChange={() => setFormat("csv")}
                />
                <span className="format-name">CSV Spreadsheet</span>
                <span className="format-desc">Compatible with Excel & Sheets</span>
              </label>

              <label
                className={`software-export-format-card ${
                  format === "json" ? "active" : ""
                }`}
              >
                <input
                  type="radio"
                  name="format"
                  value="json"
                  checked={format === "json"}
                  onChange={() => setFormat("json")}
                />
                <span className="format-name">JSON Data</span>
                <span className="format-desc">Full programmatic dump</span>
              </label>
            </div>
          </div>

          {/* Scope selection */}
          <div className="software-export-field-group">
            <label className="software-export-field-title">Export Scope</label>
            <div className="software-export-scope-options">
              <label className="software-export-radio-label">
                <input
                  type="radio"
                  name="scope"
                  value="all"
                  checked={scope === "all"}
                  onChange={() => setScope("all")}
                />
                <span>All Loaded Records ({softwareList.length})</span>
              </label>

              <label
                className={`software-export-radio-label ${
                  selectedSoftwareIds.size === 0 ? "disabled" : ""
                }`}
              >
                <input
                  type="radio"
                  name="scope"
                  value="selected"
                  checked={scope === "selected"}
                  onChange={() => setScope("selected")}
                  disabled={selectedSoftwareIds.size === 0}
                />
                <span>
                  Selected Records Only ({selectedSoftwareIds.size})
                </span>
              </label>
            </div>
          </div>

          {/* Attributes to include */}
          <div className="software-export-field-group">
            <label className="software-export-field-title">
              Attributes Included
            </label>
            <div className="software-export-checkbox-grid">
              <label className="software-export-checkbox-label">
                <input
                  type="checkbox"
                  checked={includeLocation}
                  onChange={(e) => setIncludeLocation(e.target.checked)}
                />
                <span>Installation Paths & Directories</span>
              </label>
              <label className="software-export-checkbox-label">
                <input
                  type="checkbox"
                  checked={includeArchitecture}
                  onChange={(e) => setIncludeArchitecture(e.target.checked)}
                />
                <span>Architecture & Hardware Target (32/64-bit)</span>
              </label>
            </div>
          </div>
        </div>

        <div className="software-modal-footer">
          <button
            type="button"
            className="software-modal-close-action-btn"
            onClick={onClose}
          >
            Cancel
          </button>

          <button
            type="button"
            className="software-header-export-btn"
            onClick={handleExport}
          >
            <Icon type="download" size={16} />
            <span>Download Report</span>
          </button>
        </div>
      </div>
    </div>
  );
}
