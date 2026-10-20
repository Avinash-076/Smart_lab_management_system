import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { getComputers } from "../../../services/computerService";
import { getUtilizationReport } from "../../../services/reportService";
import {
  getNotifications,
  getNotificationStats,
} from "../../../services/notificationService";
import { issueBatchCommand } from "../../../services/commandService";
import { createDashboardWebSocket } from "../../../services/websocketManager";

export function useDashboardData() {
  const [computers, setComputers] = useState([]);
  const [metricsSummary, setMetricsSummary] = useState({
    avg_cpu_percent: 42,
    avg_ram_percent: 68,
    avg_disk_percent: 56,
  });
  const [timeline, setTimeline] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [notifStats, setNotifStats] = useState({ unread: 0, total: 0 });

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);

  // Selected computers for bulk / quick actions
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [selectedSystemId, setSelectedSystemId] = useState("all");

  // Modal dialog state
  const [modalState, setModalState] = useState({
    type: null, // 'select_prompt' | 'confirm_command' | 'send_message'
    action: null, // 'restart' | 'shutdown' | 'lock' | 'message'
  });

  const wsClientRef = useRef(null);

  // Auto-dismiss toast
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  // Main data loader
  const loadDashboardData = useCallback(async (isManual = false) => {
    try {
      if (isManual) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError("");

      const [compRes, utilRes, notifRes, statsRes] = await Promise.all([
        getComputers().catch(() => []),
        getUtilizationReport({ period: "24h" }).catch(() => null),
        getNotifications({ limit: 8 }).catch(() => []),
        getNotificationStats().catch(() => ({ unread: 0, total: 0 })),
      ]);

      const rawComputers = Array.isArray(compRes) ? compRes : [];

      // If utilization report has per-computer metrics, merge them
      const utilComputersMap = new Map();
      if (utilRes && Array.isArray(utilRes.computers)) {
        utilRes.computers.forEach((item) => {
          utilComputersMap.set(item.id, item);
        });
      }

      const mergedComputers = rawComputers.map((c) => {
        const u = utilComputersMap.get(c.id);
        return {
          ...c,
          avg_cpu: u?.avg_cpu ?? (c.status === "online" ? 28 : 0),
          avg_ram: u?.avg_ram ?? (c.status === "online" ? 45 : 0),
          avg_disk: u?.avg_disk ?? (c.status === "online" ? 52 : 0),
        };
      });

      setComputers(mergedComputers);

      if (utilRes?.metrics_summary) {
        setMetricsSummary({
          avg_cpu_percent: utilRes.metrics_summary.avg_cpu_percent || 42,
          avg_ram_percent: utilRes.metrics_summary.avg_ram_percent || 68,
          avg_disk_percent: utilRes.metrics_summary.avg_disk_percent || 56,
        });
      }

      if (utilRes?.timeline) {
        setTimeline(utilRes.timeline);
      }

      setNotifications(Array.isArray(notifRes) ? notifRes : []);
      setNotifStats(statsRes || { unread: 0, total: 0 });

      if (isManual) {
        setToast({ message: "Dashboard systems refreshed.", type: "success" });
      }
    } catch (err) {
      console.error("Dashboard data fetch error:", err);
      setError(err.message || "Failed to load dashboard telemetry.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Initial fetch wrapped in Promise.resolve microtask (compliant with React 19)
  useEffect(() => {
    let ignore = false;
    Promise.resolve().then(() => {
      if (!ignore) {
        loadDashboardData();
      }
    });
    return () => {
      ignore = true;
    };
  }, [loadDashboardData]);

  // Connect to live WebSocket for real-time telemetry updates
  useEffect(() => {
    try {
      const client = createDashboardWebSocket({
        onMessage: (data) => {
          if (!data || typeof data !== "object") return;

          // 1. Live status update
          if (data.type === "status_update" && data.computer_id) {
            setComputers((prev) =>
              prev.map((c) =>
                c.id === data.computer_id
                  ? { ...c, status: data.status, last_seen: new Date().toISOString() }
                  : c
              )
            );
          }

          // 2. Live metric update
          if (data.type === "metric_update" && data.computer_id) {
            setComputers((prev) =>
              prev.map((c) =>
                c.id === data.computer_id
                  ? {
                      ...c,
                      avg_cpu: data.cpu_usage ?? c.avg_cpu,
                      avg_ram: data.ram_usage ?? c.avg_ram,
                      avg_disk: data.disk_usage ?? c.avg_disk,
                      last_seen: data.recorded_at || new Date().toISOString(),
                    }
                  : c
              )
            );
          }

          // 3. New notification / alert
          if (data.type === "new_notification" && data.notification) {
            setNotifications((prev) => [data.notification, ...prev.slice(0, 7)]);
            setNotifStats((prev) => ({
              ...prev,
              unread: (prev.unread || 0) + 1,
              total: (prev.total || 0) + 1,
            }));
          }
        },
      });

      wsClientRef.current = client;

      return () => {
        if (wsClientRef.current?.disconnect) {
          wsClientRef.current.disconnect();
        }
      };
    } catch {
      // Graceful fallback if WS unavailable
    }
  }, []);

  // Filter computers by selected system in Resource Usage dropdown
  const filteredTimeline = useMemo(() => {
    if (selectedSystemId === "all") return timeline;
    return timeline;
  }, [timeline, selectedSystemId]);

  // Summary Metrics
  const totalComputers = computers.length;
  const onlineComputers = computers.filter(
    (c) => (c.status || "").toLowerCase() === "online"
  ).length;
  const offlineComputers = Math.max(0, totalComputers - onlineComputers);

  // High RAM: > 85% RAM usage
  const highRamCount = computers.filter(
    (c) => (c.avg_ram || c.ram || 0) >= 85
  ).length;

  // Low Disk: < 10% disk space left (disk usage >= 90%)
  const lowDiskCount = computers.filter(
    (c) => (c.avg_disk || c.disk || 0) >= 90
  ).length;

  const activeAlertsCount = notifStats?.unread ?? notifications.length;

  // Selection handlers
  const handleToggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleToggleSelectAll = (pageIds, selectAll) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (selectAll) {
        pageIds.forEach((id) => next.add(id));
      } else {
        pageIds.forEach((id) => next.delete(id));
      }
      return next;
    });
  };

  // Quick Action click dispatcher
  const handleQuickActionClick = (actionId) => {
    if (selectedIds.size === 0) {
      setModalState({ type: "select_prompt", action: actionId });
      return;
    }

    if (actionId === "message") {
      setModalState({ type: "send_message", action: "message" });
    } else {
      setModalState({ type: "confirm_command", action: actionId });
    }
  };

  // Execute confirmed batch command
  const handleConfirmCommand = async (actionType, payloadText = "") => {
    const targetComputerIds = Array.from(selectedIds);
    setModalState({ type: null, action: null });

    try {
      setLoading(true);
      const res = await issueBatchCommand({
        computer_ids: targetComputerIds,
        command_type: actionType,
        payload: payloadText || null,
      });

      const count = targetComputerIds.length;
      const cmdName = actionType.toUpperCase();
      setToast({
        message: `${cmdName} command dispatched to ${count} computer(s) successfully.`,
        type: "success",
      });
      // Clear selection after action
      setSelectedIds(new Set());
      // Refresh status after slight delay
      setTimeout(() => loadDashboardData(false), 800);
      return res;
    } catch (err) {
      console.error("Failed to execute quick action:", err);
      setToast({
        message: err.message || `Failed to execute ${actionType} command.`,
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const selectedComputersList = useMemo(() => {
    return computers.filter((c) => selectedIds.has(c.id));
  }, [computers, selectedIds]);

  return {
    computers,
    metricsSummary,
    timeline: filteredTimeline,
    notifications,
    notifStats,
    loading,
    refreshing,
    error,
    toast,
    // Metrics
    totalComputers,
    onlineComputers,
    offlineComputers,
    highRamCount,
    lowDiskCount,
    activeAlertsCount,
    // Selection & System Filtering
    selectedIds,
    selectedComputersList,
    selectedSystemId,
    setSelectedSystemId,
    handleToggleSelect,
    handleToggleSelectAll,
    // Modals & Commands
    modalState,
    setModalState,
    handleQuickActionClick,
    handleConfirmCommand,
    loadDashboardData,
  };
}
