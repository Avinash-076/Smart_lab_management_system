import { useState, useEffect, useCallback } from "react";
import { getComputer, getComputerMetrics } from "../services/api";
import StatCard from "../components/StatCard";
import Icon from "../components/Icon";
import MetricChart from "../components/MetricChart";
import { useComputerWebSocket } from "../hooks/useComputerWebSocket";

function formatDateTime(dateStr) {
  if (!dateStr) return "Never";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return "Never";
  }
}

function ComputerDetails({ computer, onBack }) {
  const computerId = computer?.id || (typeof computer === "number" ? computer : null);

  const [details, setDetails] = useState(null);
  const [latestMetric, setLatestMetric] = useState(null);
  const [loading, setLoading] = useState(Boolean(computerId));
  const [error, setError] = useState("");

  // Historical metrics state
  const [timeRange, setTimeRange] = useState("1h"); // '1h' | '6h' | '24h'
  const [historicalMetrics, setHistoricalMetrics] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");

  const loadHistoricalMetrics = useCallback(
    async (range = timeRange) => {
      if (!computerId) return;

      try {
        setHistoryLoading(true);
        setHistoryError("");

        const now = Date.now();
        let startTime = new Date(now - 60 * 60 * 1000); // default 1h

        if (range === "6h") {
          startTime = new Date(now - 6 * 60 * 60 * 1000);
        } else if (range === "24h") {
          startTime = new Date(now - 24 * 60 * 60 * 1000);
        }

        const metricsData = await getComputerMetrics(computerId, {
          start_time: startTime,
          limit: 300,
        });

        if (Array.isArray(metricsData)) {
          setHistoricalMetrics(metricsData);
        } else {
          setHistoricalMetrics([]);
        }
      } catch (err) {
        console.error("Failed to load historical metrics:", err);
        setHistoryError(err.message || "Failed to load historical metrics.");
      } finally {
        setHistoryLoading(false);
      }
    },
    [computerId, timeRange]
  );

  const loadDetails = useCallback(async () => {
    if (!computerId) return;

    try {
      setLoading(true);
      setError("");

      const computerData = await getComputer(computerId);
      setDetails(computerData);

      try {
        const metricsData = await getComputerMetrics(computerId, 1);
        if (Array.isArray(metricsData) && metricsData.length > 0) {
          setLatestMetric(metricsData[0]);
        } else {
          setLatestMetric(null);
        }
      } catch (metricErr) {
        console.warn("Could not fetch latest metric for computer:", metricErr);
        setLatestMetric(null);
      }

      await loadHistoricalMetrics(timeRange);
    } catch (err) {
      console.error("Failed to load computer details:", err);
      setError(err.message || "Failed to load computer details.");
      setDetails(null);
      setLatestMetric(null);
    } finally {
      setLoading(false);
    }
  }, [computerId, timeRange, loadHistoricalMetrics]);

  useEffect(() => {
    if (!computerId) {
      return;
    }
    let ignore = false;
    async function init() {
      try {
        setError("");
        const computerData = await getComputer(computerId);
        if (ignore) return;
        setDetails(computerData);

        try {
          const metricsData = await getComputerMetrics(computerId, 1);
          if (ignore) return;
          if (Array.isArray(metricsData) && metricsData.length > 0) {
            setLatestMetric(metricsData[0]);
          } else {
            setLatestMetric(null);
          }
        } catch {
          if (!ignore) setLatestMetric(null);
        }

        if (!ignore) {
          await loadHistoricalMetrics(timeRange);
        }
      } catch (err) {
        if (!ignore) {
          setError(err.message || "Failed to load computer details.");
          setDetails(null);
          setLatestMetric(null);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    init();

    return () => {
      ignore = true;
    };
  }, [computerId, timeRange, loadHistoricalMetrics]);

  // WebSocket Live Updates Handler (V2.3)
  const handleLiveMetric = useCallback((metricMsg) => {
    setLatestMetric({
      computer_id: metricMsg.computer_id,
      cpu_usage: metricMsg.cpu_usage,
      ram_usage: metricMsg.ram_usage,
      disk_usage: metricMsg.disk_usage,
      network_sent: metricMsg.network_sent,
      network_received: metricMsg.network_received,
      recorded_at: metricMsg.recorded_at,
    });

    setHistoricalMetrics((prev) => {
      if (!Array.isArray(prev)) return prev;
      const isDuplicate = prev.some(
        (m) => m.recorded_at === metricMsg.recorded_at
      );
      if (isDuplicate) return prev;
      const newPoint = {
        id: `live-${Date.now()}`,
        computer_id: metricMsg.computer_id,
        cpu_usage: metricMsg.cpu_usage,
        ram_usage: metricMsg.ram_usage,
        disk_usage: metricMsg.disk_usage,
        network_sent: metricMsg.network_sent,
        network_received: metricMsg.network_received,
        recorded_at: metricMsg.recorded_at,
      };
      return [newPoint, ...prev].slice(0, 300);
    });
  }, []);

  const handleLiveStatus = useCallback((statusMsg) => {
    setDetails((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        status: statusMsg.status || prev.status,
        last_seen: statusMsg.last_seen || prev.last_seen || new Date().toISOString(),
      };
    });
  }, []);

  const { wsStatus } = useComputerWebSocket(computerId, {
    onMetricUpdate: handleLiveMetric,
    onStatusUpdate: handleLiveStatus,
  });

  const handleTimeRangeChange = (newRange) => {
    setTimeRange(newRange);
    loadHistoricalMetrics(newRange);
  };

  /* =====================================================
     NO COMPUTER SELECTED
  ===================================================== */
  if (!computerId) {
    return (
      <div className="content">
        <div className="page-top">
          <div>
            <h2>Computer Details</h2>
            <p>
              Select a computer from the Computer List to view its complete
              information.
            </p>
          </div>
        </div>

        <div className="table-card">
          <div className="empty-state" style={{ padding: "50px 20px" }}>
            <Icon type="details" size={40} />
            <h3>No computer selected</h3>
            <p>
              Open the Computer List and click the view button beside a
              computer.
            </p>
            <button
              className="refresh"
              onClick={onBack}
              style={{ marginTop: "15px", display: "inline-flex" }}
            >
              ← Go to Computer List
            </button>
          </div>
        </div>
      </div>
    );
  }

  /* =====================================================
     LOADING STATE
  ===================================================== */
  if (loading && !details) {
    return (
      <div className="content">
        <div className="page-top">
          <div>
            <h2>Computer Details</h2>
            <p>Fetching real computer information from backend...</p>
          </div>
          <button className="refresh" onClick={onBack}>
            ← Back to Computer List
          </button>
        </div>

        <div className="table-card">
          <div className="empty-state" style={{ padding: "50px 20px" }}>
            <Icon type="refresh" size={40} />
            <h3>Loading computer details...</h3>
            <p>Retrieving computer record and latest metrics from server.</p>
          </div>
        </div>
      </div>
    );
  }

  /* =====================================================
     ERROR STATE (e.g. 404 / Network error)
  ===================================================== */
  if (error && !details) {
    return (
      <div className="content">
        <div className="page-top">
          <div>
            <h2>Computer Details</h2>
            <p>Error retrieving computer information.</p>
          </div>
          <button className="refresh" onClick={onBack}>
            ← Back to Computer List
          </button>
        </div>

        <div className="table-card">
          <div className="empty-state" style={{ padding: "50px 20px" }}>
            <Icon type="details" size={40} />
            <h3 style={{ color: "#dc2626" }}>Failed to load computer</h3>
            <p>{error}</p>
            <div
              style={{
                marginTop: "15px",
                display: "flex",
                gap: "10px",
                justifyContent: "center",
              }}
            >
              <button className="refresh" onClick={loadDetails}>
                <Icon type="refresh" size={16} />
                Try Again
              </button>
              <button className="export" onClick={onBack}>
                ← Back to Computer List
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* =====================================================
     REAL BACKEND VALUES
  ===================================================== */
  const hostname = details.hostname || `PC-${details.id}`;
  const ip = details.ip_address || "—";
  const mac = details.mac_address || "—";
  const osName = details.os_name || "—";
  const osVersion = details.os_version || "";
  const fullOs = `${osName} ${osVersion}`.trim();
  const status = (details.status || "offline").toLowerCase();
  const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);
  const isWindows = fullOs.toLowerCase().includes("windows");

  // Current Metrics (Distinguish real 0% from null/Unavailable!)
  const hasCpu = latestMetric && typeof latestMetric.cpu_usage === "number";
  const hasRam = latestMetric && typeof latestMetric.ram_usage === "number";
  const hasDisk = latestMetric && typeof latestMetric.disk_usage === "number";

  const cpuText = hasCpu
    ? `${latestMetric.cpu_usage.toFixed(1)}%`
    : "Unavailable";
  const ramText = hasRam
    ? `${latestMetric.ram_usage.toFixed(1)}%`
    : "Unavailable";
  const diskText = hasDisk
    ? `${latestMetric.disk_usage.toFixed(1)}%`
    : "Unavailable";

  const networkSentText =
    latestMetric && typeof latestMetric.network_sent === "number"
      ? `${latestMetric.network_sent.toFixed(1)} KB/s`
      : "Unavailable";
  const networkRecvText =
    latestMetric && typeof latestMetric.network_received === "number"
      ? `${latestMetric.network_received.toFixed(1)} KB/s`
      : "Unavailable";

  return (
    <div className="content">
      {/* =================================================
          PAGE HEADER
      ================================================= */}
      <div className="page-top">
        <div>
          <h2>Computer Details</h2>
          <p>System specifications and telemetry for {hostname}.</p>
        </div>

        <div className="top-actions">
          <button
            className="export"
            onClick={loadDetails}
            disabled={loading}
            title="Refresh computer information from backend"
          >
            <Icon type="refresh" size={16} />
            Refresh
          </button>

          <button className="refresh" onClick={onBack}>
            ← Back to Computer List
          </button>
        </div>
      </div>

      {/* =================================================
          SELECTED COMPUTER HEADER
      ================================================= */}
      <div className="details-computer-header">
        <div className="details-computer-title">
          <div className="details-computer-icon">
            <Icon type={isWindows ? "windows" : "computer"} size={30} />
          </div>

          <div>
            <h2>{hostname}</h2>
            <p>
              ID #{details.id} • {ip} • {fullOs}
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span className={`ws-badge ws-${wsStatus}`}>
            <i />
            {wsStatus === "connected" && "● Live"}
            {wsStatus === "connecting" && "↻ Connecting"}
            {wsStatus === "reconnecting" && "↻ Reconnecting"}
            {wsStatus === "disconnected" && "○ Disconnected"}
          </span>

          <span className={`status ${status}`}>
            <i />
            {statusLabel}
          </span>
        </div>
      </div>

      {/* =================================================
          CURRENT METRIC STAT CARDS
      ================================================= */}
      <div className="cards">
        <StatCard
          icon="computer"
          title="CPU Usage"
          number={cpuText}
          footer={
            hasCpu ? "Current processor usage" : "No metric data recorded"
          }
          type="blue"
        />

        <StatCard
          icon="computer"
          title="RAM Usage"
          number={ramText}
          footer={hasRam ? "Current memory usage" : "No metric data recorded"}
          type="green"
        />

        <StatCard
          icon="computer"
          title="Disk Usage"
          number={diskText}
          footer={hasDisk ? "Storage utilization" : "No metric data recorded"}
          type="orange"
        />

        <StatCard
          icon={isWindows ? "windows" : "computer"}
          title="Operating System"
          number={osName}
          footer={osVersion || "Standard"}
          type="purple"
        />
      </div>

      {/* =================================================
          INFORMATION GRID
      ================================================= */}
      <div className="details-sections">
        {/* SYSTEM INFORMATION */}
        <div className="details-panel">
          <div className="details-panel-header">
            <h3>System Information</h3>
          </div>

          <div className="details-info-grid">
            <div>
              <span>Computer Name</span>
              <strong>{hostname}</strong>
            </div>

            <div>
              <span>Computer ID</span>
              <strong>#{details.id}</strong>
            </div>

            <div>
              <span>Operating System</span>
              <strong>{fullOs || "—"}</strong>
            </div>

            <div>
              <span>System Status</span>
              <strong>{statusLabel}</strong>
            </div>

            <div>
              <span>Last Seen</span>
              <strong>{formatDateTime(details.last_seen)}</strong>
            </div>

            <div>
              <span>Registered At</span>
              <strong>{formatDateTime(details.registered_at)}</strong>
            </div>
          </div>
        </div>

        {/* NETWORK INFORMATION */}
        <div className="details-panel">
          <div className="details-panel-header">
            <h3>Network Information</h3>
          </div>

          <div className="details-info-grid">
            <div>
              <span>IP Address</span>
              <strong>{ip}</strong>
            </div>

            <div>
              <span>MAC Address</span>
              <strong>
                <code style={{ fontSize: "13px", color: "#1e293b" }}>{mac}</code>
              </strong>
            </div>

            <div>
              <span>Network Sent</span>
              <strong>{networkSentText}</strong>
            </div>

            <div>
              <span>Network Received</span>
              <strong>{networkRecvText}</strong>
            </div>

            <div>
              <span>Connection Status</span>
              <strong>{statusLabel}</strong>
            </div>

            <div>
              <span>Last Heartbeat</span>
              <strong>{formatDateTime(details.last_seen)}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* =================================================
          CURRENT HARDWARE UTILIZATION
      ================================================= */}
      <div className="details-panel disk-panel" style={{ marginTop: "20px" }}>
        <div className="details-panel-header">
          <h3>Current Hardware Utilization</h3>
        </div>

        {latestMetric ? (
          <div style={{ padding: "20px 22px" }}>
            {/* CPU Bar */}
            <div style={{ marginBottom: "18px" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "6px",
                  fontSize: "13px",
                }}
              >
                <span style={{ color: "#68748b" }}>Current CPU Load</span>
                <strong style={{ color: "#172343" }}>{cpuText}</strong>
              </div>
              <div className="large-disk-track" style={{ height: "9px" }}>
                <div
                  className="large-disk-fill"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(0, latestMetric.cpu_usage)
                    )}%`,
                    background: "#0962df",
                  }}
                />
              </div>
            </div>

            {/* RAM Bar */}
            <div style={{ marginBottom: "18px" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "6px",
                  fontSize: "13px",
                }}
              >
                <span style={{ color: "#68748b" }}>Current RAM Utilization</span>
                <strong style={{ color: "#172343" }}>{ramText}</strong>
              </div>
              <div className="large-disk-track" style={{ height: "9px" }}>
                <div
                  className="large-disk-fill"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(0, latestMetric.ram_usage)
                    )}%`,
                    background: "#159b55",
                  }}
                />
              </div>
            </div>

            {/* Disk Bar */}
            <div style={{ marginBottom: "18px" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  marginBottom: "6px",
                  fontSize: "13px",
                }}
              >
                <span style={{ color: "#68748b" }}>Current Disk Utilization</span>
                <strong style={{ color: "#172343" }}>{diskText}</strong>
              </div>
              <div className="large-disk-track" style={{ height: "9px" }}>
                <div
                  className="large-disk-fill"
                  style={{
                    width: `${Math.min(
                      100,
                      Math.max(0, latestMetric.disk_usage)
                    )}%`,
                    background: "#f39b13",
                  }}
                />
              </div>
            </div>

            <div
              style={{
                marginTop: "12px",
                fontSize: "11px",
                color: "#718099",
              }}
            >
              Latest report timestamp: {formatDateTime(latestMetric.recorded_at)}
            </div>
          </div>
        ) : (
          <div
            style={{
              padding: "30px 20px",
              textAlign: "center",
              color: "#68748b",
            }}
          >
            <p style={{ margin: 0, fontSize: "13px" }}>
              No telemetry reports have been recorded for this computer yet.
            </p>
          </div>
        )}
      </div>

      {/* =================================================
          HISTORICAL METRICS & CHARTS (V2.2)
      ================================================= */}
      <MetricChart
        metrics={historicalMetrics}
        loading={historyLoading}
        error={historyError}
        timeRange={timeRange}
        onTimeRangeChange={handleTimeRangeChange}
        onRefresh={() => loadHistoricalMetrics(timeRange)}
      />
    </div>
  );
}

export default ComputerDetails;