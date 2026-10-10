import { useCallback, useEffect, useState } from "react";

import StatCard from "../../../components/ui/StatCard";
import Icon from "../../../components/ui/Icon";
import {
  downloadReportCSV,
  getAuditReport,
  getCommandReport,
  getIssueReport,
  getMaintenanceReport,
  getReportOverview,
  getSoftwareReport,
  getUtilizationReport,
} from "../../../services/api";

function Reports() {
  const [reportType, setReportType] = useState("utilization");
  const [period, setPeriod] = useState("24h");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);

  // Data states
  const [overview, setOverview] = useState(null);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    async function fetchOverview() {
      try {
        const data = await getReportOverview();
        if (active) setOverview(data);
      } catch {
        // Fallback silently if unprivileged
      }
    }
    fetchOverview();
    return () => {
      active = false;
    };
  }, []);

  const loadReportData = useCallback(async () => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      let data = null;
      const options = {
        period,
        from_date: period === "custom" && dateFrom ? dateFrom : undefined,
        to_date: period === "custom" && dateTo ? dateTo : undefined,
        search: search || undefined,
        page,
        limit: 25,
      };

      if (reportType === "utilization") {
        data = await getUtilizationReport(options);
      } else if (reportType === "software") {
        data = await getSoftwareReport(options);
      } else if (reportType === "issues") {
        data = await getIssueReport(options);
      } else if (reportType === "maintenance") {
        data = await getMaintenanceReport(options);
      } else if (reportType === "commands") {
        data = await getCommandReport(options);
      } else if (reportType === "audit") {
        data = await getAuditReport(options);
      }

      setReportData(data);
    } catch (err) {
      setError(err.message || "Failed to load report data");
    } finally {
      setLoading(false);
    }
  }, [reportType, period, dateFrom, dateTo, search, page]);

  useEffect(() => {
    let active = true;
    async function fetchReportData() {
      try {
        let data = null;
        const options = {
          period,
          from_date: period === "custom" && dateFrom ? dateFrom : undefined,
          to_date: period === "custom" && dateTo ? dateTo : undefined,
          search: search || undefined,
          page,
          limit: 25,
        };

        if (reportType === "utilization") {
          data = await getUtilizationReport(options);
        } else if (reportType === "software") {
          data = await getSoftwareReport(options);
        } else if (reportType === "issues") {
          data = await getIssueReport(options);
        } else if (reportType === "maintenance") {
          data = await getMaintenanceReport(options);
        } else if (reportType === "commands") {
          data = await getCommandReport(options);
        } else if (reportType === "audit") {
          data = await getAuditReport(options);
        }

        if (active) {
          setReportData(data);
          setError("");
          setLoading(false);
        }
      } catch (err) {
        if (active) {
          setError(err.message || "Failed to load report data");
          setLoading(false);
        }
      }
    }

    fetchReportData();
    return () => {
      active = false;
    };
  }, [reportType, period, dateFrom, dateTo, search, page]);

  // Handle CSV Export
  const handleExport = async () => {
    setExporting(true);
    setError("");
    setMessage("");
    try {
      const options = {
        period,
        from_date: period === "custom" && dateFrom ? dateFrom : undefined,
        to_date: period === "custom" && dateTo ? dateTo : undefined,
        search: search || undefined,
      };
      const filename = await downloadReportCSV(reportType, options);
      setMessage(`Report exported successfully as ${filename}`);
    } catch (err) {
      setError(err.message || "Failed to export CSV report");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="content">
      {/* PAGE HEADER */}
      <div className="page-top">
        <div>
          <h2>Reports & Analytics</h2>
          <p>
            Generate, inspect, and export system metrics, telemetry, and administrative logs.
          </p>
        </div>
      </div>

      {/* OVERVIEW STAT CARDS */}
      <div className="cards">
        <StatCard
          icon="computer"
          title="Computers & Metrics"
          number={overview ? `${overview.online_computers}/${overview.total_computers}` : "—"}
          footer="Online / Registered"
          type="blue"
        />
        <StatCard
          icon="software"
          title="Software Inventory"
          number={overview ? overview.unique_software_count : "—"}
          footer={`${overview ? overview.total_software_records : 0} total installations`}
          type="green"
        />
        <StatCard
          icon="issue"
          title="Issues Tracking"
          number={overview ? overview.open_issues : "—"}
          footer={`${overview ? overview.critical_issues : 0} critical open`}
          type="orange"
        />
        <StatCard
          icon="maintenance"
          title="Maintenance"
          number={overview ? overview.pending_maintenance : "—"}
          footer={`${overview ? overview.overdue_maintenance : 0} overdue tasks`}
          type="purple"
        />
      </div>

      {/* REPORT CONTROLS CARD */}
      <div className="report-generator" style={{ marginBottom: "24px" }}>
        <div className="page-section-header">
          <div>
            <h3>Report Configuration</h3>
            <p>Select report domain, time window, filters, and export format.</p>
          </div>
        </div>

        <div className="report-controls" style={{ flexWrap: "wrap", gap: "16px" }}>
          {/* REPORT TYPE */}
          <div className="report-field">
            <label>Report Domain</label>
            <select
              value={reportType}
              onChange={(e) => {
                setReportType(e.target.value);
                setPage(1);
              }}
            >
              <option value="utilization">Computer & Utilization</option>
              <option value="software">Software Inventory</option>
              <option value="issues">Issue Tracking</option>
              <option value="maintenance">Maintenance Operations</option>
              <option value="commands">Remote Commands</option>
              <option value="audit">Security Audit Logs</option>
            </select>
          </div>

          {/* TIME PERIOD */}
          {reportType !== "software" && (
            <div className="report-field">
              <label>Time Window</label>
              <select
                value={period}
                onChange={(e) => {
                  setPeriod(e.target.value);
                  setPage(1);
                }}
              >
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
                <option value="custom">Custom Date Range</option>
              </select>
            </div>
          )}

          {/* CUSTOM DATES */}
          {period === "custom" && reportType !== "software" && (
            <>
              <div className="report-field">
                <label>From Date</label>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </div>
              <div className="report-field">
                <label>To Date</label>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </div>
            </>
          )}

          {/* SEARCH (for software / audit) */}
          {(reportType === "software" || reportType === "audit") && (
            <div className="report-field" style={{ flexGrow: 1, minWidth: "180px" }}>
              <label>Search Keyword</label>
              <input
                type="text"
                placeholder="Search..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
          )}

          {/* ACTIONS */}
          <div style={{ display: "flex", gap: "10px", alignItems: "flex-end" }}>
            <button
              className="btn btn-secondary"
              onClick={loadReportData}
              disabled={loading}
              style={{ height: "42px", padding: "0 16px" }}
            >
              <Icon type="refresh" size={16} /> Refresh
            </button>
            <button
              className="report-export-button"
              onClick={handleExport}
              disabled={exporting || loading}
              style={{ height: "42px", padding: "0 18px", whiteSpace: "nowrap" }}
            >
              <Icon type="download" size={16} />
              {exporting ? "Exporting..." : "Export CSV"}
            </button>
          </div>
        </div>

        {/* MESSAGES / TOASTS */}
        {message && (
          <div className="report-message" style={{ marginTop: "14px" }}>
            <Icon type="check" size={16} /> {message}
          </div>
        )}
        {error && (
          <div
            style={{
              marginTop: "14px",
              padding: "10px 14px",
              background: "#fee2e2",
              color: "#991b1b",
              borderRadius: "8px",
              fontSize: "14px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <Icon type="alert" size={16} /> {error}
          </div>
        )}
      </div>

      {/* REPORT PREVIEW AND METRICS */}
      <div className="report-preview">
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
            Loading report data...
          </div>
        ) : !reportData ? (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
            No report data available.
          </div>
        ) : (
          <>
            {/* DOMAIN 1: UTILIZATION */}
            {reportType === "utilization" && (
              <div>
                <div className="report-summary-grid">
                  <div className="report-summary-item">
                    <span>Total Nodes</span>
                    <strong>{reportData.total_computers}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Online / Offline</span>
                    <strong>
                      {reportData.online_computers} / {reportData.offline_computers}
                    </strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Avg CPU / Max CPU</span>
                    <strong>
                      {reportData.metrics_summary.avg_cpu_percent}% /{" "}
                      {reportData.metrics_summary.max_cpu_percent}%
                    </strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Avg RAM / Avg Disk</span>
                    <strong>
                      {reportData.metrics_summary.avg_ram_percent}% /{" "}
                      {reportData.metrics_summary.avg_disk_percent}%
                    </strong>
                  </div>
                </div>

                <div style={{ marginTop: "24px" }}>
                  <h4 style={{ marginBottom: "12px", color: "#1e293b" }}>
                    Per-Computer Telemetry Breakdown
                  </h4>
                  <div className="table-wrapper" style={{ overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                          <th style={{ padding: "10px 14px" }}>Hostname</th>
                          <th style={{ padding: "10px 14px" }}>Status</th>
                          <th style={{ padding: "10px 14px" }}>IP Address</th>
                          <th style={{ padding: "10px 14px" }}>Avg CPU</th>
                          <th style={{ padding: "10px 14px" }}>Avg RAM</th>
                          <th style={{ padding: "10px 14px" }}>Avg Disk</th>
                          <th style={{ padding: "10px 14px" }}>Samples</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reportData.computers.map((c) => (
                          <tr key={c.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                            <td style={{ padding: "12px 14px", fontWeight: "600" }}>{c.hostname}</td>
                            <td style={{ padding: "12px 14px" }}>
                              <span
                                style={{
                                  padding: "3px 8px",
                                  borderRadius: "12px",
                                  fontSize: "12px",
                                  fontWeight: "600",
                                  background: c.status === "online" ? "#dcfce7" : "#f1f5f9",
                                  color: c.status === "online" ? "#15803d" : "#64748b",
                                }}
                              >
                                {c.status}
                              </span>
                            </td>
                            <td style={{ padding: "12px 14px" }}>{c.ip_address}</td>
                            <td style={{ padding: "12px 14px" }}>{c.avg_cpu}%</td>
                            <td style={{ padding: "12px 14px" }}>{c.avg_ram}%</td>
                            <td style={{ padding: "12px 14px" }}>{c.avg_disk}%</td>
                            <td style={{ padding: "12px 14px" }}>{c.sample_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* DOMAIN 2: SOFTWARE INVENTORY */}
            {reportType === "software" && (
              <div>
                <div className="report-summary-grid">
                  <div className="report-summary-item">
                    <span>Total Installations</span>
                    <strong>{reportData.total_records}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Unique Software</span>
                    <strong>{reportData.unique_software_count}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Top Application</span>
                    <strong>{reportData.top_installed[0]?.name || "N/A"}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Page</span>
                    <strong>
                      {reportData.page} of {reportData.total_pages}
                    </strong>
                  </div>
                </div>

                <div style={{ marginTop: "24px" }}>
                  <h4 style={{ marginBottom: "12px", color: "#1e293b" }}>Installed Software Records</h4>
                  <div className="table-wrapper" style={{ overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                          <th style={{ padding: "10px 14px" }}>Application Name</th>
                          <th style={{ padding: "10px 14px" }}>Version</th>
                          <th style={{ padding: "10px 14px" }}>Publisher</th>
                          <th style={{ padding: "10px 14px" }}>Host Computer</th>
                          <th style={{ padding: "10px 14px" }}>Install Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reportData.items.map((s) => (
                          <tr key={s.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                            <td style={{ padding: "12px 14px", fontWeight: "600" }}>{s.name}</td>
                            <td style={{ padding: "12px 14px" }}>{s.version || "—"}</td>
                            <td style={{ padding: "12px 14px" }}>{s.publisher || "Unknown"}</td>
                            <td style={{ padding: "12px 14px" }}>{s.computer_hostname || `ID #${s.computer_id}`}</td>
                            <td style={{ padding: "12px 14px" }}>{s.install_date || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* DOMAIN 3: ISSUES */}
            {reportType === "issues" && (
              <div>
                <div className="report-summary-grid">
                  <div className="report-summary-item">
                    <span>Total Issues</span>
                    <strong>{reportData.total_issues}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Open / In Progress</span>
                    <strong>
                      {reportData.by_status.open || 0} / {reportData.by_status.in_progress || 0}
                    </strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Resolved</span>
                    <strong>{reportData.by_status.resolved || 0}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Critical / High</span>
                    <strong>
                      {reportData.by_severity.critical || 0} / {reportData.by_severity.high || 0}
                    </strong>
                  </div>
                </div>

                <div style={{ marginTop: "24px" }}>
                  <h4 style={{ marginBottom: "12px", color: "#1e293b" }}>Issue Records</h4>
                  <div className="table-wrapper" style={{ overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                          <th style={{ padding: "10px 14px" }}>Issue Title</th>
                          <th style={{ padding: "10px 14px" }}>Computer</th>
                          <th style={{ padding: "10px 14px" }}>Severity</th>
                          <th style={{ padding: "10px 14px" }}>Status</th>
                          <th style={{ padding: "10px 14px" }}>Reported At</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reportData.items.map((iss) => (
                          <tr key={iss.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                            <td style={{ padding: "12px 14px", fontWeight: "600" }}>{iss.title}</td>
                            <td style={{ padding: "12px 14px" }}>{iss.computer_hostname || `ID #${iss.computer_id}`}</td>
                            <td style={{ padding: "12px 14px" }}>
                              <span
                                style={{
                                  padding: "3px 8px",
                                  borderRadius: "12px",
                                  fontSize: "12px",
                                  fontWeight: "600",
                                  background:
                                    iss.severity === "critical"
                                      ? "#fee2e2"
                                      : iss.severity === "high"
                                      ? "#ffedd5"
                                      : "#f1f5f9",
                                  color:
                                    iss.severity === "critical"
                                      ? "#991b1b"
                                      : iss.severity === "high"
                                      ? "#c2410c"
                                      : "#475569",
                                }}
                              >
                                {iss.severity}
                              </span>
                            </td>
                            <td style={{ padding: "12px 14px" }}>
                              <span
                                style={{
                                  padding: "3px 8px",
                                  borderRadius: "12px",
                                  fontSize: "12px",
                                  fontWeight: "600",
                                  background: iss.status === "resolved" ? "#dcfce7" : "#e0e7ff",
                                  color: iss.status === "resolved" ? "#15803d" : "#3730a3",
                                }}
                              >
                                {iss.status}
                              </span>
                            </td>
                            <td style={{ padding: "12px 14px" }}>
                              {new Date(iss.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* DOMAIN 4: MAINTENANCE */}
            {reportType === "maintenance" && (
              <div>
                <div className="report-summary-grid">
                  <div className="report-summary-item">
                    <span>Total Tasks</span>
                    <strong>{reportData.total_records}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Scheduled / In Progress</span>
                    <strong>
                      {reportData.by_status.scheduled || 0} / {reportData.by_status.in_progress || 0}
                    </strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Completed</span>
                    <strong>{reportData.by_status.completed || 0}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Upcoming / Overdue</span>
                    <strong>
                      {reportData.upcoming_count} / {reportData.overdue_count}
                    </strong>
                  </div>
                </div>

                <div style={{ marginTop: "24px" }}>
                  <h4 style={{ marginBottom: "12px", color: "#1e293b" }}>Maintenance Records</h4>
                  <div className="table-wrapper" style={{ overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                          <th style={{ padding: "10px 14px" }}>Task Title</th>
                          <th style={{ padding: "10px 14px" }}>Type</th>
                          <th style={{ padding: "10px 14px" }}>Computer</th>
                          <th style={{ padding: "10px 14px" }}>Technician</th>
                          <th style={{ padding: "10px 14px" }}>Status</th>
                          <th style={{ padding: "10px 14px" }}>Scheduled Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reportData.items.map((m) => (
                          <tr key={m.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                            <td style={{ padding: "12px 14px", fontWeight: "600" }}>{m.title}</td>
                            <td style={{ padding: "12px 14px" }}>{m.maintenance_type}</td>
                            <td style={{ padding: "12px 14px" }}>{m.computer_hostname || `ID #${m.computer_id}`}</td>
                            <td style={{ padding: "12px 14px" }}>{m.technician_name || "Unassigned"}</td>
                            <td style={{ padding: "12px 14px" }}>
                              <span
                                style={{
                                  padding: "3px 8px",
                                  borderRadius: "12px",
                                  fontSize: "12px",
                                  fontWeight: "600",
                                  background: m.status === "completed" ? "#dcfce7" : "#e0e7ff",
                                  color: m.status === "completed" ? "#15803d" : "#3730a3",
                                }}
                              >
                                {m.status}
                              </span>
                            </td>
                            <td style={{ padding: "12px 14px" }}>
                              {m.scheduled_at ? new Date(m.scheduled_at).toLocaleDateString() : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* DOMAIN 5: REMOTE COMMANDS */}
            {reportType === "commands" && (
              <div>
                <div className="report-summary-grid">
                  <div className="report-summary-item">
                    <span>Total Commands</span>
                    <strong>{reportData.total_commands}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Success Rate</span>
                    <strong>{reportData.success_rate}%</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Executed</span>
                    <strong>{reportData.by_status.executed || 0}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Failed / Pending</span>
                    <strong>
                      {reportData.by_status.failed || 0} / {reportData.by_status.pending || 0}
                    </strong>
                  </div>
                </div>

                <div style={{ marginTop: "24px" }}>
                  <h4 style={{ marginBottom: "12px", color: "#1e293b" }}>Command Execution History</h4>
                  <div className="table-wrapper" style={{ overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                          <th style={{ padding: "10px 14px" }}>Command Type</th>
                          <th style={{ padding: "10px 14px" }}>Target Computer</th>
                          <th style={{ padding: "10px 14px" }}>Status</th>
                          <th style={{ padding: "10px 14px" }}>Issued By</th>
                          <th style={{ padding: "10px 14px" }}>Result</th>
                          <th style={{ padding: "10px 14px" }}>Timestamp</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reportData.items.map((cmd) => (
                          <tr key={cmd.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                            <td style={{ padding: "12px 14px", fontWeight: "600" }}>{cmd.command_type}</td>
                            <td style={{ padding: "12px 14px" }}>{cmd.computer_hostname || `ID #${cmd.computer_id}`}</td>
                            <td style={{ padding: "12px 14px" }}>
                              <span
                                style={{
                                  padding: "3px 8px",
                                  borderRadius: "12px",
                                  fontSize: "12px",
                                  fontWeight: "600",
                                  background: cmd.status === "executed" ? "#dcfce7" : "#fee2e2",
                                  color: cmd.status === "executed" ? "#15803d" : "#991b1b",
                                }}
                              >
                                {cmd.status}
                              </span>
                            </td>
                            <td style={{ padding: "12px 14px" }}>{cmd.issued_by_username || `User #${cmd.issued_by}`}</td>
                            <td style={{ padding: "12px 14px" }}>{cmd.result_message || "—"}</td>
                            <td style={{ padding: "12px 14px" }}>
                              {new Date(cmd.created_at).toLocaleString()}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* DOMAIN 6: SECURITY AUDIT */}
            {reportType === "audit" && (
              <div>
                <div className="report-summary-grid">
                  <div className="report-summary-item">
                    <span>Total Audit Events</span>
                    <strong>{reportData.total_events}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Successful Operations</span>
                    <strong>{reportData.by_result.success || 0}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Failed / Unauthorized</span>
                    <strong>{reportData.by_result.failure || 0}</strong>
                  </div>
                  <div className="report-summary-item">
                    <span>Top Action</span>
                    <strong>{Object.keys(reportData.by_action)[0] || "N/A"}</strong>
                  </div>
                </div>

                <div style={{ marginTop: "24px" }}>
                  <h4 style={{ marginBottom: "12px", color: "#1e293b" }}>Security Audit Trail</h4>
                  <div className="table-wrapper" style={{ overflowX: "auto" }}>
                    <table className="table" style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead>
                        <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                          <th style={{ padding: "10px 14px" }}>Timestamp</th>
                          <th style={{ padding: "10px 14px" }}>Action Code</th>
                          <th style={{ padding: "10px 14px" }}>Actor</th>
                          <th style={{ padding: "10px 14px" }}>Target</th>
                          <th style={{ padding: "10px 14px" }}>Result</th>
                          <th style={{ padding: "10px 14px" }}>IP Address</th>
                        </tr>
                      </thead>
                      <tbody>
                        {reportData.items.map((a) => (
                          <tr key={a.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                            <td style={{ padding: "12px 14px" }}>{new Date(a.created_at).toLocaleString()}</td>
                            <td style={{ padding: "12px 14px", fontWeight: "600" }}>{a.action}</td>
                            <td style={{ padding: "12px 14px" }}>{a.username || "System"}</td>
                            <td style={{ padding: "12px 14px" }}>
                              {a.target_type ? `${a.target_type} #${a.target_id || ""}` : "—"}
                            </td>
                            <td style={{ padding: "12px 14px" }}>
                              <span
                                style={{
                                  padding: "3px 8px",
                                  borderRadius: "12px",
                                  fontSize: "12px",
                                  fontWeight: "600",
                                  background: a.result === "success" ? "#dcfce7" : "#fee2e2",
                                  color: a.result === "success" ? "#15803d" : "#991b1b",
                                }}
                              >
                                {a.result}
                              </span>
                            </td>
                            <td style={{ padding: "12px 14px" }}>{a.ip_address || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default Reports;