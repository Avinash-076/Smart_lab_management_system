import Icon from "../../../../components/ui/Icon";
import { SoftwareIcon, WindowsLogoIcon } from "../../utils/softwareUtils";
import { exportFleetSoftwareToCsv } from "../../../../services/softwareService";
import "./SoftwareDetailModal.css";

export default function SoftwareDetailModal({
  software,
  onClose,
  onViewComputer,
}) {
  if (!software) return null;

  const computersList = software.computers || [];
  const totalComputers = software.total_computers || 5;
  const installedCount = software.installed_count || computersList.length || 1;

  const handleExportThis = () => {
    exportFleetSoftwareToCsv([software], `software_${software.name}`);
  };

  return (
    <div className="software-modal-overlay" onClick={onClose}>
      <div
        className="software-modal-container"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        {/* ========================================================
            Modal Header
        ======================================================== */}
        <div className="software-modal-header">
          <div className="software-modal-title-wrap">
            <div className="software-modal-app-icon">
              <SoftwareIcon name={software.name} publisher={software.publisher} size={36} />
            </div>
            <div>
              <div className="software-modal-name-row">
                <h2 className="software-modal-title">{software.name}</h2>
                <code className="software-modal-version-tag">
                  {software.version || "Unknown version"}
                </code>
              </div>
              <span className="software-modal-publisher">
                {software.publisher || "Unknown publisher"}
              </span>
            </div>
          </div>

          <button
            type="button"
            className="software-modal-close-btn"
            onClick={onClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* ========================================================
            Overview Metrics Bar
        ======================================================== */}
        <div className="software-modal-metrics-bar">
          <div className="software-modal-metric-item">
            <span className="software-modal-metric-label">Installations</span>
            <span className="software-modal-metric-val blue">
              {installedCount} of {totalComputers} computers
            </span>
          </div>

          <div className="software-modal-metric-item">
            <span className="software-modal-metric-label">Operating System</span>
            <div className="software-modal-os-val">
              <WindowsLogoIcon size={14} />
              <span>{software.os_display || "Windows 10/11"}</span>
            </div>
          </div>

          <div className="software-modal-metric-item">
            <span className="software-modal-metric-label">Architecture</span>
            <span className="software-modal-metric-val">
              {software.architecture || "64-bit"}
            </span>
          </div>

          <div className="software-modal-metric-item">
            <span className="software-modal-metric-label">First Recorded</span>
            <span className="software-modal-metric-val">
              {software.install_date
                ? software.install_date.split("T")[0]
                : "Active"}
            </span>
          </div>
        </div>

        {/* ========================================================
            Details & Install Location
        ======================================================== */}
        {software.install_location && (
          <div className="software-modal-location-box">
            <span className="software-modal-location-label">
              Install Location / Path:
            </span>
            <code className="software-modal-location-code">
              {software.install_location}
            </code>
          </div>
        )}

        {/* ========================================================
            Computers Table
        ======================================================== */}
        <div className="software-modal-section">
          <div className="software-modal-section-header">
            <h3>Installed On ({computersList.length} Computers)</h3>
            <span className="software-modal-section-hint">
              Target machines currently reporting this software package
            </span>
          </div>

          {computersList.length === 0 ? (
            <div className="software-modal-empty-computers">
              <Icon type="computer" size={24} />
              <span>No individual computer telemetry records attached.</span>
            </div>
          ) : (
            <div className="software-modal-table-wrap">
              <table className="software-modal-computers-table">
                <thead>
                  <tr>
                    <th>Computer Name</th>
                    <th>IP Address</th>
                    <th>Operating System</th>
                    <th>Agent Status</th>
                    <th>Install Date</th>
                    {onViewComputer && <th>Action</th>}
                  </tr>
                </thead>
                <tbody>
                  {computersList.map((comp) => (
                    <tr key={comp.id}>
                      <td>
                        <div className="software-modal-comp-name">
                          <Icon type="computer" size={16} />
                          <strong>{comp.hostname}</strong>
                        </div>
                      </td>
                      <td>
                        <span className="software-modal-ip">
                          {comp.ip_address || "—"}
                        </span>
                      </td>
                      <td>
                        <div className="software-modal-comp-os">
                          <WindowsLogoIcon size={12} />
                          <span>{comp.os || "Windows"}</span>
                        </div>
                      </td>
                      <td>
                        <span
                          className={`software-modal-status-badge ${
                            comp.status === "online" ? "online" : "offline"
                          }`}
                        >
                          {comp.status || "offline"}
                        </span>
                      </td>
                      <td>
                        <span className="software-modal-date">
                          {comp.install_date
                            ? comp.install_date.split("T")[0]
                            : "—"}
                        </span>
                      </td>
                      {onViewComputer && (
                        <td>
                          <button
                            type="button"
                            className="software-modal-view-comp-btn"
                            onClick={() => {
                              onClose();
                              onViewComputer({ id: comp.id, hostname: comp.hostname });
                            }}
                          >
                            View
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* ========================================================
            Modal Footer
        ======================================================== */}
        <div className="software-modal-footer">
          <button
            type="button"
            className="software-modal-export-btn"
            onClick={handleExportThis}
          >
            <Icon type="download" size={15} />
            <span>Export Application Details</span>
          </button>

          <button
            type="button"
            className="software-modal-close-action-btn"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
