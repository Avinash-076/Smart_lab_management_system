import { useState, useEffect, useCallback } from "react";
import StatCard from "../../../components/ui/StatCard";
import Icon from "../../../components/ui/Icon";
import { getAuditLogs, getAuditLogDetails } from "../../../services/api";

function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(25);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("");
  const [resultFilter, setResultFilter] = useState("");
  const [targetTypeFilter, setTargetTypeFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // Inspection Modal
  const [selectedLog, setSelectedLog] = useState(null);

  // Stats
  const [stats, setStats] = useState({
    total: 0,
    success: 0,
    failure: 0,
    commands: 0,
  });

  const loadLogs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        page,
        limit,
      };
      if (search.trim()) params.search = search.trim();
      if (actionFilter) params.action = actionFilter;
      if (resultFilter) params.result = resultFilter;
      if (targetTypeFilter) params.target_type = targetTypeFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const data = await getAuditLogs(params);
      setLogs(data.items || []);
      setTotalCount(data.total || 0);
      setTotalPages(data.total_pages || 1);

      if (page === 1 && !actionFilter && !resultFilter && !targetTypeFilter && !search) {
        const successData = await getAuditLogs({ limit: 1, result: "success" });
        const failureData = await getAuditLogs({ limit: 1, result: "failure" });
        const commandData = await getAuditLogs({ limit: 1, search: "COMMAND" });
        setStats({
          total: data.total || 0,
          success: successData.total || 0,
          failure: failureData.total || 0,
          commands: commandData.total || 0,
        });
      }
    } catch (err) {
      setError(err.message || "Failed to load audit logs");
    } finally {
      setLoading(false);
    }
  }, [page, limit, search, actionFilter, resultFilter, targetTypeFilter, dateFrom, dateTo]);

  useEffect(() => {
    let active = true;
    async function init() {
      try {
        const params = {
          page,
          limit,
        };
        if (search.trim()) params.search = search.trim();
        if (actionFilter) params.action = actionFilter;
        if (resultFilter) params.result = resultFilter;
        if (targetTypeFilter) params.target_type = targetTypeFilter;
        if (dateFrom) params.date_from = dateFrom;
        if (dateTo) params.date_to = dateTo;

        const data = await getAuditLogs(params);
        if (active) {
          setLogs(data.items || []);
          setTotalCount(data.total || 0);
          setTotalPages(data.total_pages || 1);
          setLoading(false);
        }
      } catch (err) {
        if (active) {
          setError(err.message || "Failed to load audit logs");
          setLoading(false);
        }
      }
    }

    init();
    return () => {
      active = false;
    };
  }, [page, limit, search, actionFilter, resultFilter, targetTypeFilter, dateFrom, dateTo]);

  const handleOpenDetail = async (logId) => {
    try {
      const detail = await getAuditLogDetails(logId);
      setSelectedLog(detail);
    } catch (err) {
      setError(err.message || "Failed to load event details");
    }
  };

  const handleCloseDetail = () => {
    setSelectedLog(null);
  };

  const handleResetFilters = () => {
    setSearch("");
    setActionFilter("");
    setResultFilter("");
    setTargetTypeFilter("");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  };

  const formatDate = (isoString) => {
    if (!isoString) return "-";
    try {
      const d = new Date(isoString);
      return d.toLocaleString(undefined, {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  const getActionBadgeStyle = (action) => {
    const act = (action || "").toUpperCase();
    if (act.includes("COMMAND") || act.includes("ISSUE_COMMAND")) {
      return { background: "#eff6ff", color: "#1d4ed8", border: "1px solid #bfdbfe" };
    }
    if (act.includes("LOGIN") || act.includes("AUTH")) {
      return { background: "#ecfdf5", color: "#047857", border: "1px solid #a7f3d0" };
    }
    if (act.includes("USER") || act.includes("ROLE")) {
      return { background: "#faf5ff", color: "#6b21a8", border: "1px solid #e9d5ff" };
    }
    if (act.includes("COMPUTER") || act.includes("AGENT")) {
      return { background: "#fffbeb", color: "#b45309", border: "1px solid #fde68a" };
    }
    return { background: "#f1f5f9", color: "#475569", border: "1px solid #e2e8f0" };
  };

  return (
    <div className="content">
      {/* PAGE TOP */}
      <div className="page-top">
        <div>
          <h2>Audit Logs & Remote Trail</h2>
          <p>Complete traceability and security audit trail for all operations across the laboratory.</p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            className="refresh"
            onClick={() => loadLogs()}
            disabled={loading}
          >
            <Icon type="refresh" size={16} />
            {loading ? "Refreshing..." : "Refresh Logs"}
          </button>
        </div>
      </div>

      {/* STAT CARDS */}
      <div className="cards">
        <StatCard
          icon="audit"
          title="Total Events"
          number={stats.total}
          footer="All recorded operations"
          type="blue"
        />
        <StatCard
          icon="software"
          title="Successful Operations"
          number={stats.success}
          footer="Completed without error"
          type="green"
        />
        <StatCard
          icon="issue"
          title="Security & Failures"
          number={stats.failure}
          footer="Rejected or failed actions"
          type="red"
        />
        <StatCard
          icon="computer"
          title="Remote Commands"
          number={stats.commands}
          footer="Dispatched & executed"
          type="purple"
        />
      </div>

      {/* AUDIT LOG EXPLORER SECTION */}
      <div className="page-section" style={{ background: "#ffffff", borderRadius: "10px", padding: "20px", border: "1px solid #e2e8f0", marginTop: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px", flexWrap: "wrap", gap: "12px" }}>
          <div>
            <h3 style={{ margin: 0, fontSize: "16px", color: "#1e293b", fontWeight: 700 }}>
              Audit Event Explorer
            </h3>
            <p style={{ margin: "4px 0 0", fontSize: "13px", color: "#64748b" }}>
              Filter by actor, action type, target computer, outcome, and timestamp range.
            </p>
          </div>
          {(search || actionFilter || resultFilter || targetTypeFilter || dateFrom || dateTo) && (
            <button
              type="button"
              onClick={handleResetFilters}
              style={{
                background: "#f1f5f9",
                border: "1px solid #cbd5e1",
                borderRadius: "6px",
                padding: "6px 12px",
                fontSize: "12px",
                color: "#475569",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              Clear Filters
            </button>
          )}
        </div>

        {/* FILTERS BAR */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "12px", marginBottom: "18px", background: "#f8fafc", padding: "14px", borderRadius: "8px", border: "1px solid #edf0f4" }}>
          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "#64748b", marginBottom: "4px" }}>Search Keyword</label>
            <input
              type="text"
              placeholder="Action, actor, IP..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              style={{ width: "100%", padding: "7px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", boxSizing: "border-box" }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "#64748b", marginBottom: "4px" }}>Outcome</label>
            <select
              value={resultFilter}
              onChange={(e) => { setResultFilter(e.target.value); setPage(1); }}
              style={{ width: "100%", padding: "7px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", boxSizing: "border-box", background: "#ffffff" }}
            >
              <option value="">All Outcomes</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "#64748b", marginBottom: "4px" }}>Target Resource</label>
            <select
              value={targetTypeFilter}
              onChange={(e) => { setTargetTypeFilter(e.target.value); setPage(1); }}
              style={{ width: "100%", padding: "7px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", boxSizing: "border-box", background: "#ffffff" }}
            >
              <option value="">All Resources</option>
              <option value="COMPUTER">Computer</option>
              <option value="COMMAND">Remote Command</option>
              <option value="USER">User</option>
              <option value="ISSUE">Issue</option>
              <option value="MAINTENANCE">Maintenance</option>
            </select>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "#64748b", marginBottom: "4px" }}>From Date</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => { setDateFrom(e.target.value); setPage(1); }}
              style={{ width: "100%", padding: "7px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", boxSizing: "border-box" }}
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "11px", fontWeight: 600, color: "#64748b", marginBottom: "4px" }}>To Date</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => { setDateTo(e.target.value); setPage(1); }}
              style={{ width: "100%", padding: "7px 10px", borderRadius: "6px", border: "1px solid #cbd5e1", fontSize: "12px", boxSizing: "border-box" }}
            />
          </div>
        </div>

        {/* ERROR STATE */}
        {error && (
          <div style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "6px", color: "#dc2626", marginBottom: "16px", fontSize: "13px" }}>
            🚨 {error}
          </div>
        )}

        {/* TABLE */}
        <div style={{ overflowX: "auto", border: "1px solid #edf0f4", borderRadius: "8px" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px", textAlign: "left" }}>
            <thead>
              <tr style={{ background: "#f8fafc", borderBottom: "1px solid #edf0f4", color: "#64748b", fontWeight: 600, textTransform: "uppercase", fontSize: "11px", letterSpacing: "0.5px" }}>
                <th style={{ padding: "12px 16px" }}>ID</th>
                <th style={{ padding: "12px 16px" }}>Timestamp</th>
                <th style={{ padding: "12px 16px" }}>Actor</th>
                <th style={{ padding: "12px 16px" }}>Action Code</th>
                <th style={{ padding: "12px 16px" }}>Target</th>
                <th style={{ padding: "12px 16px" }}>Outcome</th>
                <th style={{ padding: "12px 16px" }}>Source IP</th>
                <th style={{ padding: "12px 16px", textAlign: "right" }}>Inspect</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{ padding: "36px", textAlign: "center", color: "#64748b" }}>
                    Loading audit records...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ padding: "36px", textAlign: "center", color: "#64748b" }}>
                    No audit records found matching the active criteria.
                  </td>
                </tr>
              ) : (
                logs.map((entry) => {
                  const badge = getActionBadgeStyle(entry.action);
                  return (
                    <tr
                      key={entry.id}
                      style={{ borderBottom: "1px solid #edf0f4", transition: "background 0.15s" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "#f8fafc")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      <td style={{ padding: "12px 16px", fontWeight: 700, color: "#334155" }}>
                        #{entry.id}
                      </td>
                      <td style={{ padding: "12px 16px", color: "#64748b", whiteSpace: "nowrap" }}>
                        {formatDate(entry.created_at)}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        {entry.username ? (
                          <span style={{ fontWeight: 600, color: "#0f172a" }}>{entry.username}</span>
                        ) : entry.user_id ? (
                          <span style={{ color: "#64748b" }}>User #{entry.user_id}</span>
                        ) : (
                          <span style={{ padding: "2px 6px", borderRadius: "4px", background: "#f1f5f9", color: "#475569", fontSize: "10px", fontWeight: 600 }}>SYSTEM / AGENT</span>
                        )}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <span style={{ padding: "3px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 600, display: "inline-block", ...badge }}>
                          {entry.action}
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px", color: "#475569" }}>
                        {entry.target_type ? (
                          <span>
                            {entry.target_type} {entry.target_id ? `(#${entry.target_id})` : ""}
                          </span>
                        ) : (
                          <span style={{ color: "#94a3b8" }}>—</span>
                        )}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <span
                          style={{
                            padding: "3px 8px",
                            borderRadius: "4px",
                            fontSize: "10px",
                            fontWeight: 700,
                            textTransform: "uppercase",
                            background: entry.result === "success" ? "#dcfce7" : "#fee2e2",
                            color: entry.result === "success" ? "#15803d" : "#b91c1c",
                          }}
                        >
                          {entry.result}
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px", color: "#64748b", fontFamily: "monospace", fontSize: "11px" }}>
                        {entry.ip_address || "—"}
                      </td>
                      <td style={{ padding: "12px 16px", textAlign: "right" }}>
                        <button
                          type="button"
                          onClick={() => handleOpenDetail(entry.id)}
                          style={{
                            background: "#f8fafc",
                            border: "1px solid #cbd5e1",
                            borderRadius: "4px",
                            padding: "4px 8px",
                            fontSize: "11px",
                            color: "#334155",
                            cursor: "pointer",
                            fontWeight: 600,
                          }}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* PAGINATION */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "16px", flexWrap: "wrap", gap: "12px" }}>
          <div style={{ fontSize: "12px", color: "#64748b" }}>
            Showing <strong>{logs.length}</strong> of <strong>{totalCount}</strong> audit events (Page {page} of {totalPages})
          </div>
          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
            <select
              value={limit}
              onChange={(e) => { setLimit(Number(e.target.value)); setPage(1); }}
              style={{ padding: "4px 8px", borderRadius: "4px", border: "1px solid #cbd5e1", fontSize: "11px", marginRight: "8px", background: "#ffffff" }}
            >
              <option value={25}>25 / page</option>
              <option value={50}>50 / page</option>
              <option value={100}>100 / page</option>
            </select>
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              style={{
                padding: "5px 10px",
                borderRadius: "4px",
                border: "1px solid #cbd5e1",
                background: page <= 1 ? "#f1f5f9" : "#ffffff",
                color: page <= 1 ? "#94a3b8" : "#334155",
                cursor: page <= 1 ? "not-allowed" : "pointer",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              Previous
            </button>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              style={{
                padding: "5px 10px",
                borderRadius: "4px",
                border: "1px solid #cbd5e1",
                background: page >= totalPages ? "#f1f5f9" : "#ffffff",
                color: page >= totalPages ? "#94a3b8" : "#334155",
                cursor: page >= totalPages ? "not-allowed" : "pointer",
                fontSize: "12px",
                fontWeight: 600,
              }}
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* EVENT DETAIL MODAL */}
      {selectedLog && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
            padding: "20px",
          }}
          onClick={handleCloseDetail}
        >
          <div
            style={{
              backgroundColor: "#ffffff",
              borderRadius: "12px",
              width: "100%",
              maxWidth: "600px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2)",
              overflow: "hidden",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{ padding: "18px 24px", borderBottom: "1px solid #edf0f4", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ margin: 0, fontSize: "16px", color: "#0f172a", fontWeight: 700 }}>
                  Audit Event #{selectedLog.id}
                </h3>
                <p style={{ margin: "2px 0 0", fontSize: "12px", color: "#64748b" }}>
                  Detailed metadata and traceability parameters
                </p>
              </div>
              <button
                type="button"
                onClick={handleCloseDetail}
                style={{ background: "transparent", border: "none", fontSize: "20px", color: "#64748b", cursor: "pointer" }}
              >
                ×
              </button>
            </div>

            {/* Modal Body */}
            <div style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: "14px", fontSize: "13px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>ACTION CODE</span>
                  <div style={{ fontWeight: 700, color: "#0f172a", marginTop: "2px" }}>{selectedLog.action}</div>
                </div>
                <div>
                  <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>OUTCOME</span>
                  <div style={{ marginTop: "2px" }}>
                    <span
                      style={{
                        padding: "3px 8px",
                        borderRadius: "4px",
                        fontSize: "11px",
                        fontWeight: 700,
                        textTransform: "uppercase",
                        background: selectedLog.result === "success" ? "#dcfce7" : "#fee2e2",
                        color: selectedLog.result === "success" ? "#15803d" : "#b91c1c",
                      }}
                    >
                      {selectedLog.result}
                    </span>
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>ACTOR IDENTITY</span>
                  <div style={{ color: "#334155", marginTop: "2px" }}>
                    {selectedLog.username || (selectedLog.user_id ? `User ID ${selectedLog.user_id}` : "System / Agent")}
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>SOURCE IP</span>
                  <div style={{ color: "#334155", marginTop: "2px", fontFamily: "monospace" }}>
                    {selectedLog.ip_address || "None / Internal"}
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>TARGET RESOURCE</span>
                  <div style={{ color: "#334155", marginTop: "2px" }}>
                    {selectedLog.target_type ? `${selectedLog.target_type} (#${selectedLog.target_id || "N/A"})` : "None"}
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>TIMESTAMP (UTC)</span>
                  <div style={{ color: "#334155", marginTop: "2px" }}>
                    {selectedLog.created_at}
                  </div>
                </div>
              </div>

              {/* JSON preview */}
              <div style={{ marginTop: "10px" }}>
                <span style={{ fontSize: "11px", color: "#64748b", fontWeight: 600 }}>RAW AUDIT RECORD</span>
                <pre style={{ background: "#f8fafc", padding: "12px", borderRadius: "6px", border: "1px solid #e2e8f0", fontSize: "11px", color: "#334155", overflowX: "auto", marginTop: "4px" }}>
                  {JSON.stringify(selectedLog, null, 2)}
                </pre>
              </div>
            </div>

            {/* Modal Footer */}
            <div style={{ padding: "14px 24px", borderTop: "1px solid #edf0f4", background: "#f8fafc", display: "flex", justifyContent: "flex-end" }}>
              <button
                type="button"
                className="export"
                onClick={handleCloseDetail}
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

export default AuditLogs;
