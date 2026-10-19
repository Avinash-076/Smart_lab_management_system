import { useState, useEffect, useMemo, useCallback } from "react";
import { getComputers } from "../../../services/computerService";
import {
  getMaintenanceRecords,
  getMaintenanceStats,
  createMaintenanceRecord,
  updateMaintenanceRecord,
  completeMaintenanceRecord,
  deleteMaintenanceRecord,
} from "../../../services/maintenanceService";

export function useMaintenanceRecords() {
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

  // Action in-progress ID
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const showSuccess = useCallback((msg) => {
    setSuccessMsg(msg);
    setTimeout(() => {
      setSuccessMsg("");
    }, 4000);
  }, []);

  /* =====================================================
     DATA FETCHING
  ===================================================== */
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const [recordsData, statsData, computersData] = await Promise.all([
        getMaintenanceRecords({ limit: 500 }),
        getMaintenanceStats(),
        getComputers(),
      ]);

      const fetchedRecords = Array.isArray(recordsData) ? recordsData : [];
      setRecords(fetchedRecords);

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

  // Initial load
  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        setLoading(true);
        setError("");
        const [recordsData, statsData, computersData] = await Promise.all([
          getMaintenanceRecords({ limit: 500 }),
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
        if (!ignore) setLoading(false);
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, []);

  /* =====================================================
     ACTIONS & LIFECYCLE
  ===================================================== */
  const handleScheduleSubmit = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
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
        scheduled_at: scheduleForm.scheduled_at
          ? new Date(scheduleForm.scheduled_at).toISOString()
          : new Date().toISOString(),
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
    if (e && e.preventDefault) e.preventDefault();
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
     FILTERING & COMPUTER MAP
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

  const resetFilters = () => {
    setSearch("");
    setStatusFilter("All Status");
    setTypeFilter("All Types");
    setComputerFilter("All Computers");
  };

  return {
    records,
    stats,
    computers,
    computerMap,
    loading,
    error,
    successMsg,
    // Filters
    search,
    setSearch,
    statusFilter,
    setStatusFilter,
    typeFilter,
    setTypeFilter,
    computerFilter,
    setComputerFilter,
    filteredRecords,
    resetFilters,
    // Actions & Modals
    loadData,
    handleStatusChange,
    handleDelete,
    // Schedule Modal
    isScheduleOpen,
    setIsScheduleOpen,
    scheduleForm,
    setScheduleForm,
    scheduleLoading,
    scheduleError,
    handleScheduleSubmit,
    // Complete Modal
    completeModal,
    setCompleteModal,
    completeLoading,
    completeError,
    handleOpenComplete,
    handleCompleteSubmit,
    // Details Modal
    detailModal,
    setDetailModal,
    actionLoadingId,
  };
}
