import { useState, useEffect, useMemo, useCallback } from "react";
import { getComputers } from "../../../services/computerService";
import {
  getIssues,
  getIssueStats,
  createIssue,
  updateIssue,
  resolveIssue,
  deleteIssue,
} from "../../../services/issueService";
import { createDashboardWebSocket } from "../../../services/websocketManager";
import { filterByDateRange } from "../utils/issueUtils";

export function useIssueManagement() {
  const [issues, setIssues] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    open: 0,
    in_progress: 0,
    resolved: 0,
  });
  const [computers, setComputers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Selected issue for inspector panel (defaults to first row once loaded)
  const [selectedIssueId, setSelectedIssueId] = useState(null);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All Status");
  const [priorityFilter, setPriorityFilter] = useState("All Priority");
  const [computerFilter, setComputerFilter] = useState("All Computers");
  const [dateRangeFilter, setDateRangeFilter] = useState("Last 30 Days");

  // Modals
  const [isReportOpen, setIsReportOpen] = useState(false);
  const [resolveModal, setResolveModal] = useState({ isOpen: false, issue: null });
  const [editModal, setEditModal] = useState({ isOpen: false, issue: null });
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [realtimeAlert, setRealtimeAlert] = useState(null);

  const showSuccess = useCallback((msg) => {
    setSuccessMsg(msg);
    setTimeout(() => {
      setSuccessMsg("");
    }, 4000);
  }, []);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const [issuesData, statsData, computersData] = await Promise.all([
        getIssues({ limit: 500 }),
        getIssueStats(),
        getComputers(),
      ]);

      const fetchedIssues = Array.isArray(issuesData) ? issuesData : [];
      setIssues(fetchedIssues);

      if (statsData && typeof statsData === "object") {
        setStats({
          total: statsData.total || 0,
          open: statsData.open || 0,
          in_progress: statsData.in_progress || 0,
          resolved: statsData.resolved || 0,
        });
      }

      if (Array.isArray(computersData)) {
        setComputers(computersData);
      }

      // Preserve active selection if it still exists in the newly fetched issues
      setSelectedIssueId((prevId) => {
        if (prevId && fetchedIssues.some((i) => i.id === prevId)) {
          return prevId;
        }
        return null;
      });
    } catch (err) {
      console.error("Failed to load issue data:", err);
      setError(err.message || "Failed to load issue data.");
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
        const [issuesData, statsData, computersData] = await Promise.all([
          getIssues({ limit: 500 }),
          getIssueStats(),
          getComputers(),
        ]);
        if (ignore) return;
        const fetched = Array.isArray(issuesData) ? issuesData : [];
        setIssues(fetched);
        if (statsData && typeof statsData === "object") {
          setStats({
            total: statsData.total || 0,
            open: statsData.open || 0,
            in_progress: statsData.in_progress || 0,
            resolved: statsData.resolved || 0,
          });
        }
        if (Array.isArray(computersData)) setComputers(computersData);
        // Do not auto-select first issue: drawer stays closed by default
      } catch (err) {
        if (!ignore) {
          console.error("Failed to load issue data:", err);
          setError(err.message || "Failed to load issue data.");
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

  // WebSocket Live Updates
  useEffect(() => {
    let timer = null;
    const wsClient = createDashboardWebSocket({
      onMessage: (message) => {
        if (!message) return;

        if (message.type === "issue_created") {
          loadData();
          const issueObj = message.issue || {};
          setRealtimeAlert({
            type: "created",
            id: issueObj.id || Date.now(),
            title: issueObj.title || "New Issue Detected",
            computer: message.computer_hostname || `Computer #${message.computer_id}`,
            severity: issueObj.severity || "high",
            time: new Date().toLocaleTimeString(),
          });
          if (timer) clearTimeout(timer);
          timer = setTimeout(() => setRealtimeAlert(null), 9000);
        } else if (message.type === "issue_resolved") {
          loadData();
          setRealtimeAlert({
            type: "resolved",
            id: message.issue_id || Date.now(),
            title: message.title || "Issue Auto-Resolved",
            computer: `Computer #${message.computer_id}`,
            notes: message.resolution_notes,
            time: new Date().toLocaleTimeString(),
          });
          if (timer) clearTimeout(timer);
          timer = setTimeout(() => setRealtimeAlert(null), 9000);
        } else if (message.type === "issue_updated") {
          loadData();
        }
      },
    });

    return () => {
      if (timer) clearTimeout(timer);
      wsClient.close();
    };
  }, [loadData]);

  // Computer Map
  const computerMap = useMemo(() => {
    const map = new Map();
    computers.forEach((c) => {
      map.set(c.id, c.hostname || `Computer #${c.id}`);
    });
    return map;
  }, [computers]);

  // Filtered Issues
  const filteredIssues = useMemo(() => {
    const q = search.toLowerCase().trim();

    return issues.filter((issue) => {
      const compName =
        issue.computer_hostname ||
        computerMap.get(issue.computer_id) ||
        `PC-${issue.computer_id}`;

      // 1. Search text filter
      const matchesSearch =
        !q ||
        compName.toLowerCase().includes(q) ||
        (issue.title && issue.title.toLowerCase().includes(q)) ||
        (issue.description && issue.description.toLowerCase().includes(q));

      if (!matchesSearch) return false;

      // 2. Status filter
      if (statusFilter === "Open" && issue.status !== "open") return false;
      if (statusFilter === "In Progress" && issue.status !== "in_progress") return false;
      if (statusFilter === "Resolved" && issue.status !== "resolved") return false;

      // 3. Priority filter
      if (
        priorityFilter !== "All Priority" &&
        issue.severity?.toLowerCase() !== priorityFilter.toLowerCase()
      ) {
        return false;
      }

      // 4. Computer filter
      if (
        computerFilter !== "All Computers" &&
        compName !== computerFilter &&
        String(issue.computer_id) !== String(computerFilter)
      ) {
        return false;
      }

      // 5. Date Range filter
      if (!filterByDateRange(issue.created_at, dateRangeFilter)) {
        return false;
      }

      return true;
    });
  }, [issues, search, statusFilter, priorityFilter, computerFilter, dateRangeFilter, computerMap]);

  // Currently selected issue object
  const selectedIssue = useMemo(() => {
    if (!selectedIssueId) return null;
    return issues.find((i) => i.id === selectedIssueId) || null;
  }, [issues, selectedIssueId]);

  // Selected computer object
  const selectedComputer = useMemo(() => {
    if (!selectedIssue) return null;
    return computers.find((c) => c.id === selectedIssue.computer_id) || null;
  }, [computers, selectedIssue]);

  /* =====================================================
     ACTIONS
  ===================================================== */

  const handleCreateIssue = async (formData) => {
    try {
      setActionLoadingId("create");
      await createIssue(formData);
      setIsReportOpen(false);
      showSuccess("Issue reported successfully.");
      await loadData();
    } catch (err) {
      console.error("Failed to create issue:", err);
      setError(err.message || "Failed to create issue.");
      throw err;
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleStatusChange = async (issue, newStatus) => {
    try {
      setActionLoadingId(issue.id);
      await updateIssue(issue.id, { status: newStatus });
      showSuccess(`Issue #${issue.id} marked as ${newStatus.replace("_", " ")}.`);
      await loadData();
    } catch (err) {
      console.error("Failed to update status:", err);
      setError(err.message || "Failed to update status.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleResolveIssue = async (issueId, resolutionNotes) => {
    try {
      setActionLoadingId(issueId);
      await resolveIssue(issueId, resolutionNotes);
      setResolveModal({ isOpen: false, issue: null });
      showSuccess(`Issue #${issueId} resolved.`);
      await loadData();
    } catch (err) {
      console.error("Failed to resolve issue:", err);
      setError(err.message || "Failed to resolve issue.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleUpdateIssue = async (issueId, patchData) => {
    try {
      setActionLoadingId(issueId);
      await updateIssue(issueId, patchData);
      setEditModal({ isOpen: false, issue: null });
      showSuccess(`Issue #${issueId} updated successfully.`);
      await loadData();
    } catch (err) {
      console.error("Failed to update issue:", err);
      setError(err.message || "Failed to update issue.");
      throw err;
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDeleteIssue = async (issue) => {
    if (!window.confirm(`Are you sure you want to delete issue "${issue.title}"?`)) {
      return;
    }
    try {
      setActionLoadingId(issue.id);
      await deleteIssue(issue.id);
      showSuccess(`Issue #${issue.id} deleted successfully.`);
      if (selectedIssueId === issue.id) {
        setSelectedIssueId(null);
      }
      await loadData();
    } catch (err) {
      console.error("Failed to delete issue:", err);
      setError(err.message || "Failed to delete issue.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleAddComment = async (issue, commentText) => {
    try {
      setActionLoadingId(issue.id);
      const updatedNotes = issue.resolution_notes
        ? `${issue.resolution_notes}\n[Admin Remark - ${new Date().toLocaleTimeString()}]: ${commentText}`
        : `[Admin Remark - ${new Date().toLocaleTimeString()}]: ${commentText}`;

      await updateIssue(issue.id, { resolution_notes: updatedNotes });
      showSuccess("Comment added to issue record.");
      await loadData();
    } catch (err) {
      console.error("Failed to add comment:", err);
      setError(err.message || "Failed to add comment.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const resetFilters = () => {
    setSearch("");
    setStatusFilter("All Status");
    setPriorityFilter("All Priority");
    setComputerFilter("All Computers");
    setDateRangeFilter("Last 30 Days");
  };

  return {
    issues,
    stats,
    computers,
    computerMap,
    loading,
    error,
    successMsg,
    selectedIssue,
    selectedComputer,
    setSelectedIssue: (issue) => setSelectedIssueId(issue ? issue.id : null),
    // Filter states
    search,
    setSearch,
    statusFilter,
    setStatusFilter,
    priorityFilter,
    setPriorityFilter,
    computerFilter,
    setComputerFilter,
    dateRangeFilter,
    setDateRangeFilter,
    filteredIssues,
    resetFilters,
    // Actions & Modals
    loadData,
    handleCreateIssue,
    handleStatusChange,
    handleResolveIssue,
    handleUpdateIssue,
    handleDeleteIssue,
    handleAddComment,
    isReportOpen,
    setIsReportOpen,
    resolveModal,
    setResolveModal,
    editModal,
    setEditModal,
    actionLoadingId,
    realtimeAlert,
    setRealtimeAlert,
  };
}
