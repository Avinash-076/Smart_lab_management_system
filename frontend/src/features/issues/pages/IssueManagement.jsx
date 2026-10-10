import { useState, useEffect, useMemo, useCallback } from "react";
import {
  getIssues,
  getIssueStats,
  getComputers,
  createIssue,
  updateIssue,
  resolveIssue,
  deleteIssue,
} from "../../../services/api";
import StatCard from "../../../components/ui/StatCard";
import Icon from "../../../components/ui/Icon";

function formatDateTime(dateStr) {
  if (!dateStr) return "N/A";
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return dateStr;
    return date.toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return "N/A";
  }
}

function IssueManagement() {
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

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All Status");
  const [priorityFilter, setPriorityFilter] = useState("All Priority");
  const [computerFilter, setComputerFilter] = useState("All Computers");

  // Create Issue Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    computer_id: "",
    title: "",
    description: "",
    severity: "medium",
  });
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState("");

  // Resolve Modal State
  const [resolveModal, setResolveModal] = useState({
    isOpen: false,
    issue: null,
    notes: "",
  });
  const [resolveLoading, setResolveLoading] = useState(false);

  // Detail Modal State
  const [detailModal, setDetailModal] = useState({
    isOpen: false,
    issue: null,
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

      const [issuesData, statsData, computersData] = await Promise.all([
        getIssues({ limit: 300 }),
        getIssueStats(),
        getComputers(),
      ]);

      setIssues(Array.isArray(issuesData) ? issuesData : []);

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
    } catch (err) {
      console.error("Failed to load issue data:", err);
      setError(err.message || "Failed to load issue data.");
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

        const [issuesData, statsData, computersData] = await Promise.all([
          getIssues({ limit: 300 }),
          getIssueStats(),
          getComputers(),
        ]);

        if (ignore) return;

        setIssues(Array.isArray(issuesData) ? issuesData : []);

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
      } catch (err) {
        if (!ignore) {
          console.error("Failed to load issue data:", err);
          setError(err.message || "Failed to load issue data.");
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

  // Helper to trigger transient success message
  const showSuccess = (msg) => {
    setSuccessMsg(msg);
    setTimeout(() => {
      setSuccessMsg("");
    }, 4000);
  };

  /* =====================================================
     CREATE ISSUE HANDLER
  ===================================================== */

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    if (!createForm.computer_id) {
      setCreateError("Please select a computer.");
      return;
    }
    if (!createForm.title.trim()) {
      setCreateError("Issue title is required.");
      return;
    }
    if (!createForm.description.trim()) {
      setCreateError("Issue description is required.");
      return;
    }

    try {
      setCreateLoading(true);
      setCreateError("");

      await createIssue({
        computer_id: Number(createForm.computer_id),
        title: createForm.title.trim(),
        description: createForm.description.trim(),
        severity: createForm.severity,
      });

      setIsCreateOpen(false);
      setCreateForm({
        computer_id: "",
        title: "",
        description: "",
        severity: "medium",
      });

      showSuccess("Issue reported successfully.");
      await loadData();
    } catch (err) {
      console.error("Failed to create issue:", err);
      setCreateError(err.message || "Failed to create issue.");
    } finally {
      setCreateLoading(false);
    }
  };

  /* =====================================================
     STATUS TRANSITION HANDLERS
  ===================================================== */

  const handleStatusChange = async (issue, newStatus) => {
    try {
      setActionLoadingId(issue.id);
      await updateIssue(issue.id, { status: newStatus });
      showSuccess(`Issue status updated to ${newStatus.replace("_", " ")}.`);
      await loadData();
    } catch (err) {
      console.error("Failed to update issue status:", err);
      setError(err.message || "Failed to update issue status.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleOpenResolve = (issue) => {
    setResolveModal({
      isOpen: true,
      issue,
      notes: "",
    });
  };

  const handleResolveSubmit = async (e) => {
    e.preventDefault();
    if (!resolveModal.issue) return;

    try {
      setResolveLoading(true);
      await resolveIssue(resolveModal.issue.id, resolveModal.notes.trim() || null);
      setResolveModal({ isOpen: false, issue: null, notes: "" });
      showSuccess("Issue marked as resolved.");
      await loadData();
    } catch (err) {
      console.error("Failed to resolve issue:", err);
      setError(err.message || "Failed to resolve issue.");
    } finally {
      setResolveLoading(false);
    }
  };

  const handleDelete = async (issue) => {
    if (!window.confirm(`Are you sure you want to delete issue "${issue.title}"?`)) {
      return;
    }

    try {
      setActionLoadingId(issue.id);
      await deleteIssue(issue.id);
      showSuccess("Issue deleted successfully.");
      await loadData();
    } catch (err) {
      console.error("Failed to delete issue:", err);
      setError(err.message || "Failed to delete issue.");
    } finally {
      setActionLoadingId(null);
    }
  };

  /* =====================================================
     FILTER ISSUES
  ===================================================== */

  const computerMap = useMemo(() => {
    const map = new Map();
    computers.forEach((c) => {
      map.set(c.id, c.hostname || `Computer #${c.id}`);
    });
    return map;
  }, [computers]);

  const filteredIssues = useMemo(() => {
    const searchText = search.toLowerCase().trim();

    return issues.filter((issue) => {
      const compName =
        issue.computer_hostname ||
        computerMap.get(issue.computer_id) ||
        `PC-${issue.computer_id}`;

      const matchesSearch =
        !searchText ||
        compName.toLowerCase().includes(searchText) ||
        (issue.title && issue.title.toLowerCase().includes(searchText)) ||
        (issue.description && issue.description.toLowerCase().includes(searchText));

      let matchesStatus = true;
      if (statusFilter === "Open") matchesStatus = issue.status === "open";
      else if (statusFilter === "In Progress") matchesStatus = issue.status === "in_progress";
      else if (statusFilter === "Resolved") matchesStatus = issue.status === "resolved";

      let matchesPriority = true;
      if (priorityFilter !== "All Priority") {
        matchesPriority =
          issue.severity &&
          issue.severity.toLowerCase() === priorityFilter.toLowerCase();
      }

      let matchesComputer = true;
      if (computerFilter !== "All Computers") {
        matchesComputer =
          compName === computerFilter ||
          String(issue.computer_id) === String(computerFilter);
      }

      return matchesSearch && matchesStatus && matchesPriority && matchesComputer;
    });
  }, [issues, search, statusFilter, priorityFilter, computerFilter, computerMap]);

  /* =====================================================
     RESET
  ===================================================== */

  const resetFilters = () => {
    setSearch("");
    setStatusFilter("All Status");
    setPriorityFilter("All Priority");
    setComputerFilter("All Computers");
  };

  /* =====================================================
     STYLE HELPERS
  ===================================================== */

  const getPriorityBadgeStyle = (severity) => {
    const sev = (severity || "").toLowerCase();
    if (sev === "critical") {
      return {
        background: "rgba(239, 68, 68, 0.12)",
        color: "#ef4444",
        border: "1px solid rgba(239, 68, 68, 0.3)",
      };
    }
    if (sev === "high") {
      return {
        background: "rgba(249, 115, 22, 0.12)",
        color: "#f97316",
        border: "1px solid rgba(249, 115, 22, 0.3)",
      };
    }
    if (sev === "medium") {
      return {
        background: "rgba(234, 179, 8, 0.12)",
        color: "#eab308",
        border: "1px solid rgba(234, 179, 8, 0.3)",
      };
    }
    return {
      background: "rgba(59, 130, 246, 0.12)",
      color: "#3b82f6",
      border: "1px solid rgba(59, 130, 246, 0.3)",
    };
  };

  const getStatusBadgeStyle = (statusVal) => {
    const st = (statusVal || "").toLowerCase();
    if (st === "resolved") {
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
    return {
      background: "rgba(249, 115, 22, 0.12)",
      color: "#f97316",
      border: "1px solid rgba(249, 115, 22, 0.3)",
    };
  };

  const formatStatusText = (statusVal) => {
    const st = (statusVal || "").toLowerCase();
    if (st === "in_progress") return "In Progress";
    if (st === "resolved") return "Resolved";
    return "Open";
  };

  const formatSeverityText = (severity) => {
    const s = (severity || "").toLowerCase();
    if (!s) return "Medium";
    return s.charAt(0).toUpperCase() + s.slice(1);
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
          <h2>Issue Management</h2>
          <p>Monitor and manage problems reported by laboratory computers.</p>
        </div>

        <button
          onClick={() => {
            setCreateError("");
            setIsCreateOpen(true);
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
          Report Issue
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
          icon="issue"
          title="Total Issues"
          number={stats.total}
          footer="All reported issues"
          type="blue"
        />

        <StatCard
          icon="issue"
          title="Open"
          number={stats.open}
          footer="Issues requiring attention"
          type="orange"
        />

        <StatCard
          icon="maintenance"
          title="In Progress"
          number={stats.in_progress}
          footer="Currently being handled"
          type="purple"
        />

        <StatCard
          icon="check"
          title="Resolved"
          number={stats.resolved}
          footer="Successfully resolved"
          type="green"
        />
      </div>

      {/* =================================================
          ISSUE TABLE CARD
      ================================================= */}
      <div className="table-card">
        {/* TABLE HEADER */}
        <div className="page-section-header">
          <div>
            <h3>Reported Issues</h3>
            <p>Problems reported by client agents and administrators are displayed here.</p>
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
              placeholder="Search issues, title, description or computer..."
            />
            <Icon type="search" size={18} />
          </div>

          {/* STATUS */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option>All Status</option>
            <option>Open</option>
            <option>In Progress</option>
            <option>Resolved</option>
          </select>

          {/* PRIORITY */}
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
          >
            <option>All Priority</option>
            <option>Critical</option>
            <option>High</option>
            <option>Medium</option>
            <option>Low</option>
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
          <button className="refresh" onClick={() => { resetFilters(); loadData(); }}>
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
          Showing <strong>{filteredIssues.length}</strong> issue records
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
            <p style={{ margin: 0, fontSize: "14px" }}>Loading issues...</p>
          </div>
        ) : filteredIssues.length > 0 ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th style={{ minWidth: "120px" }}>Computer</th>
                  <th style={{ minWidth: "180px" }}>Issue</th>
                  <th style={{ minWidth: "240px" }}>Description</th>
                  <th style={{ minWidth: "100px" }}>Priority</th>
                  <th style={{ minWidth: "140px" }}>Reported</th>
                  <th style={{ minWidth: "110px" }}>Status</th>
                  <th style={{ minWidth: "170px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredIssues.map((issue) => {
                  const compName =
                    issue.computer_hostname ||
                    computerMap.get(issue.computer_id) ||
                    `PC-${issue.computer_id}`;
                  const isActionLoading = actionLoadingId === issue.id;

                  return (
                    <tr key={issue.id}>
                      {/* COMPUTER */}
                      <td>
                        <strong>{compName}</strong>
                      </td>

                      {/* ISSUE TITLE */}
                      <td>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "9px",
                          }}
                        >
                          <div className="issue-icon">
                            <Icon type="issue" size={17} />
                          </div>
                          <strong>{issue.title}</strong>
                        </div>
                      </td>

                      {/* DESCRIPTION */}
                      <td>
                        <span
                          className="issue-description"
                          style={{
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
                            maxWidth: "280px",
                          }}
                        >
                          {issue.description}
                        </span>
                      </td>

                      {/* PRIORITY / SEVERITY */}
                      <td>
                        <span
                          style={{
                            display: "inline-block",
                            padding: "3px 8px",
                            borderRadius: "12px",
                            fontSize: "12px",
                            fontWeight: "600",
                            ...getPriorityBadgeStyle(issue.severity),
                          }}
                        >
                          {formatSeverityText(issue.severity)}
                        </span>
                      </td>

                      {/* REPORTED DATE */}
                      <td style={{ fontSize: "12px", color: "#8b949e" }}>
                        {formatDateTime(issue.created_at)}
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
                            ...getStatusBadgeStyle(issue.status),
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
                          {formatStatusText(issue.status)}
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
                            onClick={() => setDetailModal({ isOpen: true, issue })}
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

                          {/* Status lifecycle actions */}
                          {issue.status === "open" && (
                            <button
                              disabled={isActionLoading}
                              onClick={() => handleStatusChange(issue, "in_progress")}
                              title="Start Progress"
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

                          {issue.status !== "resolved" && (
                            <button
                              disabled={isActionLoading}
                              onClick={() => handleOpenResolve(issue)}
                              title="Resolve Issue"
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
                              Resolve
                            </button>
                          )}

                          {issue.status === "resolved" && (
                            <button
                              disabled={isActionLoading}
                              onClick={() => handleStatusChange(issue, "open")}
                              title="Reopen Issue"
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
                              Reopen
                            </button>
                          )}

                          {/* Delete */}
                          <button
                            disabled={isActionLoading}
                            onClick={() => handleDelete(issue)}
                            title="Delete Issue"
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
            <Icon type="issue" size={40} />
            <h3>No issues found</h3>
            <p>No issues match the selected filters or search keyword.</p>
            <button className="modal-button" onClick={resetFilters}>
              Clear Filters
            </button>
          </div>
        )}
      </div>

      {/* =================================================
          CREATE ISSUE MODAL
      ================================================= */}
      {isCreateOpen && (
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
                Report New Issue
              </h3>
              <button
                onClick={() => setIsCreateOpen(false)}
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

            {createError && (
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
                ⚠ {createError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit}>
              {/* COMPUTER SELECT */}
              <div style={{ marginBottom: "16px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    fontWeight: "600",
                    color: "#c9d1d9",
                    marginBottom: "6px",
                  }}
                >
                  Computer <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <select
                  value={createForm.computer_id}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, computer_id: e.target.value })
                  }
                  required
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#f0f6fc",
                    fontSize: "14px",
                  }}
                >
                  <option value="">-- Select Computer --</option>
                  {computers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.hostname || `Computer #${c.id}`} ({c.ip_address || "No IP"})
                    </option>
                  ))}
                </select>
              </div>

              {/* TITLE */}
              <div style={{ marginBottom: "16px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    fontWeight: "600",
                    color: "#c9d1d9",
                    marginBottom: "6px",
                  }}
                >
                  Issue Title <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <input
                  type="text"
                  value={createForm.title}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, title: e.target.value })
                  }
                  placeholder="e.g. High CPU Usage / Drive C Full"
                  required
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#f0f6fc",
                    fontSize: "14px",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              {/* SEVERITY */}
              <div style={{ marginBottom: "16px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    fontWeight: "600",
                    color: "#c9d1d9",
                    marginBottom: "6px",
                  }}
                >
                  Priority / Severity
                </label>
                <select
                  value={createForm.severity}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, severity: e.target.value })
                  }
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#f0f6fc",
                    fontSize: "14px",
                  }}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>

              {/* DESCRIPTION */}
              <div style={{ marginBottom: "20px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    fontWeight: "600",
                    color: "#c9d1d9",
                    marginBottom: "6px",
                  }}
                >
                  Description <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <textarea
                  rows={4}
                  value={createForm.description}
                  onChange={(e) =>
                    setCreateForm({ ...createForm, description: e.target.value })
                  }
                  placeholder="Provide details about the issue..."
                  required
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#f0f6fc",
                    fontSize: "14px",
                    fontFamily: "inherit",
                    resize: "vertical",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              {/* BUTTONS */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                }}
              >
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  style={{
                    background: "rgba(255, 255, 255, 0.08)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    color: "#c9d1d9",
                    borderRadius: "6px",
                    padding: "8px 16px",
                    fontSize: "13px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createLoading}
                  style={{
                    background: "linear-gradient(135deg, #3b82f6, #2563eb)",
                    border: "none",
                    color: "#ffffff",
                    borderRadius: "6px",
                    padding: "8px 20px",
                    fontSize: "13px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  {createLoading ? "Submitting..." : "Create Issue"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================
          RESOLVE ISSUE MODAL
      ================================================= */}
      {resolveModal.isOpen && resolveModal.issue && (
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
              maxWidth: "480px",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)",
            }}
          >
            <h3 style={{ margin: "0 0 12px", fontSize: "18px", color: "#f0f6fc" }}>
              Resolve Issue
            </h3>
            <p style={{ fontSize: "14px", color: "#8b949e", margin: "0 0 16px" }}>
              Resolving: <strong style={{ color: "#f0f6fc" }}>{resolveModal.issue.title}</strong>
            </p>

            <form onSubmit={handleResolveSubmit}>
              <div style={{ marginBottom: "20px" }}>
                <label
                  style={{
                    display: "block",
                    fontSize: "13px",
                    fontWeight: "600",
                    color: "#c9d1d9",
                    marginBottom: "6px",
                  }}
                >
                  Resolution Notes (Optional)
                </label>
                <textarea
                  rows={3}
                  value={resolveModal.notes}
                  onChange={(e) =>
                    setResolveModal({ ...resolveModal, notes: e.target.value })
                  }
                  placeholder="Describe how this issue was resolved..."
                  style={{
                    width: "100%",
                    padding: "9px 12px",
                    background: "#0d1117",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    borderRadius: "6px",
                    color: "#f0f6fc",
                    fontSize: "14px",
                    fontFamily: "inherit",
                    resize: "vertical",
                    boxSizing: "border-box",
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setResolveModal({ isOpen: false, issue: null, notes: "" })}
                  style={{
                    background: "rgba(255, 255, 255, 0.08)",
                    border: "1px solid rgba(255, 255, 255, 0.15)",
                    color: "#c9d1d9",
                    borderRadius: "6px",
                    padding: "8px 16px",
                    fontSize: "13px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resolveLoading}
                  style={{
                    background: "linear-gradient(135deg, #10b981, #059669)",
                    border: "none",
                    color: "#ffffff",
                    borderRadius: "6px",
                    padding: "8px 20px",
                    fontSize: "13px",
                    fontWeight: "600",
                    cursor: "pointer",
                  }}
                >
                  {resolveLoading ? "Saving..." : "Mark Resolved"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================
          ISSUE DETAILS MODAL
      ================================================= */}
      {detailModal.isOpen && detailModal.issue && (
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
              maxWidth: "540px",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: "16px",
              }}
            >
              <div>
                <h3 style={{ margin: "0 0 6px", fontSize: "18px", color: "#f0f6fc" }}>
                  {detailModal.issue.title}
                </h3>
                <span
                  style={{
                    display: "inline-block",
                    padding: "2px 8px",
                    borderRadius: "10px",
                    fontSize: "11px",
                    fontWeight: "600",
                    ...getStatusBadgeStyle(detailModal.issue.status),
                  }}
                >
                  {formatStatusText(detailModal.issue.status)}
                </span>
              </div>
              <button
                onClick={() => setDetailModal({ isOpen: false, issue: null })}
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

            <div style={{ fontSize: "13px", color: "#c9d1d9", display: "grid", gap: "12px", marginBottom: "20px" }}>
              <div>
                <strong style={{ color: "#8b949e" }}>Computer: </strong>
                {detailModal.issue.computer_hostname ||
                  computerMap.get(detailModal.issue.computer_id) ||
                  `PC-${detailModal.issue.computer_id}`}
              </div>
              <div>
                <strong style={{ color: "#8b949e" }}>Priority / Severity: </strong>
                {formatSeverityText(detailModal.issue.severity)}
              </div>
              <div>
                <strong style={{ color: "#8b949e" }}>Source: </strong>
                {detailModal.issue.source || "admin"}
              </div>
              <div>
                <strong style={{ color: "#8b949e" }}>Reported At: </strong>
                {formatDateTime(detailModal.issue.created_at)}
              </div>
              <div>
                <strong style={{ color: "#8b949e" }}>Description: </strong>
                <p
                  style={{
                    margin: "4px 0 0",
                    background: "#0d1117",
                    padding: "10px 12px",
                    borderRadius: "6px",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    color: "#f0f6fc",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {detailModal.issue.description}
                </p>
              </div>

              {detailModal.issue.resolution_notes && (
                <div>
                  <strong style={{ color: "#10b981" }}>Resolution Notes: </strong>
                  <p
                    style={{
                      margin: "4px 0 0",
                      background: "rgba(16, 185, 129, 0.05)",
                      padding: "10px 12px",
                      borderRadius: "6px",
                      border: "1px solid rgba(16, 185, 129, 0.2)",
                      color: "#e6edf3",
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {detailModal.issue.resolution_notes}
                  </p>
                </div>
              )}

              {detailModal.issue.resolved_at && (
                <div>
                  <strong style={{ color: "#8b949e" }}>Resolved At: </strong>
                  {formatDateTime(detailModal.issue.resolved_at)}
                </div>
              )}
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button
                onClick={() => setDetailModal({ isOpen: false, issue: null })}
                style={{
                  background: "rgba(255, 255, 255, 0.08)",
                  border: "1px solid rgba(255, 255, 255, 0.15)",
                  color: "#c9d1d9",
                  borderRadius: "6px",
                  padding: "8px 18px",
                  fontSize: "13px",
                  fontWeight: "600",
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

export default IssueManagement;