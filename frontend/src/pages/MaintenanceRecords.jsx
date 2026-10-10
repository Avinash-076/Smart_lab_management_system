import { useState, useEffect, useMemo, useCallback } from "react";
import {
  getMaintenanceRecords,
  getMaintenanceStats,
  getComputers,
  createMaintenanceRecord,
  updateMaintenanceRecord,
  completeMaintenanceRecord,
  deleteMaintenanceRecord,
} from "../services/api";
import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function formatDateTime(dateStr) {
  if (!dateStr) return "—";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return "—";
  }
}

function MaintenanceRecords() {
  const [records, setRecords] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    scheduled: 0,
    in_progress: 0,
    completed: 0,
    cancelled: 0,
  });
  const [computers, setComputers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All Status");
  const [typeFilter, setTypeFilter] = useState("All Types");
  const [computerFilter, setComputerFilter] = useState("All Computers");

  // Schedule Modal State
  const [isScheduleOpen, setIsScheduleOpen] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    computer_id: "",
    maintenance_type: "preventive",
    title: "",
    description: "",
    scheduled_at: "",
    technician_name: "",
    notes: "",
  });
  const [scheduleLoading, setScheduleLoading] = useState(false);
  const [scheduleError, setScheduleError] = useState("");

  // Complete Modal State
  const [completeModal, setCompleteModal] = useState({
    isOpen: false,
    record: null,
    work_performed: "",
    notes: "",
  });
  const [completeLoading, setCompleteLoading] = useState(false);
  const [completeError, setCompleteError] = useState("");

  // Detail Modal State
  const [detailModal, setDetailModal] = useState({
    isOpen: false,
    record: null,
  });

  // Action in-progress id
  const [actionLoadingId, setActionLoadingId] = useState(null);

  /* =====================================================
     DATA FETCHING
  ===================================================== */

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const [recordsData, statsData, computersData] = await Promise.all([
        getMaintenanceRecords({ limit: 300 }),
        getMaintenanceStats(),
        getComputers(),
      ]);

      setRecords(Array.isArray(recordsData) ? recordsData : []);

      if (statsData && typeof statsData === "object") {
        setStats({
          total: statsData.total || 0,
          scheduled: statsData.scheduled || 0,
          in_progress: statsData.in_progress || 0,
          completed: statsData.completed || 0,
          cancelled: statsData.cancelled || 0,
        });
      }

      if (Array.isArray(computersData)) {
        setComputers(computersData);
      }
    } catch (err) {
      console.error("Failed to load maintenance records:", err);
      setError(err.message || "Failed to load maintenance data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        setLoading(true);
        setError("");

        const [recordsData, statsData, computersData] = await Promise.all([
          getMaintenanceRecords({ limit: 300 }),
          getMaintenanceStats(),
          getComputers(),
        ]);

        if (ignore) return;

        setRecords(Array.isArray(recordsData) ? recordsData : []);

        if (statsData && typeof statsData === "object") {
          setStats({
            total: statsData.total || 0,
            scheduled: statsData.scheduled || 0,
            in_progress: statsData.in_progress || 0,
            completed: statsData.completed || 0,
            cancelled: statsData.cancelled || 0,
          });
        }

        if (Array.isArray(computersData)) {
          setComputers(computersData);
        }
      } catch (err) {
        if (!ignore) {
          console.error("Failed to load maintenance records:", err);
          setError(err.message || "Failed to load maintenance data.");
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
  }, []);

  const showSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => {
      setSuccessMsg("");
    }, 4000);
  };

  /* =====================================================
     SCHEDULE MAINTENANCE HANDLER
  ===================================================== */

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    if (!scheduleForm.computer_id) {
      setScheduleError("Please select a computer.");
      return;
    }
    if (!scheduleForm.title.trim()) {
      setScheduleError("Maintenance title is required.");
      return;
    }

    try {
      setScheduleLoading(true);
      setScheduleError("");

      const payload = {
        computer_id: Number(scheduleForm.computer_id),
        maintenance_type: scheduleForm.maintenance_type,
        title: scheduleForm.title.trim(),
        description: scheduleForm.description.trim() || null,
        scheduled_at: scheduleForm.scheduled_at ? new Date(scheduleForm.scheduled_at).toISOString() : new Date().toISOString(),
        technician_name: scheduleForm.technician_name.trim() || null,
        notes: scheduleForm.notes.trim() || null,
      };

      await createMaintenanceRecord(payload);

      setIsScheduleOpen(false);
      setScheduleForm({
        computer_id: "",
        maintenance_type: "preventive",
        title: "",
        description: "",
        scheduled_at: "",
        technician_name: "",
        notes: "",
      });

      showSuccess("Maintenance task scheduled successfully.");
      await loadData();
    } catch (err) {
      console.error("Failed to schedule maintenance:", err);
      setScheduleError(err.message || "Failed to schedule maintenance.");
    } finally {
      setScheduleLoading(false);
    }
  };

  /* =====================================================
     STATUS TRANSITION HANDLERS
  ===================================================== */

  const handleStatusChange = async (record, newStatus) => {
    try {
      setActionLoadingId(record.id);
      await updateMaintenanceRecord(record.id, { status: newStatus });
      showSuccess(`Maintenance status updated to ${newStatus.replace("_", " ")}.`);
      await loadData();
    } catch (err) {
      console.error("Failed to update maintenance status:", err);
      setError(err.message || "Failed to update maintenance status.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleOpenComplete = (record) => {
    setCompleteError("");
    setCompleteModal({
      isOpen: true,
      record,
      work_performed: record.work_performed || "",
      notes: record.notes || "",
    });
  };

  const handleCompleteSubmit = async (e) => {
    e.preventDefault();
    if (!completeModal.record) return;

    try {
      setCompleteLoading(true);
      setCompleteError("");
      await completeMaintenanceRecord(
        completeModal.record.id,
        completeModal.work_performed.trim() || null,
        completeModal.notes.trim() || null
      );
      setCompleteModal({ isOpen: false, record: null, work_performed: "", notes: "" });
      showSuccess("Maintenance record marked as completed.");
      await loadData();
    } catch (err) {
      console.error("Failed to complete maintenance:", err);
      setCompleteError(err.message || "Failed to complete maintenance.");
    } finally {
      setCompleteLoading(false);
    }
  };

  const handleDelete = async (record) => {
    if (!window.confirm(`Are you sure you want to delete maintenance record "${record.title}"?`)) {
      return;
    }

    try {
      setActionLoadingId(record.id);
      await deleteMaintenanceRecord(record.id);
      showSuccess("Maintenance record deleted successfully.");
      await loadData();
    } catch (err) {
      console.error("Failed to delete maintenance record:", err);
      setError(err.message || "Failed to delete maintenance record.");
    } finally {
      setActionLoadingId(null);
    }
  };

  /* =====================================================
     FILTER RECORDS
  ===================================================== */

  const computerMap = useMemo(() => {
    const map = new Map();
    computers.forEach((c) => {
      map.set(c.id, c.hostname || `Computer #${c.id}`);
    });
    return map;
  }, [computers]);

  const filteredRecords = useMemo(() => {
    const searchText = search.toLowerCase().trim();

    return records.filter((rec) => {
      const compName =
        rec.computer_hostname ||
        computerMap.get(rec.computer_id) ||
        `PC-${rec.computer_id}`;

      const matchesSearch =
        !searchText ||
        compName.toLowerCase().includes(searchText) ||
        (rec.title && rec.title.toLowerCase().includes(searchText)) ||
        (rec.description && rec.description.toLowerCase().includes(searchText)) ||
        (rec.technician_name && rec.technician_name.toLowerCase().includes(searchText)) ||
        (rec.work_performed && rec.work_performed.toLowerCase().includes(searchText));

      let matchesStatus = true;
      if (statusFilter === "Scheduled") matchesStatus = rec.status === "scheduled";
      else if (statusFilter === "In Progress") matchesStatus = rec.status === "in_progress";
      else if (statusFilter === "Completed") matchesStatus = rec.status === "completed";
      else if (statusFilter === "Cancelled") matchesStatus = rec.status === "cancelled";

      let matchesType = true;
      if (typeFilter !== "All Types") {
        matchesType =
          rec.maintenance_type &&
          rec.maintenance_type.toLowerCase() === typeFilter.toLowerCase();
      }

      let matchesComputer = true;
      if (computerFilter !== "All Computers") {
        matchesComputer =
          compName === computerFilter ||
          String(rec.computer_id) === String(computerFilter);
      }

      return matchesSearch && matchesStatus && matchesType && matchesComputer;
    });
  }, [records, search, statusFilter, typeFilter, computerFilter, computerMap]);

  /* =====================================================
     RESET
  ===================================================== */

  const resetFilters = () => {
    setSearch("");
    setStatusFilter("All Status");
    setTypeFilter("All Types");
    setComputerFilter("All Computers");
  };

  /* =====================================================
     STYLE HELPERS
  ===================================================== */

  const getTypeBadgeStyle = (typeVal) => {
    const t = (typeVal || "").toLowerCase();
    if (t === "emergency") {
      return {
        background: "rgba(239, 68, 68, 0.12)",
        color: "#ef4444",
        border: "1px solid rgba(239, 68, 68, 0.3)",
      };
    }
    if (t === "corrective") {
      return {
        background: "rgba(249, 115, 22, 0.12)",
        color: "#f97316",
        border: "1px solid rgba(249, 115, 22, 0.3)",
      };
    }
    if (t === "hardware") {
      return {
        background: "rgba(20, 184, 166, 0.12)",
        color: "#14b8a6",
        border: "1px solid rgba(20, 184, 166, 0.3)",
      };
    }
    if (t === "software") {
      return {
        background: "rgba(99, 102, 241, 0.12)",
        color: "#818cf8",
        border: "1px solid rgba(99, 102, 241, 0.3)",
      };
    }
    // preventive default
    return {
      background: "rgba(59, 130, 246, 0.12)",
      color: "#3b82f6",
      border: "1px solid rgba(59, 130, 246, 0.3)",
    };
  };

  const getStatusBadgeStyle = (statusVal) => {
    const st = (statusVal || "").toLowerCase();
    if (st === "completed") {
      return {
        background: "rgba(16, 185, 129, 0.12)",
        color: "#10b981",
        border: "1px solid rgba(16, 185, 129, 0.3)",
      };
    }
    if (st === "in_progress") {
      return {
        background: "rgba(168, 85, 247, 0.12)",
        color: "#a855f7",
        border: "1px solid rgba(168, 85, 247, 0.3)",
      };
    }
    if (st === "cancelled") {
      return {
        background: "rgba(107, 114, 128, 0.15)",
        color: "#9ca3af",
        border: "1px solid rgba(107, 114, 128, 0.3)",
      };
    }
    // scheduled
    return {
      background: "rgba(249, 115, 22, 0.12)",
      color: "#f97316",
      border: "1px solid rgba(249, 115, 22, 0.3)",
    };
  };

  const formatStatusText = (statusVal) => {
    const st = (statusVal || "").toLowerCase();
    if (st === "in_progress") return "In Progress";
    if (st === "completed") return "Completed";
    if (st === "cancelled") return "Cancelled";
    return "Scheduled";
  };

  const formatTypeText = (typeVal) => {
    const t = (typeVal || "").toLowerCase();
    if (!t) return "Preventive";
    return t.charAt(0).toUpperCase() + t.slice(1);
  };

  /* =====================================================
     RENDER
  ===================================================== */

  return (
    <div className="content">
      {/* =================================================
          PAGE HEADER
      ================================================= */}
      <div
        className="page-top"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div>
          <h2>Maintenance Records</h2>
          <p>Schedule, track, and manage computer maintenance and servicing activities.</p>
        </div>

        <button
          onClick={() => {
            setScheduleError("");
            setIsScheduleOpen(true);
          }}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            background: "linear-gradient(135deg, #3b82f6, #2563eb)",
            color: "#ffffff",
            border: "none",
            borderRadius: "8px",
            padding: "10px 18px",
            fontSize: "14px",
            fontWeight: "600",
            cursor: "pointer",
            boxShadow: "0 4px 12px rgba(37, 99, 235, 0.25)",
            transition: "all 0.2s ease",
          }}
        >
          <Icon type="plus" size={16} />
          Schedule Maintenance
        </button>
      </div>

      {/* =================================================
          SUCCESS & ERROR BANNERS
      ================================================= */}
      {successMsg && (
        <div
          style={{
            background: "rgba(16, 185, 129, 0.12)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            color: "#10b981",
            padding: "12px 18px",
            borderRadius: "8px",
            marginBottom: "16px",
            fontSize: "14px",
            fontWeight: "500",
          }}
        >
          ✓ {successMsg}
        </div>
      )}

      {error && (
        <div
          style={{
            background: "rgba(239, 68, 68, 0.12)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            color: "#ef4444",
            padding: "12px 18px",
            borderRadius: "8px",
            marginBottom: "16px",
            fontSize: "14px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>⚠ {error}</span>
          <button
            onClick={loadData}
            style={{
              background: "transparent",
              border: "1px solid rgba(239, 68, 68, 0.4)",
              color: "#ef4444",
              borderRadius: "6px",
              padding: "4px 12px",
              fontSize: "12px",
              cursor: "pointer",
            }}
          >
            Retry
          </button>
        </div>
      )}

      {/* =================================================
          STAT CARDS
      ================================================= */}
      <div className="cards">
        <StatCard
          icon="maintenance"
          title="Total Records"
          number={stats.total}
          footer="All maintenance records"
          type="blue"
        />

        <StatCard
          icon="issue"
          title="Scheduled"
          number={stats.scheduled}
          footer="Waiting for service"
          type="orange"
        />

        <StatCard
          icon="maintenance"
          title="In Progress"
          number={stats.in_progress}
          footer="Currently being serviced"
          type="purple"
        />

        <StatCard
          icon="check"
          title="Completed"
          number={stats.completed}
          footer="Finished maintenance"
          type="green"
        />
      </div>

      {/* =================================================
          MAINTENANCE TABLE CARD
      ================================================= */}
      <div className="table-card">
        {/* TABLE HEADER */}
        <div className="page-section-header">
          <div>
            <h3>Maintenance Records</h3>
            <p>Track reported problems and maintenance activities.</p>
          </div>
        </div>

        {/* FILTERS */}
        <div className="filters">
          {/* SEARCH */}
          <div className="table-search">
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search computer, title, technician..."
            />
            <Icon type="search" size={18} />
          </div>

          {/* STATUS */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option>All Status</option>
            <option>Scheduled</option>
            <option>In Progress</option>
            <option>Completed</option>
            <option>Cancelled</option>
          </select>

          {/* TYPE */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
          >
            <option>All Types</option>
            <option>Preventive</option>
            <option>Corrective</option>
            <option>Emergency</option>
            <option>Software</option>
            <option>Hardware</option>
          </select>

          {/* COMPUTER */}
          <select
            value={computerFilter}
            onChange={(e) => setComputerFilter(e.target.value)}
          >
            <option>All Computers</option>
            {computers.map((comp) => (
              <option key={comp.id} value={comp.hostname || `PC-${comp.id}`}>
                {comp.hostname || `Computer #${comp.id}`}
              </option>
            ))}
          </select>

          {/* RESET / REFRESH */}
          <button
            className="refresh"
            onClick={() => {
              resetFilters();
              loadData();
            }}
          >
            <Icon type="refresh" size={17} />
            Refresh
          </button>
        </div>

        {/* RESULT COUNT */}
        <div
          style={{
            padding: "0 20px 15px",
            fontSize: "12px",
            color: "#718099",
          }}
        >
          Showing <strong>{filteredRecords.length}</strong> maintenance records
        </div>

        {/* TABLE BODY */}
        {loading ? (
          <div style={{ padding: "48px 24px", textAlign: "center", color: "#8b949e" }}>
            <div
              style={{
                display: "inline-block",
                width: "28px",
                height: "28px",
                border: "3px solid rgba(59, 130, 246, 0.2)",
                borderTopColor: "#3b82f6",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
                marginBottom: "12px",
              }}
            />
            <p style={{ margin: 0, fontSize: "14px" }}>Loading maintenance records...</p>
          </div>
        ) : filteredRecords.length > 0 ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th style={{ minWidth: "120px" }}>Computer</th>
                  <th style={{ minWidth: "180px" }}>Task / Type</th>
                  <th style={{ minWidth: "130px" }}>Technician</th>
                  <th style={{ minWidth: "100px" }}>Type</th>
                  <th style={{ minWidth: "140px" }}>Scheduled</th>
                  <th style={{ minWidth: "140px" }}>Completed</th>
                  <th style={{ minWidth: "110px" }}>Status</th>
                  <th style={{ minWidth: "200px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredRecords.map((rec) => {
                  const compName =
                    rec.computer_hostname ||
                    computerMap.get(rec.computer_id) ||
                    `PC-${rec.computer_id}`;
                  const isActionLoading = actionLoadingId === rec.id;

                  return (
                    <tr key={rec.id}>
                      {/* COMPUTER */}
                      <td>
                        <strong>{compName}</strong>
                      </td>

                      {/* TASK / TITLE */}
                      <td>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "9px",
                          }}
                        >
                          <div className="maintenance-icon">
                            <Icon type="maintenance" size={17} />
                          </div>
                          <div>
                            <strong style={{ display: "block" }}>{rec.title}</strong>
                            {rec.description && (
                              <span
                                style={{
                                  fontSize: "12px",
                                  color: "#8b949e",
                                  display: "-webkit-box",
                                  WebkitLineClamp: 1,
                                  WebkitBoxOrient: "vertical",
                                  overflow: "hidden",
                                  maxWidth: "220px",
                                }}
                              >
                                {rec.description}
                              </span>
                            )}
                          </div>
                        </div>
                      </td>

                      {/* TECHNICIAN */}
                      <td>{rec.technician_name || "Unassigned"}</td>

                      {/* TYPE BADGE */}
                      <td>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "3px 8px",
                            borderRadius: "12px",
                            fontSize: "12px",
                            fontWeight: "600",
                            ...getTypeBadgeStyle(rec.maintenance_type),
                          }}
                        >
                          {formatTypeText(rec.maintenance_type)}
                        </span>
                      </td>

                      {/* SCHEDULED DATE */}
                      <td style={{ fontSize: "12px", color: "#8b949e" }}>
                        {formatDateTime(rec.scheduled_at)}
                      </td>

                      {/* COMPLETED DATE */}
                      <td style={{ fontSize: "12px", color: "#8b949e" }}>
                        {formatDateTime(rec.completed_at)}
                      </td>

                      {/* STATUS */}
                      <td>
                        <span
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "5px",
                            padding: "3px 8px",
                            borderRadius: "12px",
                            fontSize: "12px",
                            fontWeight: "600",
                            ...getStatusBadgeStyle(rec.status),
                          }}
                        >
                          <i
                            style={{
                              display: "inline-block",
                              width: "6px",
                              height: "6px",
                              borderRadius: "50%",
                              background: "currentColor",
                            }}
                          />
                          {formatStatusText(rec.status)}
                        </span>
                      </td>

                      {/* ACTIONS */}
                      <td style={{ textAlign: "right" }}>
                        <div
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            justifyContent: "flex-end",
                          }}
                        >
                          {/* View details */}
                          <button
                            onClick={() => setDetailModal({ isOpen: true, record: rec })}
                            title="View Details"
                            style={{
                              background: "rgba(255, 255, 255, 0.05)",
                              border: "1px solid rgba(255, 255, 255, 0.12)",
                              color: "#e6edf3",
                              borderRadius: "6px",
                              padding: "4px 8px",
                              fontSize: "12px",
                              cursor: "pointer",
                            }}
                          >
                            Details
                          </button>

                          {/* Lifecycle: scheduled -> start */}
                          {rec.status === "scheduled" && (
                            <button
                              disabled={isActionLoading}
                              onClick={() => handleStatusChange(rec, "in_progress")}
                              title="Start Maintenance"
                              style={{
                                background: "rgba(168, 85, 247, 0.15)",
                                border: "1px solid rgba(168, 85, 247, 0.3)",
                                color: "#c084fc",
                                borderRadius: "6px",
                                padding: "4px 8px",
                                fontSize: "12px",
                                fontWeight: "600",
                                cursor: "pointer",
                              }}
                            >
                              Start
                            </button>
                          )}

                          {/* Lifecycle: scheduled or in_progress -> complete */}
                          {rec.status !== "completed" && rec.status !== "cancelled" && (
                            <button
                              disabled={isActionLoading}
                              onClick={() => handleOpenComplete(rec)}
                              title="Complete Maintenance"
                              style={{
                                background: "rgba(16, 185, 129, 0.15)",
                                border: "1px solid rgba(16, 185, 129, 0.3)",
                                color: "#34d399",
                                borderRadius: "6px",
                                padding: "4px 8px",
                                fontSize: "12px",
                                fontWeight: "600",
                                cursor: "pointer",
                              }}
                            >
                              Complete
                            </button>
                          )}

                          {/* Lifecycle: scheduled or in_progress -> cancel */}
                          {rec.status !== "completed" && rec.status !== "cancelled" && (
                            <button
                              disabled={isActionLoading}
                              onClick={() => handleStatusChange(rec, "cancelled")}
                              title="Cancel Maintenance"
                              style={{
                                background: "rgba(239, 68, 68, 0.1)",
                                border: "1px solid rgba(239, 68, 68, 0.25)",
                                color: "#f87171",
                                borderRadius: "6px",
                                padding: "4px 8px",
                                fontSize: "12px",
                                fontWeight: "600",
                                cursor: "pointer",
                              }}
                            >
                              Cancel
                            </button>
                          )}

                          {/* Lifecycle: completed or cancelled -> reschedule */}
                          {(rec.status === "completed" || rec.status === "cancelled") && (
                            <button
                              disabled={isActionLoading}
                              onClick={() => handleStatusChange(rec, "scheduled")}
                              title="Reschedule Maintenance"
                              style={{
                                background: "rgba(249, 115, 22, 0.15)",
                                border: "1px solid rgba(249, 115, 22, 0.3)",
                                color: "#fb923c",
                                borderRadius: "6px",
                                padding: "4px 8px",
                                fontSize: "12px",
                                fontWeight: "600",
                                cursor: "pointer",
                              }}
                            >
                              Reschedule
                            </button>
                          )}

                          {/* Delete */}
                          <button
                            disabled={isActionLoading}
                            onClick={() => handleDelete(rec)}
                            title="Delete Record"
                            style={{
                              background: "rgba(239, 68, 68, 0.1)",
                              border: "1px solid rgba(239, 68, 68, 0.25)",
                              color: "#f87171",
                              borderRadius: "6px",
                              padding: "4px 7px",
                              fontSize: "12px",
                              cursor: "pointer",
                            }}
                          >
                            ✕
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          /* EMPTY STATE */
          <div className="empty-state">
            <Icon type="maintenance" size={40} />
            <h3>No maintenance records found</h3>
            <p>No maintenance tasks match the selected filters or search keyword.</p>
            <button className="modal-button" onClick={resetFilters}>
              Clear Filters
            </button>
          </div>
        )}
      </div>

      {/* =================================================
          SCHEDULE MAINTENANCE MODAL
      ================================================= */}
      {isScheduleOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            style={{
              background: "#161b22",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "12px",
              padding: "24px",
              width: "100%",
              maxWidth: "520px",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "20px",
              }}
            >
              <h3 style={{ margin: 0, fontSize: "18px", color: "#f0f6fc" }}>
                Schedule Maintenance
              </h3>
              <button
                onClick={() => setIsScheduleOpen(false)}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#8b949e",
                  fontSize: "18px",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>

            {scheduleError && (
              <div
                style={{
                  background: "rgba(239, 68, 68, 0.15)",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                  color: "#ef4444",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  marginBottom: "16px",
                  fontSize: "13px",
                }}
              >
                ⚠ {scheduleError}
              </div>
            )}

            <form onSubmit={handleScheduleSubmit}>
              {/* Computer selector */}
              <div style={{ marginBottom: "16px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    color: "#8b949e",
                    marginBottom: "6px",
                    fontWeight: "500",
                  }}
                >
                  Computer <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <select
                  value={scheduleForm.computer_id}
                  onChange={(e) =>
                    setScheduleForm((prev) => ({
                      ...prev,
                      computer_id: e.target.value,
                    }))
                  }
                  required
                  style={{
                    width: "100%",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#e6edf3",
                    padding: "9px 12px",
                    fontSize: "14px",
                    outline: "none",
                  }}
                >
                  <option value="">Select a Computer...</option>
                  {computers.map((comp) => (
                    <option key={comp.id} value={comp.id}>
                      {comp.hostname || `Computer #${comp.id}`} ({comp.ip_address || "No IP"})
                    </option>
                  ))}
                </select>
              </div>

              {/* Type and Technician grid */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                  marginBottom: "16px",
                }}
              >
                <div>
                  <label
                    style={{
                      display: "block",
                      fontSize: "13px",
                      color: "#8b949e",
                      marginBottom: "6px",
                      fontWeight: "500",
                    }}
                  >
                    Maintenance Type
                  </label>
                  <select
                    value={scheduleForm.maintenance_type}
                    onChange={(e) =>
                      setScheduleForm((prev) => ({
                        ...prev,
                        maintenance_type: e.target.value,
                      }))
                    }
                    style={{
                      width: "100%",
                      background: "#0d1117",
                      border: "1px solid rgba(255, 255, 255, 0.15)",
                      borderRadius: "6px",
                      color: "#e6edf3",
                      padding: "9px 12px",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  >
                    <option value="preventive">Preventive</option>
                    <option value="corrective">Corrective</option>
                    <option value="emergency">Emergency</option>
                    <option value="software">Software</option>
                    <option value="hardware">Hardware</option>
                  </select>
                </div>

                <div>
                  <label
                    style={{
                      display: "block",
                      fontSize: "13px",
                      color: "#8b949e",
                      marginBottom: "6px",
                      fontWeight: "500",
                    }}
                  >
                    Technician Name
                  </label>
                  <input
                    type="text"
                    value={scheduleForm.technician_name}
                    onChange={(e) =>
                      setScheduleForm((prev) => ({
                        ...prev,
                        technician_name: e.target.value,
                      }))
                    }
                    placeholder="e.g. Lab Admin"
                    style={{
                      width: "100%",
                      background: "#0d1117",
                      border: "1px solid rgba(255, 255, 255, 0.15)",
                      borderRadius: "6px",
                      color: "#e6edf3",
                      padding: "9px 12px",
                      fontSize: "14px",
                      outline: "none",
                      boxSizing: "border-box",
                    }}
                  />
                </div>
              </div>

              {/* Title */}
              <div style={{ marginBottom: "16px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    color: "#8b949e",
                    marginBottom: "6px",
                    fontWeight: "500",
                  }}
                >
                  Task Title <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <input
                  type="text"
                  value={scheduleForm.title}
                  onChange={(e) =>
                    setScheduleForm((prev) => ({
                      ...prev,
                      title: e.target.value,
                    }))
                  }
                  placeholder="e.g. Hardware cleaning and thermal paste replacement"
                  required
                  style={{
                    width: "100%",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#e6edf3",
                    padding: "9px 12px",
                    fontSize: "14px",
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              {/* Scheduled Date */}
              <div style={{ marginBottom: "16px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    color: "#8b949e",
                    marginBottom: "6px",
                    fontWeight: "500",
                  }}
                >
                  Scheduled Date & Time
                </label>
                <input
                  type="datetime-local"
                  value={scheduleForm.scheduled_at}
                  onChange={(e) =>
                    setScheduleForm((prev) => ({
                      ...prev,
                      scheduled_at: e.target.value,
                    }))
                  }
                  style={{
                    width: "100%",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#e6edf3",
                    padding: "9px 12px",
                    fontSize: "14px",
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              {/* Description */}
              <div style={{ marginBottom: "16px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    color: "#8b949e",
                    marginBottom: "6px",
                    fontWeight: "500",
                  }}
                >
                  Description
                </label>
                <textarea
                  value={scheduleForm.description}
                  onChange={(e) =>
                    setScheduleForm((prev) => ({
                      ...prev,
                      description: e.target.value,
                    }))
                  }
                  placeholder="Details of the planned maintenance work..."
                  rows={3}
                  style={{
                    width: "100%",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#e6edf3",
                    padding: "9px 12px",
                    fontSize: "14px",
                    outline: "none",
                    resize: "vertical",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              {/* Notes */}
              <div style={{ marginBottom: "20px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    color: "#8b949e",
                    marginBottom: "6px",
                    fontWeight: "500",
                  }}
                >
                  Additional Notes
                </label>
                <input
                  type="text"
                  value={scheduleForm.notes}
                  onChange={(e) =>
                    setScheduleForm((prev) => ({
                      ...prev,
                      notes: e.target.value,
                    }))
                  }
                  placeholder="Optional preparatory remarks or equipment needed"
                  style={{
                    width: "100%",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#e6edf3",
                    padding: "9px 12px",
                    fontSize: "14px",
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                }}
              >
                <button
                  type="button"
                  onClick={() => setIsScheduleOpen(false)}
                  disabled={scheduleLoading}
                  style={{
                    background: "rgba(255, 255, 255, 0.08)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    color: "#e6edf3",
                    borderRadius: "6px",
                    padding: "9px 16px",
                    fontSize: "14px",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={scheduleLoading}
                  style={{
                    background: "linear-gradient(135deg, #3b82f6, #2563eb)",
                    border: "none",
                    color: "#ffffff",
                    borderRadius: "6px",
                    padding: "9px 18px",
                    fontSize: "14px",
                    fontWeight: "600",
                    cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(37, 99, 235, 0.3)",
                  }}
                >
                  {scheduleLoading ? "Scheduling..." : "Schedule Task"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================
          COMPLETE MAINTENANCE MODAL
      ================================================= */}
      {completeModal.isOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            style={{
              background: "#161b22",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "12px",
              padding: "24px",
              width: "100%",
              maxWidth: "500px",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "16px",
              }}
            >
              <h3 style={{ margin: 0, fontSize: "18px", color: "#f0f6fc" }}>
                Complete Maintenance
              </h3>
              <button
                onClick={() => setCompleteModal({ isOpen: false, record: null, work_performed: "", notes: "" })}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#8b949e",
                  fontSize: "18px",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>

            {completeError && (
              <div
                style={{
                  background: "rgba(239, 68, 68, 0.15)",
                  border: "1px solid rgba(239, 68, 68, 0.3)",
                  color: "#ef4444",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  marginBottom: "16px",
                  fontSize: "13px",
                }}
              >
                ⚠ {completeError}
              </div>
            )}

            <div
              style={{
                background: "rgba(255, 255, 255, 0.04)",
                borderRadius: "8px",
                padding: "12px 14px",
                marginBottom: "16px",
                fontSize: "13px",
              }}
            >
              <div style={{ color: "#8b949e", marginBottom: "4px" }}>
                Task: <strong style={{ color: "#e6edf3" }}>{completeModal.record?.title}</strong>
              </div>
              <div style={{ color: "#8b949e" }}>
                Computer:{" "}
                <strong style={{ color: "#e6edf3" }}>
                  {completeModal.record?.computer_hostname || `PC-${completeModal.record?.computer_id}`}
                </strong>
              </div>
            </div>

            <form onSubmit={handleCompleteSubmit}>
              <div style={{ marginBottom: "16px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    color: "#8b949e",
                    marginBottom: "6px",
                    fontWeight: "500",
                  }}
                >
                  Work Performed
                </label>
                <textarea
                  value={completeModal.work_performed}
                  onChange={(e) =>
                    setCompleteModal((prev) => ({
                      ...prev,
                      work_performed: e.target.value,
                    }))
                  }
                  placeholder="Describe the actions taken, parts replaced, or tests conducted..."
                  rows={3}
                  style={{
                    width: "100%",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#e6edf3",
                    padding: "9px 12px",
                    fontSize: "14px",
                    outline: "none",
                    resize: "vertical",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div style={{ marginBottom: "20px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    color: "#8b949e",
                    marginBottom: "6px",
                    fontWeight: "500",
                  }}
                >
                  Final Completion Notes
                </label>
                <input
                  type="text"
                  value={completeModal.notes}
                  onChange={(e) =>
                    setCompleteModal((prev) => ({
                      ...prev,
                      notes: e.target.value,
                    }))
                  }
                  placeholder="Optional follow-up notes or recommendations"
                  style={{
                    width: "100%",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#e6edf3",
                    padding: "9px 12px",
                    fontSize: "14px",
                    outline: "none",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                }}
              >
                <button
                  type="button"
                  onClick={() => setCompleteModal({ isOpen: false, record: null, work_performed: "", notes: "" })}
                  disabled={completeLoading}
                  style={{
                    background: "rgba(255, 255, 255, 0.08)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    color: "#e6edf3",
                    borderRadius: "6px",
                    padding: "9px 16px",
                    fontSize: "14px",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={completeLoading}
                  style={{
                    background: "linear-gradient(135deg, #10b981, #059669)",
                    border: "none",
                    color: "#ffffff",
                    borderRadius: "6px",
                    padding: "9px 18px",
                    fontSize: "14px",
                    fontWeight: "600",
                    cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(16, 185, 129, 0.3)",
                  }}
                >
                  {completeLoading ? "Completing..." : "Complete Task"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================
          DETAIL MODAL
      ================================================= */}
      {detailModal.isOpen && detailModal.record && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            style={{
              background: "#161b22",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: "12px",
              padding: "24px",
              width: "100%",
              maxWidth: "560px",
              maxHeight: "85vh",
              overflowY: "auto",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "20px",
                borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
                paddingBottom: "14px",
              }}
            >
              <div>
                <h3 style={{ margin: 0, fontSize: "18px", color: "#f0f6fc" }}>
                  {detailModal.record.title}
                </h3>
                <span style={{ fontSize: "12px", color: "#8b949e" }}>
                  Record #{detailModal.record.id} •{" "}
                  {detailModal.record.computer_hostname || `PC-${detailModal.record.computer_id}`}
                </span>
              </div>
              <button
                onClick={() => setDetailModal({ isOpen: false, record: null })}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#8b949e",
                  fontSize: "18px",
                  cursor: "pointer",
                }}
              >
                ✕
              </button>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                }}
              >
                <div>
                  <span style={{ fontSize: "12px", color: "#8b949e", display: "block" }}>
                    Status
                  </span>
                  <span
                    style={{
                      display: "inline-block",
                      marginTop: "4px",
                      padding: "3px 8px",
                      borderRadius: "12px",
                      fontSize: "12px",
                      fontWeight: "600",
                      ...getStatusBadgeStyle(detailModal.record.status),
                    }}
                  >
                    {formatStatusText(detailModal.record.status)}
                  </span>
                </div>

                <div>
                  <span style={{ fontSize: "12px", color: "#8b949e", display: "block" }}>
                    Type
                  </span>
                  <span
                    style={{
                      display: "inline-block",
                      marginTop: "4px",
                      padding: "3px 8px",
                      borderRadius: "12px",
                      fontSize: "12px",
                      fontWeight: "600",
                      ...getTypeBadgeStyle(detailModal.record.maintenance_type),
                    }}
                  >
                    {formatTypeText(detailModal.record.maintenance_type)}
                  </span>
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                }}
              >
                <div>
                  <span style={{ fontSize: "12px", color: "#8b949e", display: "block" }}>
                    Technician
                  </span>
                  <strong style={{ fontSize: "13px", color: "#e6edf3" }}>
                    {detailModal.record.technician_name || "Unassigned"}
                  </strong>
                </div>

                <div>
                  <span style={{ fontSize: "12px", color: "#8b949e", display: "block" }}>
                    Scheduled At
                  </span>
                  <strong style={{ fontSize: "13px", color: "#e6edf3" }}>
                    {formatDateTime(detailModal.record.scheduled_at)}
                  </strong>
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                }}
              >
                <div>
                  <span style={{ fontSize: "12px", color: "#8b949e", display: "block" }}>
                    Started At
                  </span>
                  <span style={{ fontSize: "13px", color: "#e6edf3" }}>
                    {formatDateTime(detailModal.record.started_at)}
                  </span>
                </div>

                <div>
                  <span style={{ fontSize: "12px", color: "#8b949e", display: "block" }}>
                    Completed At
                  </span>
                  <span style={{ fontSize: "13px", color: "#e6edf3" }}>
                    {formatDateTime(detailModal.record.completed_at)}
                  </span>
                </div>
              </div>

              {detailModal.record.description && (
                <div>
                  <span style={{ fontSize: "12px", color: "#8b949e", display: "block", marginBottom: "4px" }}>
                    Description
                  </span>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "13px",
                      color: "#c9d1d9",
                      background: "rgba(255, 255, 255, 0.04)",
                      padding: "10px",
                      borderRadius: "6px",
                      lineHeight: "1.5",
                    }}
                  >
                    {detailModal.record.description}
                  </p>
                </div>
              )}

              {detailModal.record.work_performed && (
                <div>
                  <span style={{ fontSize: "12px", color: "#8b949e", display: "block", marginBottom: "4px" }}>
                    Work Performed
                  </span>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "13px",
                      color: "#34d399",
                      background: "rgba(16, 185, 129, 0.08)",
                      border: "1px solid rgba(16, 185, 129, 0.2)",
                      padding: "10px",
                      borderRadius: "6px",
                      lineHeight: "1.5",
                    }}
                  >
                    {detailModal.record.work_performed}
                  </p>
                </div>
              )}

              {detailModal.record.notes && (
                <div>
                  <span style={{ fontSize: "12px", color: "#8b949e", display: "block", marginBottom: "4px" }}>
                    Notes
                  </span>
                  <p
                    style={{
                      margin: 0,
                      fontSize: "13px",
                      color: "#c9d1d9",
                      background: "rgba(255, 255, 255, 0.04)",
                      padding: "10px",
                      borderRadius: "6px",
                      lineHeight: "1.5",
                    }}
                  >
                    {detailModal.record.notes}
                  </p>
                </div>
              )}
            </div>

            <div
              style={{
                marginTop: "20px",
                display: "flex",
                justifyContent: "flex-end",
              }}
            >
              <button
                onClick={() => setDetailModal({ isOpen: false, record: null })}
                style={{
                  background: "rgba(255, 255, 255, 0.08)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  color: "#e6edf3",
                  borderRadius: "6px",
                  padding: "8px 16px",
                  fontSize: "13px",
                  cursor: "pointer",
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default MaintenanceRecords;
