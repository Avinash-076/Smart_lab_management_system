import Icon from "../../../../components/ui/Icon";
import { parseUptimeString, parseApiDate } from "../../utils/computerUtils";
import SoftwareSummaryCards from "../software/SoftwareSummaryCards";
import ProcessSummaryCards from "../processes/ProcessSummaryCards";
import CommandSummaryCards from "../remote-control/CommandSummaryCards";
import "./ComputerSummaryCard.css";

function ComputerIllustration() {
  return (
    <div className="summary-device-illu" aria-hidden="true">
      <svg
        viewBox="0 0 160 130"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="summary-device-svg"
      >
        <defs>
          <linearGradient id="screen-grad" x1="0" y1="0" x2="160" y2="100" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#1e3a8a" />
            <stop offset="50%" stopColor="#0f172a" />
            <stop offset="100%" stopColor="#172554" />
          </linearGradient>
          <linearGradient id="cube-grad-1" x1="50" y1="35" x2="80" y2="65" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#2563eb" stopOpacity="0.3" />
          </linearGradient>
          <linearGradient id="cube-grad-2" x1="75" y1="45" x2="105" y2="75" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#0284c7" stopOpacity="0.4" />
          </linearGradient>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Outer Monitor Frame */}
        <rect x="12" y="10" width="136" height="84" rx="8" fill="#0f172a" stroke="#334155" strokeWidth="2.5" />

        {/* Inner Screen */}
        <rect x="18" y="16" width="124" height="72" rx="4" fill="url(#screen-grad)" />

        {/* Futuristic Glowing Cubes Illustration */}
        <g filter="url(#glow)">
          {/* Back Cube */}
          <polygon points="62,42 76,34 90,42 76,50" fill="url(#cube-grad-1)" />
          <polygon points="62,42 76,50 76,66 62,58" fill="#1d4ed8" fillOpacity="0.6" />
          <polygon points="76,50 90,42 90,58 76,66" fill="#3b82f6" fillOpacity="0.7" />

          {/* Front Cube */}
          <polygon points="78,52 92,44 106,52 92,60" fill="url(#cube-grad-2)" />
          <polygon points="78,52 92,60 92,76 78,68" fill="#0284c7" fillOpacity="0.7" />
          <polygon points="92,60 106,52 106,68 92,76" fill="#38bdf8" fillOpacity="0.85" />
        </g>

        {/* Screen Stand & Base */}
        <path d="M72 95 L68 112 L92 112 L88 95 Z" fill="#1e293b" stroke="#334155" strokeWidth="1.5" />
        <rect x="52" y="112" width="56" height="7" rx="3.5" fill="#0f172a" stroke="#334155" strokeWidth="1.5" />
      </svg>
    </div>
  );
}

function MiniSparkline({ color = "#3b82f6" }) {
  return (
    <svg viewBox="0 0 100 24" fill="none" className="metric-sparkline" preserveAspectRatio="none">
      <path
        d="M2 14 C 18 6, 28 20, 44 12 C 58 4, 72 18, 86 10 C 92 6, 96 11, 98 12"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export default function ComputerSummaryCard({
  computer,
  latestMetric,
  activeTab = "hardware",
  softwareSummary = null,
  softwareLoading = false,
  processSummary = null,
  processLoading = false,
  commandSummary = null,
  commandLoading = false,
  onRunCommand = null,
  onScanNow = null,
  scanning = false,
}) {
  if (!computer) return null;

  const hostname = computer.hostname || `PC-${computer.id}`;
  const ipAddress = computer.ip_address || "—";
  const macAddress = computer.mac_address || "—";
  const isOnline = (computer.status || "offline").toLowerCase() === "online";
  const statusLabel = isOnline ? "Online" : "Offline";

  const hardware = computer.hardware || {};
  const agentVersion = hardware.agent_version || "—";
  const labName = computer.lab_name || (computer.lab ? computer.lab.name : null);

  // Last seen format
  let lastSeenText = "—";
  if (computer.last_seen) {
    try {
      const d = parseApiDate(computer.last_seen) || new Date(computer.last_seen);
      if (d && !isNaN(d.getTime())) {
        const now = new Date();
        const timeStr = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        if (d.toDateString() === now.toDateString()) {
          lastSeenText = `Today, ${timeStr}`;
        } else {
          lastSeenText = `${d.toLocaleDateString([], { month: "short", day: "numeric" })}, ${timeStr}`;
        }
      }
    } catch {
      lastSeenText = "—";
    }
  }

  // Metrics
  const cpuPercent =
    latestMetric && typeof latestMetric.cpu_usage === "number"
      ? Math.round(latestMetric.cpu_usage)
      : null;
  const ramPercent =
    latestMetric && typeof latestMetric.ram_usage === "number"
      ? Math.round(latestMetric.ram_usage)
      : null;
  const storagePercent =
    latestMetric && typeof latestMetric.disk_usage === "number"
      ? Math.round(latestMetric.disk_usage)
      : null;

  // Uptime
  const computedUptime = parseUptimeString(hardware.last_boot_time);
  const uptimeText = computedUptime || (isOnline ? "Active" : "—");

  return (
    <div className="computer-summary-card">
      {/* LEFT SECTION: Computer Identity */}
      <div className="summary-identity-section">
        <div className="summary-identity-left">
          <ComputerIllustration />
          <div className="summary-status-pill-container">
            <span className={`summary-status-pill ${isOnline ? "online" : "offline"}`}>
              <span className="summary-status-dot" />
              {statusLabel}
            </span>
          </div>
        </div>

        <div className="summary-identity-details">
          <div className="summary-title-row">
            <h1 className="summary-computer-name">{hostname}</h1>
            {labName && <span className="summary-lab-badge">{labName}</span>}
          </div>

          <div className="summary-specs-list">
            <div className="summary-spec-row">
              <span className="summary-spec-label">IP Address</span>
              <span className="summary-spec-colon">:</span>
              <span className="summary-spec-value">{ipAddress}</span>
            </div>
            <div className="summary-spec-row">
              <span className="summary-spec-label">MAC Address</span>
              <span className="summary-spec-colon">:</span>
              <span className="summary-spec-value summary-mac">{macAddress}</span>
            </div>
            <div className="summary-spec-row">
              <span className="summary-spec-label">Last Seen</span>
              <span className="summary-spec-colon">:</span>
              <span className="summary-spec-value">{lastSeenText}</span>
            </div>
            <div className="summary-spec-row">
              <span className="summary-spec-label">Agent Version</span>
              <span className="summary-spec-colon">:</span>
              <span className="summary-spec-value">{agentVersion}</span>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT SECTION: Metric Cards */}
      {activeTab === "software" ? (
        <SoftwareSummaryCards
          summary={softwareSummary}
          loading={softwareLoading}
          onScanNow={onScanNow}
          scanning={scanning}
        />
      ) : activeTab === "processes" ? (
        <ProcessSummaryCards
          summary={processSummary}
          loading={processLoading}
          onScanNow={onScanNow}
          scanning={scanning}
        />
      ) : activeTab === "commands" ? (
        <CommandSummaryCards
          summary={commandSummary}
          loading={commandLoading}
          onRunCommand={onRunCommand}
        />
      ) : (
        <div className="summary-metrics-grid">
          {/* 1. CPU Usage */}
          <div className="summary-metric-card metric-cpu">
            <div className="metric-header">
              <div className="metric-icon-box metric-icon-blue">
                <Icon type="chip" size={20} />
              </div>
              <div className="metric-text-group">
                <span className="metric-label">CPU Usage</span>
                <span className="metric-value">
                  {cpuPercent !== null ? `${cpuPercent}%` : "—"}
                </span>
              </div>
            </div>
            <div className="metric-visual">
              <MiniSparkline color="#2563eb" />
              <div className="metric-progress-track">
                <div
                  className="metric-progress-bar metric-bar-blue"
                  style={{ width: `${Math.min(100, Math.max(0, cpuPercent ?? 0))}%` }}
                />
              </div>
              {cpuPercent !== null && (
                <span className="metric-progress-number">{cpuPercent}%</span>
              )}
            </div>
          </div>

          {/* 2. RAM Usage */}
          <div className="summary-metric-card metric-ram">
            <div className="metric-header">
              <div className="metric-icon-box metric-icon-green">
                <Icon type="ram" size={20} />
              </div>
              <div className="metric-text-group">
                <span className="metric-label">RAM Usage</span>
                <span className="metric-value">
                  {ramPercent !== null ? `${ramPercent}%` : "—"}
                </span>
              </div>
            </div>
            <div className="metric-visual">
              <MiniSparkline color="#10b981" />
              <div className="metric-progress-track">
                <div
                  className="metric-progress-bar metric-bar-green"
                  style={{ width: `${Math.min(100, Math.max(0, ramPercent ?? 0))}%` }}
                />
              </div>
              {ramPercent !== null && (
                <span className="metric-progress-number">{ramPercent}%</span>
              )}
            </div>
          </div>

          {/* 3. Storage Usage */}
          <div className="summary-metric-card metric-storage">
            <div className="metric-header">
              <div className="metric-icon-box metric-icon-orange">
                <Icon type="storage" size={20} />
              </div>
              <div className="metric-text-group">
                <span className="metric-label">Storage Usage</span>
                <span className="metric-value">
                  {storagePercent !== null ? `${storagePercent}%` : "—"}
                </span>
              </div>
            </div>
            <div className="metric-visual">
              <MiniSparkline color="#f59e0b" />
              <div className="metric-progress-track">
                <div
                  className="metric-progress-bar metric-bar-orange"
                  style={{ width: `${Math.min(100, Math.max(0, storagePercent ?? 0))}%` }}
                />
              </div>
              {storagePercent !== null && (
                <span className="metric-progress-number">{storagePercent}%</span>
              )}
            </div>
          </div>

          {/* 4. System Uptime */}
          <div className="summary-metric-card metric-uptime">
            <div className="metric-header">
              <div className="metric-icon-box metric-icon-purple">
                <Icon type="clock" size={20} />
              </div>
              <div className="metric-text-group">
                <span className="metric-label">Uptime</span>
                <span className="metric-value metric-value-uptime">{uptimeText}</span>
              </div>
            </div>
            <div className="metric-visual">
              <MiniSparkline color="#8b5cf6" />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
