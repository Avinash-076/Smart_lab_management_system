import { useState, useEffect, useCallback } from "react";
import {
  getComputer,
  getComputerMetrics,
  updateComputer,
} from "../../../services/computerService";
import {
  getComputerSoftware,
  getComputerSoftwareSummary,
} from "../../../services/softwareService";
import { getComputerProcessesSummary } from "../../../services/processService";
import { getComputerCommandsSummary } from "../../../services/commandService";
import Icon from "../../../components/ui/Icon";
import MatrixTab from "../components/MatrixTab";
import ComputerSummaryCard from "../components/ComputerSummaryCard";
import ComputerDetailsTabs from "../components/ComputerDetailsTabs";
import HardwareInfoTab from "../components/HardwareInfoTab";
import HistoryTab from "../components/HistoryTab";
import SoftwareTab from "../components/SoftwareTab";
import ProcessesTab from "../components/ProcessesTab";
import RemoteControlTab from "../components/RemoteControlTab";
import EditComputerModal from "../components/EditComputerModal";
import { useComputerWebSocket } from "../hooks/useComputerWebSocket";
import "./ComputerDetails.css";





function ComputerDetails({ computer, onBack }) {
  const rawId =
    computer?.id !== undefined
      ? computer.id
      : typeof computer === "number" || typeof computer === "string"
      ? computer
      : null;
  const computerId =
    rawId !== null && rawId !== undefined && !isNaN(Number(rawId))
      ? Number(rawId)
      : rawId;

  const [details, setDetails] = useState(null);
  const [latestMetric, setLatestMetric] = useState(null);
  const [loading, setLoading] = useState(Boolean(computerId));
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("hardware");
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);


  // Software inventory state (V3.1 & V3.2)
  const [, setSoftwareList] = useState([]);
  const [softwareLoading, setSoftwareLoading] = useState(false);
  const [softwareSummary, setSoftwareSummary] = useState(null);
  const [isScanningSoftware, setIsScanningSoftware] = useState(false);

  // Running processes state (V3.2 & V6)
  const [processSummary, setProcessSummary] = useState(null);
  const [processLoading, setProcessLoading] = useState(false);


  // Remote command summary state (V5.1 & V6)
  const [commandSummary, setCommandSummary] = useState(null);
  const [commandLoading, setCommandLoading] = useState(false);


  const loadSoftware = useCallback(async () => {
    if (!computerId) return;
    try {
      setSoftwareLoading(true);
      const [dataRes, sumRes] = await Promise.allSettled([
        getComputerSoftware(computerId),
        getComputerSoftwareSummary(computerId),
      ]);
      if (dataRes.status === "fulfilled") {
        const val = dataRes.value;
        const list = Array.isArray(val?.data) ? val.data : (Array.isArray(val) ? val : []);
        setSoftwareList(list);
      } else {
        setSoftwareList([]);
      }
      if (sumRes.status === "fulfilled") {
        setSoftwareSummary(sumRes.value);
      }
    } catch (err) {
      console.warn("Could not fetch software inventory:", err);
      setSoftwareList([]);
    } finally {
      setSoftwareLoading(false);
    }
  }, [computerId]);

  const handleScanNow = useCallback(async () => {
    if (!computerId) return;
    try {
      setIsScanningSoftware(true);
      await loadSoftware();
      const sum = await getComputerSoftwareSummary(computerId);
      setSoftwareSummary(sum);
    } catch (err) {
      console.warn("Scan refresh failed:", err);
    } finally {
      setIsScanningSoftware(false);
    }
  }, [computerId, loadSoftware]);

  const loadProcesses = useCallback(async () => {
    if (!computerId) return;
    try {
      setProcessLoading(true);
      const sum = await getComputerProcessesSummary(computerId);
      setProcessSummary(sum);
    } catch (err) {
      console.warn("Could not fetch process summary:", err);
    } finally {
      setProcessLoading(false);
    }
  }, [computerId]);

  const loadCommandsSummary = useCallback(async () => {
    if (!computerId) return;
    try {
      setCommandLoading(true);
      const sum = await getComputerCommandsSummary(computerId);
      setCommandSummary(sum);
    } catch (err) {
      console.warn("Could not fetch command summary:", err);
    } finally {
      setCommandLoading(false);
    }
  }, [computerId]);

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

      await loadCommandsSummary();
      await loadSoftware();
      await loadProcesses();
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
    loadCommandsSummary,
    loadSoftware,
    loadProcesses,
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

        try {
          const sw = await getComputerSoftware(computerId);
          if (!ignore) {
            setSoftwareList(Array.isArray(sw?.data) ? sw.data : (Array.isArray(sw) ? sw : []));
          }
        } catch {
          if (!ignore) {
            setSoftwareList([]);
          }
        }

        try {
          const pSum = await getComputerProcessesSummary(computerId);
          if (!ignore) {
            setProcessSummary(pSum);
          }
        } catch {
          // ignore process summary error in background refresh
        }

        try {
          const cSum = await getComputerCommandsSummary(computerId);
          if (!ignore) {
            setCommandSummary(cSum);
          }
        } catch {
          // ignore command summary error in background refresh
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
  }, [computerId]);

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

  useComputerWebSocket(computerId, {
    onMetricUpdate: handleLiveMetric,
    onStatusUpdate: handleLiveStatus,
  });


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
              Select a computer from Computers to view its complete
              information.
            </p>
          </div>
        </div>

        <div className="table-card">
          <div className="empty-state" style={{ padding: "50px 20px" }}>
            <Icon type="details" size={40} />
            <h3>No computer selected</h3>
            <p>
              Open Computers and click the view button beside a
              computer.
            </p>
            <button
              type="button"
              className="computer-details-back-btn"
              onClick={onBack}
              style={{ marginTop: "15px" }}
            >
              <Icon type="arrow-left" size={16} />
              Back to Computers
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
          <div className="top-actions">
            <button
              type="button"
              className="computer-details-back-btn"
              onClick={onBack}
            >
              <Icon type="arrow-left" size={16} />
              Back to Computers
            </button>
          </div>
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
          <div className="top-actions">
            <button
              type="button"
              className="computer-details-back-btn"
              onClick={onBack}
            >
              <Icon type="arrow-left" size={16} />
              Back to Computers
            </button>
          </div>
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
              <button
                type="button"
                className="computer-details-back-btn"
                onClick={onBack}
              >
                <Icon type="arrow-left" size={16} />
                Back to Computers
              </button>
              <button
                type="button"
                className="export"
                onClick={loadDetails}
              >
                <Icon type="refresh" size={16} />
                Try Again
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
  const status = (details.status || "offline").toLowerCase();






  const hardware = details.hardware || {};
  const uptimeText = (() => {
    if (typeof hardware.uptime_seconds === "number" && hardware.uptime_seconds > 0) {
      const days = Math.floor(hardware.uptime_seconds / 86400);
      const hours = Math.floor((hardware.uptime_seconds % 86400) / 3600);
      const mins = Math.floor((hardware.uptime_seconds % 3600) / 60);
      if (days > 0) return `${days}d ${hours}h ${mins}m`;
      if (hours > 0) return `${hours}h ${mins}m`;
      return `${mins}m`;
    }
    return status === "online" ? "Active" : "—";
  })();

  const handleSaveEdit = async (updatedComputer) => {
    try {
      await updateComputer(updatedComputer.id, {
        hostname: updatedComputer.hostname,
        ip_address: updatedComputer.ip_address,
        mac_address: updatedComputer.mac_address,
        os_name: updatedComputer.os_name,
        os_version: updatedComputer.os_version || "1.0",
      });
      setDetails((prev) => ({ ...prev, ...updatedComputer }));
      setIsEditModalOpen(false);
    } catch (err) {
      console.error("Failed to update computer:", err);
      setDetails((prev) => ({ ...prev, ...updatedComputer }));
      setIsEditModalOpen(false);
    }
  };

  return (
    <div className="content">
      {/* =================================================
          TOP ACTION BAR (Back to Computers, Refresh, Edit Details)
      ================================================= */}
      <div className="details-top-actions-bar">
        <button
          type="button"
          className="computer-details-back-btn"
          onClick={onBack}
          title="Return to Computers inventory"
        >
          <Icon type="arrow-left" size={16} />
          Back to Computers
        </button>

        <div className="details-action-btns-group">
          <button
            type="button"
            className="details-btn-refresh"
            onClick={loadDetails}
            disabled={loading}
            title="Refresh computer information from backend"
          >
            <Icon type="refresh" size={15} />
            Refresh
          </button>
          <button
            type="button"
            className="details-btn-edit"
            onClick={() => setIsEditModalOpen(true)}
            title="Edit computer details"
          >
            <Icon type="edit" size={15} />
            Edit Details
          </button>
        </div>
      </div>

      {/* =================================================
          COMPUTER SUMMARY CARD
      ================================================= */}
      <ComputerSummaryCard
        computer={details}
        latestMetric={latestMetric}
        activeTab={activeTab}
        softwareSummary={softwareSummary}
        softwareLoading={softwareLoading}
        processSummary={processSummary}
        processLoading={processLoading}
        commandSummary={commandSummary}
        commandLoading={commandLoading}
        onRunCommand={() => {
          const el = document.getElementById("execute-command-panel");
          if (el) el.scrollIntoView({ behavior: "smooth" });
        }}
        onScanNow={handleScanNow}
        scanning={isScanningSoftware}
      />

      {/* =================================================
          6-TAB NAVIGATION
      ================================================= */}
      <ComputerDetailsTabs
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      {/* =================================================
          TAB 1: HARDWARE INFO (REDESIGNED)
      ================================================= */}
      {activeTab === "hardware" && (
        <HardwareInfoTab
          computer={details}
          uptimeText={uptimeText}
        />
      )}

      {/* =================================================
          TAB 2: MATRIX (HISTORICAL METRICS & CHARTS)
      ================================================= */}
      {activeTab === "matrix" && (
        <MatrixTab
          computerId={computerId}
          computer={details}
          onTabChange={setActiveTab}
        />
      )}

      {/* =================================================
          TAB 6: REMOTE CONTROL (REDESIGNED)
      ================================================= */}
      {activeTab === "commands" && (
        <RemoteControlTab
          computerId={computerId}
          computer={details}
          onSummaryUpdate={setCommandSummary}
        />
      )}

      {/* =================================================
          TAB 4: SOFTWARE INVENTORY (REDESIGNED)
      ================================================= */}
      {activeTab === "software" && (
        <SoftwareTab
          computerId={computerId}
          computer={details}
          onSummaryUpdate={setSoftwareSummary}
          onScanNow={handleScanNow}
          scanning={isScanningSoftware}
        />
      )}

      {/* =================================================
          TAB 5: RUNNING PROCESSES (REDESIGNED)
      ================================================= */}
      {activeTab === "processes" && (
        <ProcessesTab
          computerId={computerId}
          computer={details}
          onSummaryUpdate={setProcessSummary}
          onScanNow={handleScanNow}
          scanning={isScanningSoftware}
        />
      )}

      {/* =================================================
          TAB 3: APPLICATION USAGE HISTORY
      ================================================= */}
      {activeTab === "history" && (
        <HistoryTab
          computerId={computerId}
        />
      )}

      {/* =================================================
          EDIT COMPUTER DETAILS MODAL
      ================================================= */}
      {isEditModalOpen && details && (
        <EditComputerModal
          computer={details}
          onClose={() => setIsEditModalOpen(false)}
          onSave={handleSaveEdit}
        />
      )}
    </div>
  );
}

export default ComputerDetails;