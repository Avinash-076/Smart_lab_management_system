import { useState, useEffect, useCallback } from "react";
import {
  getComputer,
  getComputerMetrics,
  getComputerSoftware,
  getComputerProcesses,
  getComputerUsage,
  issueCommand,
  getComputerCommands,
  cancelCommand,
} from "../services/api";
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

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return "0s";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) {
    return `${h}h ${m > 0 ? `${m}m ` : ""}${s > 0 ? `${s}s` : ""}`.trim();
  }
  if (m > 0) {
    return `${m}m ${s > 0 ? `${s}s` : ""}`.trim();
  }
  return `${s}s`;
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

  // Software inventory state (V3.1)
  const [softwareList, setSoftwareList] = useState([]);
  const [softwareLoading, setSoftwareLoading] = useState(false);
  const [softwareError, setSoftwareError] = useState("");
  const [softwareSearch, setSoftwareSearch] = useState("");

  // Running processes state (V3.2)
  const [processList, setProcessList] = useState([]);
  const [processLoading, setProcessLoading] = useState(false);
  const [processError, setProcessError] = useState("");
  const [processSearch, setProcessSearch] = useState("");

  // Application usage history state (V3.3)
  const [usageList, setUsageList] = useState([]);
  const [usageLoading, setUsageLoading] = useState(false);
  const [usageError, setUsageError] = useState("");
  const [usageSearch, setUsageSearch] = useState("");
  const [usageTimeRange, setUsageTimeRange] = useState("all"); // '1h' | '6h' | '24h' | 'all'

  // Remote command management state (V5.1)
  const [commandList, setCommandList] = useState([]);
  const [commandLoading, setCommandLoading] = useState(false);
  const [commandError, setCommandError] = useState("");
  const [commandSearch, setCommandSearch] = useState("");
  const [commandFilter, setCommandFilter] = useState("all"); // 'all' | 'pending' | 'delivered' | 'executed' | 'failed' | 'cancelled'
  const [actionLoading, setActionLoading] = useState(false);
  const [actionToast, setActionToast] = useState(null); // { type: 'success' | 'error', text: string }
  const [commandModal, setCommandModal] = useState({
    open: false,
    type: "", // 'message' | 'lock' | 'restart' | 'shutdown'
    payload: "",
  });

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

  const loadSoftware = useCallback(async () => {
    if (!computerId) return;
    try {
      setSoftwareLoading(true);
      setSoftwareError("");
      const data = await getComputerSoftware(computerId);
      if (Array.isArray(data)) {
        setSoftwareList(data);
      } else {
        setSoftwareList([]);
      }
    } catch (err) {
      console.warn("Could not fetch software inventory:", err);
      setSoftwareError(err.message || "Failed to load software inventory.");
      setSoftwareList([]);
    } finally {
      setSoftwareLoading(false);
    }
  }, [computerId]);

  const loadProcesses = useCallback(async () => {
    if (!computerId) return;
    try {
      setProcessLoading(true);
      setProcessError("");
      const data = await getComputerProcesses(computerId);
      if (Array.isArray(data)) {
        setProcessList(data);
      } else {
        setProcessList([]);
      }
    } catch (err) {
      console.warn("Could not fetch running processes:", err);
      setProcessError(err.message || "Failed to load running processes.");
      setProcessList([]);
    } finally {
      setProcessLoading(false);
    }
  }, [computerId]);

  const loadUsage = useCallback(
    async (range = usageTimeRange) => {
      if (!computerId) return;
      try {
        setUsageLoading(true);
        setUsageError("");
        let startTime = undefined;
        const now = Date.now();
        if (range === "1h") {
          startTime = new Date(now - 60 * 60 * 1000);
        } else if (range === "6h") {
          startTime = new Date(now - 6 * 60 * 60 * 1000);
        } else if (range === "24h") {
          startTime = new Date(now - 24 * 60 * 60 * 1000);
        }

        const data = await getComputerUsage(computerId, {
          start_time: startTime,
          limit: 200,
        });

        if (Array.isArray(data)) {
          setUsageList(data);
        } else {
          setUsageList([]);
        }
      } catch (err) {
        console.warn("Could not fetch usage history:", err);
        setUsageError(err.message || "Failed to load usage history.");
        setUsageList([]);
      } finally {
        setUsageLoading(false);
      }
    },
    [computerId, usageTimeRange]
  );

  const loadCommands = useCallback(async () => {
    if (!computerId) return;

    try {
      setCommandLoading(true);
      setCommandError("");

      const data = await getComputerCommands(computerId, { limit: 100 });
      if (Array.isArray(data)) {
        setCommandList(data);
      } else {
        setCommandList([]);
      }
    } catch (err) {
      console.warn("Could not fetch remote commands:", err);
      setCommandError(err.message || "Failed to load command history.");
      setCommandList([]);
    } finally {
      setCommandLoading(false);
    }
  }, [computerId]);

  const handleOpenCommandModal = (type) => {
    setCommandModal({
      open: true,
      type,
      payload: "",
    });
  };

  const handleCloseCommandModal = () => {
    setCommandModal({ open: false, type: "", payload: "" });
  };

  const handleSubmitCommand = async () => {
    if (!computerId || !commandModal.type) return;

    if (commandModal.type === "message" && !commandModal.payload.trim()) {
      setActionToast({
        type: "error",
        text: "Please provide a notice message before sending.",
      });
      return;
    }

    try {
      setActionLoading(true);
      const payloadStr =
        commandModal.type === "message"
          ? commandModal.payload.trim().slice(0, 255)
          : null;

      const newCmd = await issueCommand(computerId, {
        command_type: commandModal.type,
        payload: payloadStr,
      });

      handleCloseCommandModal();
      setActionToast({
        type: "success",
        text: `Command "${commandModal.type.toUpperCase()}" dispatched successfully (Status: ${newCmd.status}).`,
      });
      await loadCommands();
    } catch (err) {
      console.error("Failed to issue command:", err);
      setActionToast({
        type: "error",
        text: err.message || "Failed to dispatch remote command.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelCommand = async (cmdId) => {
    try {
      setActionLoading(true);
      await cancelCommand(cmdId);
      setActionToast({
        type: "success",
        text: `Command #${cmdId} cancelled successfully.`,
      });
      await loadCommands();
    } catch (err) {
      console.error("Failed to cancel command:", err);
      setActionToast({
        type: "error",
        text: err.message || "Failed to cancel command.",
      });
    } finally {
      setActionLoading(false);
    }
  };

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
      await loadCommands();
      await loadSoftware();
      await loadProcesses();
      await loadUsage(usageTimeRange);
    } catch (err) {
      console.error("Failed to load computer details:", err);
      setError(err.message || "Failed to load computer details.");
      setDetails(null);
      setLatestMetric(null);
    } finally {
      setLoading(false);
    }
  }, [
    computerId,
    timeRange,
    loadHistoricalMetrics,
    loadCommands,
    loadSoftware,
    loadProcesses,
    loadUsage,
    usageTimeRange,
  ]);

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

        try {
          const sw = await getComputerSoftware(computerId);
          if (!ignore) {
            setSoftwareList(Array.isArray(sw) ? sw : []);
          }
        } catch (swErr) {
          if (!ignore) {
            setSoftwareError(swErr.message || "Failed to load software inventory.");
            setSoftwareList([]);
          }
        }

        try {
          const procs = await getComputerProcesses(computerId);
          if (!ignore) {
            setProcessList(Array.isArray(procs) ? procs : []);
          }
        } catch (procErr) {
          if (!ignore) {
            setProcessError(procErr.message || "Failed to load running processes.");
            setProcessList([]);
          }
        }

        try {
          const usg = await getComputerUsage(computerId, { limit: 200 });
          if (!ignore) {
            setUsageList(Array.isArray(usg) ? usg : []);
          }
        } catch (usgErr) {
          if (!ignore) {
            setUsageError(usgErr.message || "Failed to load usage history.");
            setUsageList([]);
          }
        }

        try {
          const cmds = await getComputerCommands(computerId, { limit: 100 });
          if (!ignore) {
            setCommandList(Array.isArray(cmds) ? cmds : []);
          }
        } catch (cmdErr) {
          if (!ignore) {
            setCommandError(cmdErr.message || "Failed to load command history.");
            setCommandList([]);
          }
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

  const filteredSoftware = softwareList.filter((item) => {
    if (!softwareSearch.trim()) return true;
    const q = softwareSearch.toLowerCase();
    return (
      (item.name && item.name.toLowerCase().includes(q)) ||
      (item.publisher && item.publisher.toLowerCase().includes(q)) ||
      (item.version && item.version.toLowerCase().includes(q))
    );
  });

  const filteredProcesses = processList.filter((item) => {
    if (!processSearch.trim()) return true;
    const q = processSearch.toLowerCase();
    return (
      (item.name && item.name.toLowerCase().includes(q)) ||
      (item.pid !== undefined && item.pid !== null && String(item.pid).includes(q)) ||
      (item.status && item.status.toLowerCase().includes(q))
    );
  });

  const handleUsageTimeRangeChange = (range) => {
    setUsageTimeRange(range);
    loadUsage(range);
  };

  const filteredUsage = usageList.filter((item) => {
    if (!usageSearch.trim()) return true;
    const q = usageSearch.toLowerCase();
    return item.application_name && item.application_name.toLowerCase().includes(q);
  });

  const filteredCommands = commandList.filter((cmd) => {
    const matchesStatus =
      commandFilter === "all" ||
      cmd.status?.toLowerCase() === commandFilter.toLowerCase();
    const searchLower = commandSearch.toLowerCase().trim();
    const matchesSearch =
      !searchLower ||
      cmd.command_type?.toLowerCase().includes(searchLower) ||
      (cmd.payload && cmd.payload.toLowerCase().includes(searchLower)) ||
      (cmd.result?.message &&
        cmd.result.message.toLowerCase().includes(searchLower)) ||
      String(cmd.id).includes(searchLower);
    return matchesStatus && matchesSearch;
  });

  const totalUsageSeconds = filteredUsage.reduce(
    (acc, curr) => acc + (curr.duration_seconds || 0),
    0
  );

  const appDurationMap = {};
  filteredUsage.forEach((item) => {
    const name = item.application_name || "Unknown";
    appDurationMap[name] = (appDurationMap[name] || 0) + (item.duration_seconds || 0);
  });

  const topApplications = Object.entries(appDurationMap)
    .map(([name, duration]) => ({ name, duration }))
    .sort((a, b) => b.duration - a.duration)
    .slice(0, 5);

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

      {/* =================================================
          REMOTE COMMAND MANAGEMENT (V5.1)
      ================================================= */}
      <div className="table-card" style={{ marginTop: "24px" }}>
        {/* Action Feedback Toast */}
        {actionToast && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "12px 20px",
              background:
                actionToast.type === "success"
                  ? "rgba(16, 185, 129, 0.12)"
                  : "rgba(239, 68, 68, 0.12)",
              borderBottom: `1px solid ${
                actionToast.type === "success"
                  ? "rgba(16, 185, 129, 0.3)"
                  : "rgba(239, 68, 68, 0.3)"
              }`,
              color: actionToast.type === "success" ? "#065f46" : "#991b1b",
              fontSize: "13px",
              fontWeight: 500,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span>{actionToast.type === "success" ? "✓" : "⚠"}</span>
              <span>{actionToast.text}</span>
            </div>
            <button
              type="button"
              onClick={() => setActionToast(null)}
              style={{
                background: "transparent",
                border: "none",
                cursor: "pointer",
                color: "inherit",
                fontSize: "16px",
                padding: "0 4px",
              }}
              title="Dismiss notice"
            >
              ×
            </button>
          </div>
        )}

        {/* Section Header */}
        <div
          className="page-section-header"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "18px 22px",
            borderBottom: "1px solid #edf0f4",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: "16px", color: "#07144a" }}>
              Remote Command Management
            </h3>
            <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#68748b" }}>
              Dispatch administrative operations and monitor agent execution results.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            {/* Status Filter Tabs */}
            <div className="range-selector" style={{ display: "flex", gap: "4px" }}>
              {["all", "pending", "delivered", "executed", "failed", "cancelled"].map((st) => (
                <button
                  key={st}
                  type="button"
                  className={commandFilter === st ? "active" : ""}
                  onClick={() => setCommandFilter(st)}
                  style={{
                    padding: "4px 10px",
                    fontSize: "12px",
                    borderRadius: "4px",
                    border: commandFilter === st ? "1px solid #0962df" : "1px solid #e2e8f0",
                    background: commandFilter === st ? "#0962df" : "#ffffff",
                    color: commandFilter === st ? "#ffffff" : "#475569",
                    cursor: "pointer",
                    fontWeight: commandFilter === st ? 600 : 400,
                  }}
                >
                  {st.charAt(0).toUpperCase() + st.slice(1)}
                </button>
              ))}
            </div>

            <div className="table-search" style={{ width: "220px", height: "36px" }}>
              <input
                value={commandSearch}
                onChange={(e) => setCommandSearch(e.target.value)}
                placeholder="Search commands, results..."
                style={{ fontSize: "12px" }}
              />
              <Icon type="search" size={16} />
            </div>

            <button
              className="export"
              onClick={loadCommands}
              disabled={commandLoading}
              title="Refresh remote command queue from server"
              style={{ width: "auto", height: "36px", padding: "0 14px" }}
            >
              <Icon type="refresh" size={14} />
              Refresh
            </button>
          </div>
        </div>

        {/* Action Buttons Deck */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "14px",
            padding: "18px 22px",
            background: "#f8fafc",
            borderBottom: "1px solid #edf0f4",
          }}
        >
          {/* Action 1: Send Message */}
          <button
            type="button"
            onClick={() => handleOpenCommandModal("message")}
            disabled={actionLoading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "14px 16px",
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              cursor: "pointer",
              textAlign: "left",
              transition: "all 0.15s ease",
            }}
          >
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "rgba(9, 98, 223, 0.1)",
                color: "#0962df",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Icon type="details" size={18} />
            </div>
            <div>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a" }}>
                Send Notice
              </div>
              <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                Broadcast message on desktop
              </div>
            </div>
          </button>

          {/* Action 2: Lock Workstation */}
          <button
            type="button"
            onClick={() => handleOpenCommandModal("lock")}
            disabled={actionLoading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "14px 16px",
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              cursor: "pointer",
              textAlign: "left",
              transition: "all 0.15s ease",
            }}
          >
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "rgba(245, 158, 11, 0.1)",
                color: "#d97706",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Icon type="settings" size={18} />
            </div>
            <div>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a" }}>
                Lock Workstation
              </div>
              <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                Lock active user session
              </div>
            </div>
          </button>

          {/* Action 3: Restart System */}
          <button
            type="button"
            onClick={() => handleOpenCommandModal("restart")}
            disabled={actionLoading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "14px 16px",
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              cursor: "pointer",
              textAlign: "left",
              transition: "all 0.15s ease",
            }}
          >
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "rgba(249, 115, 22, 0.1)",
                color: "#ea580c",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Icon type="refresh" size={18} />
            </div>
            <div>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a" }}>
                Restart System
              </div>
              <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                Scheduled 5s reboot
              </div>
            </div>
          </button>

          {/* Action 4: Shutdown System */}
          <button
            type="button"
            onClick={() => handleOpenCommandModal("shutdown")}
            disabled={actionLoading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "12px",
              padding: "14px 16px",
              background: "#ffffff",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              cursor: "pointer",
              textAlign: "left",
              transition: "all 0.15s ease",
            }}
          >
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "rgba(239, 68, 68, 0.1)",
                color: "#dc2626",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Icon type="logout" size={18} />
            </div>
            <div>
              <div style={{ fontSize: "13px", fontWeight: 600, color: "#0f172a" }}>
                Shutdown System
              </div>
              <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
                Scheduled 5s power off
              </div>
            </div>
          </button>
        </div>

        {/* Command History Table */}
        {commandLoading && commandList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <Icon type="refresh" size={32} />
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>
              Loading command history...
            </h4>
            <p style={{ margin: 0, fontSize: "13px", color: "#68748b" }}>
              Fetching command dispatch records and execution results from server.
            </p>
          </div>
        ) : commandError && commandList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#dc2626" }}>
              Failed to load remote commands
            </h4>
            <p style={{ margin: "0 0 12px", fontSize: "13px", color: "#68748b" }}>
              {commandError}
            </p>
            <button
              className="refresh"
              onClick={loadCommands}
              style={{ display: "inline-flex" }}
            >
              Try Again
            </button>
          </div>
        ) : commandList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <Icon type="details" size={36} />
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>
              No remote commands issued yet
            </h4>
            <p style={{ margin: 0, fontSize: "13px", color: "#68748b" }}>
              Use the action buttons above to dispatch remote commands to this computer.
            </p>
          </div>
        ) : filteredCommands.length === 0 ? (
          <div className="empty-state" style={{ padding: "30px 20px" }}>
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>
              No matching commands found
            </h4>
            <p style={{ margin: "0 0 12px", fontSize: "13px", color: "#68748b" }}>
              No commands match current filter &quot;{commandFilter}&quot; or search query.
            </p>
            <button
              className="export"
              onClick={() => {
                setCommandFilter("all");
                setCommandSearch("");
              }}
              style={{ display: "inline-flex" }}
            >
              Reset Filters
            </button>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th style={{ width: "18%" }}>Command</th>
                  <th style={{ width: "25%" }}>Parameters / Payload</th>
                  <th style={{ width: "18%" }}>Issued Timestamp</th>
                  <th style={{ width: "15%" }}>Status</th>
                  <th style={{ width: "16%" }}>Agent Result</th>
                  <th style={{ width: "8%", textAlign: "center" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredCommands.map((cmd) => {
                  const cmdType = (cmd.command_type || "").toUpperCase();
                  const isPending = cmd.status === "pending";
                  const isDelivered = cmd.status === "delivered";
                  const isExecuted = cmd.status === "executed";
                  const isFailed = cmd.status === "failed";

                  const statusBadgeBg = isPending
                    ? "rgba(245, 158, 11, 0.12)"
                    : isDelivered
                    ? "rgba(14, 165, 233, 0.12)"
                    : isExecuted
                    ? "rgba(16, 185, 129, 0.12)"
                    : isFailed
                    ? "rgba(239, 68, 68, 0.12)"
                    : "rgba(100, 116, 139, 0.12)";

                  const statusBadgeColor = isPending
                    ? "#d97706"
                    : isDelivered
                    ? "#0284c7"
                    : isExecuted
                    ? "#059669"
                    : isFailed
                    ? "#dc2626"
                    : "#64748b";

                  return (
                    <tr key={cmd.id}>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span
                            style={{
                              padding: "3px 8px",
                              borderRadius: "6px",
                              fontSize: "11px",
                              fontWeight: 700,
                              background:
                                cmd.command_type === "shutdown"
                                  ? "#fee2e2"
                                  : cmd.command_type === "restart"
                                  ? "#ffedd5"
                                  : cmd.command_type === "lock"
                                  ? "#fef3c7"
                                  : "#e0f2fe",
                              color:
                                cmd.command_type === "shutdown"
                                  ? "#b91c1c"
                                  : cmd.command_type === "restart"
                                  ? "#c2410c"
                                  : cmd.command_type === "lock"
                                  ? "#b45309"
                                  : "#0369a1",
                            }}
                          >
                            {cmdType}
                          </span>
                          <span style={{ fontSize: "11px", color: "#94a3b8" }}>
                            #{cmd.id}
                          </span>
                        </div>
                      </td>

                      <td style={{ fontSize: "12px", color: "#334155" }}>
                        {cmd.payload ? (
                          <span
                            style={{
                              fontFamily: "monospace",
                              background: "#f1f5f9",
                              padding: "2px 6px",
                              borderRadius: "4px",
                              fontSize: "12px",
                              wordBreak: "break-all",
                            }}
                          >
                            {cmd.payload}
                          </span>
                        ) : (
                          <span style={{ color: "#94a3b8" }}>—</span>
                        )}
                      </td>

                      <td style={{ fontSize: "12px", color: "#475569" }}>
                        {formatDateTime(cmd.created_at)}
                      </td>

                      <td>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "3px 8px",
                            borderRadius: "12px",
                            fontSize: "11px",
                            fontWeight: 600,
                            background: statusBadgeBg,
                            color: statusBadgeColor,
                          }}
                        >
                          <span
                            style={{
                              width: "6px",
                              height: "6px",
                              borderRadius: "50%",
                              background: statusBadgeColor,
                            }}
                          />
                          {cmd.status}
                        </span>
                      </td>

                      <td style={{ fontSize: "12px" }}>
                        {cmd.result ? (
                          <div>
                            <div
                              style={{
                                color: cmd.result.success ? "#16a34a" : "#dc2626",
                                fontWeight: 500,
                              }}
                            >
                              {cmd.result.success ? "✓ Succeeded" : "✕ Failed"}
                            </div>
                            {cmd.result.message && (
                              <div
                                style={{
                                  fontSize: "11px",
                                  color: "#64748b",
                                  marginTop: "2px",
                                }}
                              >
                                {cmd.result.message}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span style={{ color: "#94a3b8" }}>
                            {isPending ? "Waiting for agent..." : isDelivered ? "Dispatched" : "—"}
                          </span>
                        )}
                      </td>

                      <td style={{ textAlign: "center" }}>
                        {isPending ? (
                          <button
                            type="button"
                            onClick={() => handleCancelCommand(cmd.id)}
                            disabled={actionLoading}
                            style={{
                              padding: "4px 8px",
                              fontSize: "11px",
                              fontWeight: 600,
                              borderRadius: "4px",
                              border: "1px solid #fca5a5",
                              background: "#fef2f2",
                              color: "#dc2626",
                              cursor: "pointer",
                            }}
                            title="Cancel pending command"
                          >
                            Cancel
                          </button>
                        ) : (
                          <span style={{ color: "#cbd5e1" }}>—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {commandList.length > 0 && (
          <div
            style={{
              padding: "12px 20px",
              fontSize: "12px",
              color: "#64748b",
              borderTop: "1px solid #edf0f4",
              background: "#f8fafc",
            }}
          >
            Showing <strong>{filteredCommands.length}</strong> of{" "}
            <strong>{commandList.length}</strong> remote command records
          </div>
        )}
      </div>

      {/* Action / Safety Confirmation Modal */}
      {commandModal.open && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
          onClick={handleCloseCommandModal}
        >
          <div
            style={{
              background: "#ffffff",
              borderRadius: "12px",
              maxWidth: "480px",
              width: "100%",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)",
              overflow: "hidden",
              border: "1px solid #e2e8f0",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: "18px 22px",
                borderBottom: "1px solid #edf0f4",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background:
                  commandModal.type === "shutdown"
                    ? "#fef2f2"
                    : commandModal.type === "restart"
                    ? "#fff7ed"
                    : "#f8fafc",
              }}
            >
              <div>
                <h3
                  style={{
                    margin: 0,
                    fontSize: "16px",
                    color:
                      commandModal.type === "shutdown"
                        ? "#b91c1c"
                        : commandModal.type === "restart"
                        ? "#c2410c"
                        : "#0f172a",
                  }}
                >
                  {commandModal.type === "message"
                    ? "Broadcast Message Notice"
                    : commandModal.type === "lock"
                    ? "Confirm Workstation Lock"
                    : commandModal.type === "restart"
                    ? "Confirm System Restart"
                    : "Confirm System Shutdown"}
                </h3>
                <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#64748b" }}>
                  Target: <strong>{hostname}</strong> ({ip})
                </p>
              </div>

              <button
                type="button"
                onClick={handleCloseCommandModal}
                style={{
                  background: "transparent",
                  border: "none",
                  fontSize: "20px",
                  color: "#64748b",
                  cursor: "pointer",
                }}
              >
                ×
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: "20px 22px" }}>
              {commandModal.type === "message" ? (
                <div>
                  <label
                    style={{
                      display: "block",
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "#334155",
                      marginBottom: "6px",
                    }}
                  >
                    Administrative Notice Message:
                  </label>
                  <textarea
                    rows={4}
                    value={commandModal.payload}
                    onChange={(e) =>
                      setCommandModal((prev) => ({
                        ...prev,
                        payload: e.target.value.slice(0, 255),
                      }))
                    }
                    placeholder="e.g. Scheduled lab maintenance will begin in 10 minutes. Please save all work."
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: "6px",
                      border: "1px solid #cbd5e1",
                      fontSize: "13px",
                      boxSizing: "border-box",
                      fontFamily: "inherit",
                      resize: "vertical",
                    }}
                  />
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: "11px",
                      color: "#64748b",
                      marginTop: "4px",
                    }}
                  >
                    <span>Broadcasted to all active interactive user sessions.</span>
                    <span>{commandModal.payload.length} / 255</span>
                  </div>
                </div>
              ) : commandModal.type === "lock" ? (
                <div style={{ fontSize: "13px", color: "#475569", lineHeight: 1.5 }}>
                  This will immediately lock the desktop user session on <strong>{hostname}</strong>.
                  The user will need to enter their password to unlock.
                </div>
              ) : commandModal.type === "restart" ? (
                <div style={{ fontSize: "13px", color: "#475569", lineHeight: 1.5 }}>
                  <div
                    style={{
                      padding: "10px 12px",
                      background: "#fff7ed",
                      border: "1px solid #ffedd5",
                      borderRadius: "6px",
                      color: "#9a3412",
                      marginBottom: "12px",
                      fontSize: "12px",
                    }}
                  >
                    ⚠ <strong>Warning:</strong> Active user sessions on <strong>{hostname}</strong> will receive a 5-second countdown notice before reboot. Unsaved work may be lost.
                  </div>
                  Are you sure you want to trigger a remote system restart?
                </div>
              ) : (
                <div style={{ fontSize: "13px", color: "#475569", lineHeight: 1.5 }}>
                  <div
                    style={{
                      padding: "10px 12px",
                      background: "#fef2f2",
                      border: "1px solid #fee2e2",
                      borderRadius: "6px",
                      color: "#991b1b",
                      marginBottom: "12px",
                      fontSize: "12px",
                    }}
                  >
                    🚨 <strong>Danger:</strong> The computer <strong>{hostname}</strong> will be powered down in 5 seconds. You will not be able to interact with it remotely until it is manually powered on.
                  </div>
                  Are you sure you want to trigger a remote system shutdown?
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div
              style={{
                padding: "14px 22px",
                borderTop: "1px solid #edf0f4",
                background: "#f8fafc",
                display: "flex",
                justifyContent: "flex-end",
                gap: "10px",
              }}
            >
              <button
                type="button"
                className="export"
                onClick={handleCloseCommandModal}
                disabled={actionLoading}
              >
                Cancel
              </button>
              <button
                type="button"
                className="refresh"
                onClick={handleSubmitCommand}
                disabled={actionLoading}
                style={{
                  background:
                    commandModal.type === "shutdown"
                      ? "#dc2626"
                      : commandModal.type === "restart"
                      ? "#ea580c"
                      : "#0962df",
                  color: "#ffffff",
                  border: "none",
                }}
              >
                {actionLoading
                  ? "Dispatching..."
                  : commandModal.type === "message"
                  ? "Send Notice"
                  : commandModal.type === "lock"
                  ? "Lock Workstation"
                  : commandModal.type === "restart"
                  ? "Restart System"
                  : "Shutdown System"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =================================================
          SOFTWARE INVENTORY (V3.1)
      ================================================= */}
      <div className="table-card" style={{ marginTop: "24px" }}>
        <div
          className="page-section-header"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "18px 22px",
            borderBottom: "1px solid #edf0f4",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: "16px", color: "#07144a" }}>
              Installed Software Inventory
            </h3>
            <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#68748b" }}>
              System applications discovered on this computer.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              className="table-search"
              style={{ width: "240px", height: "36px" }}
            >
              <input
                value={softwareSearch}
                onChange={(e) => setSoftwareSearch(e.target.value)}
                placeholder="Search software, publisher..."
                style={{ fontSize: "12px" }}
              />
              <Icon type="search" size={16} />
            </div>

            <button
              className="export"
              onClick={loadSoftware}
              disabled={softwareLoading}
              title="Refresh software list from server"
              style={{ width: "auto", height: "36px", padding: "0 14px" }}
            >
              <Icon type="refresh" size={14} />
              Refresh
            </button>
          </div>
        </div>

        {softwareLoading && softwareList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <Icon type="refresh" size={32} />
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>Loading software inventory...</h4>
            <p style={{ margin: 0, fontSize: "13px", color: "#68748b" }}>Fetching installed application registry from server.</p>
          </div>
        ) : softwareError && softwareList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#dc2626" }}>Failed to load software inventory</h4>
            <p style={{ margin: "0 0 12px", fontSize: "13px", color: "#68748b" }}>{softwareError}</p>
            <button
              className="refresh"
              onClick={loadSoftware}
              style={{ display: "inline-flex" }}
            >
              Try Again
            </button>
          </div>
        ) : softwareList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <Icon type="software" size={36} />
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>No software inventory recorded</h4>
            <p style={{ margin: 0, fontSize: "13px", color: "#68748b" }}>The client agent has not reported installed applications for this computer yet.</p>
          </div>
        ) : filteredSoftware.length === 0 ? (
          <div className="empty-state" style={{ padding: "30px 20px" }}>
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>No matching software found</h4>
            <p style={{ margin: "0 0 12px", fontSize: "13px", color: "#68748b" }}>No applications match &quot;{softwareSearch}&quot;.</p>
            <button
              className="export"
              onClick={() => setSoftwareSearch("")}
              style={{ display: "inline-flex" }}
            >
              Clear Search
            </button>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th style={{ width: "35%" }}>Software Name</th>
                  <th style={{ width: "20%" }}>Version</th>
                  <th style={{ width: "25%" }}>Publisher / Vendor</th>
                  <th style={{ width: "20%" }}>Install Date</th>
                </tr>
              </thead>
              <tbody>
                {filteredSoftware.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                        }}
                      >
                        <div
                          style={{
                            width: "32px",
                            height: "32px",
                            borderRadius: "6px",
                            background: "#eff6ff",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "#2563eb",
                            flexShrink: 0,
                          }}
                        >
                          <Icon type="software" size={16} />
                        </div>
                        <strong style={{ color: "#1e293b", fontSize: "12px" }}>
                          {item.name}
                        </strong>
                      </div>
                    </td>
                    <td>
                      <code
                        style={{
                          fontSize: "12px",
                          color: "#475569",
                          background: "#f1f5f9",
                          padding: "2px 6px",
                          borderRadius: "4px",
                        }}
                      >
                        {item.version || "—"}
                      </code>
                    </td>
                    <td style={{ color: "#475569", fontSize: "12px" }}>
                      {item.publisher || "—"}
                    </td>
                    <td style={{ color: "#64748b", fontSize: "12px" }}>
                      {item.install_date || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {softwareList.length > 0 && (
          <div
            style={{
              padding: "12px 20px",
              fontSize: "12px",
              color: "#64748b",
              borderTop: "1px solid #edf0f4",
              background: "#f8fafc",
            }}
          >
            Showing <strong>{filteredSoftware.length}</strong> of{" "}
            <strong>{softwareList.length}</strong> installed applications
          </div>
        )}
      </div>

      {/* =================================================
          RUNNING PROCESSES (V3.2)
      ================================================= */}
      <div className="table-card" style={{ marginTop: "24px" }}>
        <div
          className="page-section-header"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "18px 22px",
            borderBottom: "1px solid #edf0f4",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: "16px", color: "#07144a" }}>
              Running Processes
            </h3>
            <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#68748b" }}>
              Active system processes and resource utilization on this computer.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              className="table-search"
              style={{ width: "240px", height: "36px" }}
            >
              <input
                value={processSearch}
                onChange={(e) => setProcessSearch(e.target.value)}
                placeholder="Search process, PID..."
                style={{ fontSize: "12px" }}
              />
              <Icon type="search" size={16} />
            </div>

            <button
              className="export"
              onClick={loadProcesses}
              disabled={processLoading}
              title="Refresh running processes from server"
              style={{ width: "auto", height: "36px", padding: "0 14px" }}
            >
              <Icon type="refresh" size={14} />
              Refresh
            </button>
          </div>
        </div>

        {processLoading && processList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <Icon type="refresh" size={32} />
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>Loading running processes...</h4>
            <p style={{ margin: 0, fontSize: "13px", color: "#68748b" }}>Fetching active process table from server.</p>
          </div>
        ) : processError && processList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#dc2626" }}>Failed to load running processes</h4>
            <p style={{ margin: "0 0 12px", fontSize: "13px", color: "#68748b" }}>{processError}</p>
            <button
              className="refresh"
              onClick={loadProcesses}
              style={{ display: "inline-flex" }}
            >
              Try Again
            </button>
          </div>
        ) : processList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <Icon type="details" size={36} />
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>No running processes recorded</h4>
            <p style={{ margin: 0, fontSize: "13px", color: "#68748b" }}>The client agent has not reported active processes for this computer yet.</p>
          </div>
        ) : filteredProcesses.length === 0 ? (
          <div className="empty-state" style={{ padding: "30px 20px" }}>
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>No matching processes found</h4>
            <p style={{ margin: "0 0 12px", fontSize: "13px", color: "#68748b" }}>No active processes match &quot;{processSearch}&quot;.</p>
            <button
              className="export"
              onClick={() => setProcessSearch("")}
              style={{ display: "inline-flex" }}
            >
              Clear Search
            </button>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th style={{ width: "35%" }}>Process Name</th>
                  <th style={{ width: "15%" }}>PID</th>
                  <th style={{ width: "20%" }}>CPU %</th>
                  <th style={{ width: "20%" }}>Memory %</th>
                  <th style={{ width: "10%" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {filteredProcesses.map((proc) => (
                  <tr key={proc.id || `${proc.pid}-${proc.name}`}>
                    <td>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                        }}
                      >
                        <strong style={{ color: "#1e293b", fontSize: "12px", fontFamily: "monospace" }}>
                          {proc.name}
                        </strong>
                      </div>
                    </td>
                    <td>
                      <code
                        style={{
                          fontSize: "12px",
                          color: "#475569",
                          background: "#f1f5f9",
                          padding: "2px 6px",
                          borderRadius: "4px",
                        }}
                      >
                        {proc.pid}
                      </code>
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: "12px",
                          fontWeight: 600,
                          color: proc.cpu_percent > 50 ? "#dc2626" : proc.cpu_percent > 20 ? "#d97706" : "#2563eb",
                        }}
                      >
                        {proc.cpu_percent.toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: "12px",
                          fontWeight: 600,
                          color: proc.memory_percent > 50 ? "#dc2626" : proc.memory_percent > 20 ? "#d97706" : "#16a34a",
                        }}
                      >
                        {proc.memory_percent.toFixed(1)}%
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: "11px",
                          padding: "2px 8px",
                          borderRadius: "12px",
                          background: proc.status === "running" ? "#dcfce7" : "#f1f5f9",
                          color: proc.status === "running" ? "#15803d" : "#64748b",
                          textTransform: "capitalize",
                          fontWeight: 500,
                        }}
                      >
                        {proc.status || "active"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {processList.length > 0 && (
          <div
            style={{
              padding: "12px 20px",
              fontSize: "12px",
              color: "#64748b",
              borderTop: "1px solid #edf0f4",
              background: "#f8fafc",
            }}
          >
            Showing <strong>{filteredProcesses.length}</strong>{" "}
            of{" "}
            <strong>{processList.length}</strong> running processes
          </div>
        )}
      </div>

      {/* =================================================
          APPLICATION USAGE HISTORY (V3.3)
      ================================================= */}
      <div className="table-card" style={{ marginTop: "24px" }}>
        <div
          className="page-section-header"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "18px 22px",
            borderBottom: "1px solid #edf0f4",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <h3 style={{ margin: 0, fontSize: "16px", color: "#07144a" }}>
              Application Usage History
            </h3>
            <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#68748b" }}>
              Completed application sessions and runtime duration tracking.
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            {/* Time range selector */}
            <div className="range-selector" style={{ display: "flex", gap: "4px" }}>
              {["1h", "6h", "24h", "all"].map((r) => (
                <button
                  key={r}
                  type="button"
                  className={usageTimeRange === r ? "active" : ""}
                  onClick={() => handleUsageTimeRangeChange(r)}
                  style={{
                    padding: "4px 10px",
                    fontSize: "12px",
                    borderRadius: "4px",
                    border: usageTimeRange === r ? "1px solid #0962df" : "1px solid #e2e8f0",
                    background: usageTimeRange === r ? "#0962df" : "#ffffff",
                    color: usageTimeRange === r ? "#ffffff" : "#475569",
                    cursor: "pointer",
                    fontWeight: usageTimeRange === r ? 600 : 400,
                  }}
                >
                  {r === "all" ? "All Time" : r.toUpperCase()}
                </button>
              ))}
            </div>

            <div
              className="table-search"
              style={{ width: "220px", height: "36px" }}
            >
              <input
                value={usageSearch}
                onChange={(e) => setUsageSearch(e.target.value)}
                placeholder="Search application..."
                style={{ fontSize: "12px" }}
              />
              <Icon type="search" size={16} />
            </div>

            <button
              className="export"
              onClick={() => loadUsage(usageTimeRange)}
              disabled={usageLoading}
              title="Refresh application usage history from server"
              style={{ width: "auto", height: "36px", padding: "0 14px" }}
            >
              <Icon type="refresh" size={14} />
              Refresh
            </button>
          </div>
        </div>

        {/* Summary Badges (When data exists) */}
        {!usageLoading && !usageError && filteredUsage.length > 0 && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "14px",
              padding: "16px 22px",
              background: "#f8fafc",
              borderBottom: "1px solid #edf0f4",
            }}
          >
            <div style={{ background: "#ffffff", padding: "12px 16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.5px" }}>
                Total Sessions
              </div>
              <div style={{ fontSize: "18px", fontWeight: 700, color: "#0f172a", marginTop: "4px" }}>
                {filteredUsage.length}
              </div>
            </div>

            <div style={{ background: "#ffffff", padding: "12px 16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.5px" }}>
                Total Active Time
              </div>
              <div style={{ fontSize: "18px", fontWeight: 700, color: "#0962df", marginTop: "4px" }}>
                {formatDuration(totalUsageSeconds)}
              </div>
            </div>

            <div style={{ background: "#ffffff", padding: "12px 16px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ fontSize: "11px", color: "#64748b", textTransform: "uppercase", fontWeight: 600, letterSpacing: "0.5px" }}>
                Top Application
              </div>
              <div style={{ fontSize: "14px", fontWeight: 700, color: "#0f172a", marginTop: "4px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {topApplications[0] ? `${topApplications[0].name} (${formatDuration(topApplications[0].duration)})` : "—"}
              </div>
            </div>
          </div>
        )}

        {/* Top Applications Duration Breakdown Bar */}
        {!usageLoading && !usageError && topApplications.length > 0 && totalUsageSeconds > 0 && (
          <div style={{ padding: "14px 22px", borderBottom: "1px solid #edf0f4" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <span style={{ fontSize: "12px", fontWeight: 600, color: "#334155" }}>Top Applications by Usage Time</span>
              <span style={{ fontSize: "11px", color: "#64748b" }}>Share of recorded runtime</span>
            </div>
            <div style={{ display: "flex", height: "10px", borderRadius: "5px", overflow: "hidden", background: "#f1f5f9" }}>
              {topApplications.map((app, idx) => {
                const colors = ["#0962df", "#159b55", "#f39b13", "#8b5cf6", "#ec4899"];
                const pct = (app.duration / totalUsageSeconds) * 100;
                return (
                  <div
                    key={app.name}
                    title={`${app.name}: ${formatDuration(app.duration)} (${pct.toFixed(1)}%)`}
                    style={{
                      width: `${pct}%`,
                      background: colors[idx % colors.length],
                      minWidth: pct > 0 ? "4px" : "0",
                    }}
                  />
                );
              })}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginTop: "10px" }}>
              {topApplications.map((app, idx) => {
                const colors = ["#0962df", "#159b55", "#f39b13", "#8b5cf6", "#ec4899"];
                const pct = (app.duration / totalUsageSeconds) * 100;
                return (
                  <div key={app.name} style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "11px", color: "#475569" }}>
                    <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: colors[idx % colors.length] }} />
                    <strong>{app.name}</strong>
                    <span>({formatDuration(app.duration)} · {pct.toFixed(0)}%)</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {usageLoading && usageList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <Icon type="refresh" size={32} />
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>Loading usage history...</h4>
            <p style={{ margin: 0, fontSize: "13px", color: "#68748b" }}>Fetching application runtime sessions from server.</p>
          </div>
        ) : usageError && usageList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#dc2626" }}>Failed to load usage history</h4>
            <p style={{ margin: "0 0 12px", fontSize: "13px", color: "#68748b" }}>{usageError}</p>
            <button
              className="refresh"
              onClick={() => loadUsage(usageTimeRange)}
              style={{ display: "inline-flex" }}
            >
              Try Again
            </button>
          </div>
        ) : usageList.length === 0 ? (
          <div className="empty-state" style={{ padding: "40px 20px" }}>
            <Icon type="reports" size={36} />
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>No application usage recorded</h4>
            <p style={{ margin: 0, fontSize: "13px", color: "#68748b" }}>The client agent has not reported application sessions for this computer yet.</p>
          </div>
        ) : filteredUsage.length === 0 ? (
          <div className="empty-state" style={{ padding: "30px 20px" }}>
            <h4 style={{ margin: "10px 0 4px", fontSize: "15px", color: "#101a3d" }}>No matching sessions found</h4>
            <p style={{ margin: "0 0 12px", fontSize: "13px", color: "#68748b" }}>No application usage matches &quot;{usageSearch}&quot;.</p>
            <button
              className="export"
              onClick={() => setUsageSearch("")}
              style={{ display: "inline-flex" }}
            >
              Clear Search
            </button>
          </div>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th style={{ width: "35%" }}>Application</th>
                  <th style={{ width: "25%" }}>Session Started</th>
                  <th style={{ width: "25%" }}>Session Ended</th>
                  <th style={{ width: "15%" }}>Active Duration</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsage.map((session) => (
                  <tr key={session.id || `${session.application_name}-${session.started_at}`}>
                    <td>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                        }}
                      >
                        <div
                          style={{
                            width: "32px",
                            height: "32px",
                            borderRadius: "6px",
                            background: "#f0fdf4",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            color: "#16a34a",
                            flexShrink: 0,
                          }}
                        >
                          <Icon type="computer" size={16} />
                        </div>
                        <strong style={{ color: "#1e293b", fontSize: "12px", fontFamily: "monospace" }}>
                          {session.application_name}
                        </strong>
                      </div>
                    </td>
                    <td style={{ color: "#475569", fontSize: "12px" }}>
                      {formatDateTime(session.started_at)}
                    </td>
                    <td style={{ color: "#64748b", fontSize: "12px" }}>
                      {formatDateTime(session.ended_at)}
                    </td>
                    <td>
                      <code
                        style={{
                          fontSize: "12px",
                          fontWeight: 600,
                          color: "#0962df",
                          background: "#eff6ff",
                          padding: "2px 8px",
                          borderRadius: "4px",
                        }}
                      >
                        {formatDuration(session.duration_seconds)}
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {usageList.length > 0 && (
          <div
            style={{
              padding: "12px 20px",
              fontSize: "12px",
              color: "#64748b",
              borderTop: "1px solid #edf0f4",
              background: "#f8fafc",
            }}
          >
            Showing <strong>{filteredUsage.length}</strong> of{" "}
            <strong>{usageList.length}</strong> application usage sessions
          </div>
        )}
      </div>
    </div>
  );
}

export default ComputerDetails;