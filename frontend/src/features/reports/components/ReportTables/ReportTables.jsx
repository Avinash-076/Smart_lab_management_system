import Icon from "../../../../components/ui/Icon";
import {
  formatDate,
  formatGigabytes,
  getSeverityBadgeClass,
  getStatusBadgeClass,
} from "../../utils/reportUtils";
import "./ReportTables.css";

function ReportTables({ category, reportData, loading, page, onPageChange }) {
  if (loading) {
    return (
      <div className="report-table-card">
        <div className="report-table-loading">
          <div className="report-table-spinner" />
          <span>Querying database records...</span>
        </div>
      </div>
    );
  }

  if (!reportData) return null;

  const isUtil = category === "utilization";
  const items = isUtil ? reportData.computers || [] : reportData.items || [];
  const totalPages = isUtil ? 1 : reportData.total_pages || 1;
  const totalCount = isUtil
    ? items.length
    : reportData.total_computers ||
      reportData.total_records ||
      reportData.total_issues ||
      reportData.total_sessions ||
      reportData.total_commands ||
      reportData.total_events ||
      items.length;

  if (items.length === 0) {
    return (
      <div className="report-table-card">
        <div className="report-table-empty">
          <div className="report-empty-icon-wrap">
            <Icon type="reports" size={32} />
          </div>
          <h4>No Report Records Found</h4>
          <p>
            No data matched your current filter criteria or the database contains no records in this
            window. Try adjusting your search or time filters.
          </p>
        </div>
      </div>
    );
  }

  const renderTableContent = () => {
    switch (category) {
      case "inventory":
        return (
          <table className="report-data-table">
            <thead>
              <tr>
                <th>Computer Hostname</th>
                <th>Network & OS</th>
                <th>Status</th>
                <th>Hardware Specification</th>
                <th>Processor & Cores</th>
                <th>Memory & Storage</th>
                <th>Registered</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div className="report-cell-primary">
                      <Icon type="computer" size={16} />
                      <strong>{row.hostname}</strong>
                    </div>
                    <span className="report-cell-sub">ID: #{row.id}</span>
                  </td>
                  <td>
                    <div className="report-cell-text">{row.ip_address}</div>
                    <span className="report-cell-sub">
                      {row.os_name} {row.os_version}
                    </span>
                  </td>
                  <td>
                    <span className={`report-badge ${getStatusBadgeClass(row.status)}`}>
                      {row.status}
                    </span>
                  </td>
                  <td>
                    <div className="report-cell-text">{row.manufacturer || "Generic"}</div>
                    <span className="report-cell-sub">{row.model || row.system_type || "N/A"}</span>
                  </td>
                  <td>
                    <div className="report-cell-text">{row.processor_name || "Unknown CPU"}</div>
                    <span className="report-cell-sub">
                      {row.processor_cores ? `${row.processor_cores} Cores` : "N/A"}
                    </span>
                  </td>
                  <td>
                    <div className="report-cell-text">RAM: {formatGigabytes(row.ram_total_gb)}</div>
                    <span className="report-cell-sub">Disk: {formatGigabytes(row.storage_total_gb)}</span>
                  </td>
                  <td>
                    <span className="report-cell-date">{formatDate(row.registered_at)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      case "utilization":
        return (
          <table className="report-data-table">
            <thead>
              <tr>
                <th>Computer Hostname</th>
                <th>Operating System</th>
                <th>Status</th>
                <th>Avg CPU</th>
                <th>Avg RAM</th>
                <th>Avg Storage</th>
                <th>Telemetry Samples</th>
                <th>Last Contact</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div className="report-cell-primary">
                      <Icon type="computer" size={16} />
                      <strong>{row.hostname}</strong>
                    </div>
                    <span className="report-cell-sub">{row.ip_address}</span>
                  </td>
                  <td>
                    <div className="report-cell-text">
                      {row.os_name} {row.os_version}
                    </div>
                  </td>
                  <td>
                    <span className={`report-badge ${getStatusBadgeClass(row.status)}`}>
                      {row.status}
                    </span>
                  </td>
                  <td>
                    <span className="report-metric-val">{row.avg_cpu}%</span>
                  </td>
                  <td>
                    <span className="report-metric-val">{row.avg_ram}%</span>
                  </td>
                  <td>
                    <span className="report-metric-val">{row.avg_disk}%</span>
                  </td>
                  <td>
                    <span className="report-sample-badge">{row.sample_count} points</span>
                  </td>
                  <td>
                    <span className="report-cell-date">{formatDate(row.last_seen)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      case "software":
        return (
          <table className="report-data-table">
            <thead>
              <tr>
                <th>Software Application</th>
                <th>Version</th>
                <th>Publisher</th>
                <th>Installed On</th>
                <th>Install Date</th>
                <th>Collected At</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div className="report-cell-primary">
                      <Icon type="software" size={16} />
                      <strong>{row.name}</strong>
                    </div>
                  </td>
                  <td>
                    <span className="report-version-tag">{row.version || "N/A"}</span>
                  </td>
                  <td>{row.publisher || "Unknown Publisher"}</td>
                  <td>
                    <span className="report-cell-text">
                      {row.computer_hostname || `Computer #${row.computer_id}`}
                    </span>
                  </td>
                  <td>{row.install_date || "N/A"}</td>
                  <td>
                    <span className="report-cell-date">{formatDate(row.collected_at)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      case "issues":
        return (
          <table className="report-data-table">
            <thead>
              <tr>
                <th>Issue</th>
                <th>Computer</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Source</th>
                <th>Created At</th>
                <th>Resolution</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div className="report-cell-primary">
                      <strong>{row.title}</strong>
                    </div>
                    <span className="report-cell-sub">{row.description}</span>
                  </td>
                  <td>
                    <span className="report-cell-text">
                      {row.computer_hostname || `Computer #${row.computer_id}`}
                    </span>
                  </td>
                  <td>
                    <span className={`report-badge ${getSeverityBadgeClass(row.severity)}`}>
                      {row.severity}
                    </span>
                  </td>
                  <td>
                    <span className={`report-badge ${getStatusBadgeClass(row.status)}`}>
                      {row.status}
                    </span>
                  </td>
                  <td>
                    <span className="report-source-tag">{row.source}</span>
                  </td>
                  <td>
                    <span className="report-cell-date">{formatDate(row.created_at)}</span>
                  </td>
                  <td>
                    {row.resolved_at ? (
                      <div>
                        <span className="report-cell-date">{formatDate(row.resolved_at)}</span>
                        {row.resolution_notes && (
                          <div className="report-cell-sub">{row.resolution_notes}</div>
                        )}
                      </div>
                    ) : (
                      <span className="report-unresolved-tag">Unresolved</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      case "maintenance":
        return (
          <table className="report-data-table">
            <thead>
              <tr>
                <th>Maintenance Task</th>
                <th>Computer</th>
                <th>Type</th>
                <th>Status</th>
                <th>Technician</th>
                <th>Scheduled At</th>
                <th>Completed At</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div className="report-cell-primary">
                      <strong>{row.title}</strong>
                    </div>
                    {row.description && <span className="report-cell-sub">{row.description}</span>}
                  </td>
                  <td>
                    <span className="report-cell-text">
                      {row.computer_hostname || `Computer #${row.computer_id}`}
                    </span>
                  </td>
                  <td>
                    <span className="report-source-tag">{row.maintenance_type}</span>
                  </td>
                  <td>
                    <span className={`report-badge ${getStatusBadgeClass(row.status)}`}>
                      {row.status}
                    </span>
                  </td>
                  <td>{row.technician_name || "Unassigned"}</td>
                  <td>
                    <span className="report-cell-date">{formatDate(row.scheduled_at)}</span>
                  </td>
                  <td>
                    <span className="report-cell-date">{formatDate(row.completed_at)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      case "usage":
        return (
          <table className="report-data-table">
            <thead>
              <tr>
                <th>Application Name</th>
                <th>Computer</th>
                <th>Active User</th>
                <th>Runtime Duration</th>
                <th>Started At</th>
                <th>Ended At</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div className="report-cell-primary">
                      <Icon type="cpu" size={16} />
                      <strong>{row.application_name}</strong>
                    </div>
                    {row.process_name && (
                      <span className="report-cell-sub">{row.process_name}</span>
                    )}
                  </td>
                  <td>
                    <span className="report-cell-text">
                      {row.computer_hostname || `Computer #${row.computer_id}`}
                    </span>
                  </td>
                  <td>
                    <span className="report-user-tag">{row.user || "N/A"}</span>
                  </td>
                  <td>
                    <span className="report-duration-badge">{row.duration_formatted}</span>
                  </td>
                  <td>
                    <span className="report-cell-date">{formatDate(row.started_at)}</span>
                  </td>
                  <td>
                    <span className="report-cell-date">
                      {row.ended_at ? formatDate(row.ended_at) : "Active"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      case "commands":
        return (
          <table className="report-data-table">
            <thead>
              <tr>
                <th>Command Type</th>
                <th>Computer</th>
                <th>Status</th>
                <th>Issuer</th>
                <th>Outcome / Result</th>
                <th>Issued At</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div className="report-cell-primary">
                      <Icon type="command" size={16} />
                      <strong>{row.command_type}</strong>
                    </div>
                  </td>
                  <td>
                    <span className="report-cell-text">
                      {row.computer_hostname || `Computer #${row.computer_id}`}
                    </span>
                  </td>
                  <td>
                    <span className={`report-badge ${getStatusBadgeClass(row.status)}`}>
                      {row.status}
                    </span>
                  </td>
                  <td>{row.issued_by_username || `User #${row.issued_by}`}</td>
                  <td>
                    <div className="report-cell-text">
                      {row.success === true && <span className="report-text-success">Success</span>}
                      {row.success === false && <span className="report-text-danger">Failed</span>}
                      {row.success === null && <span className="report-text-muted">Pending</span>}
                    </div>
                    {row.result_message && (
                      <span className="report-cell-sub">{row.result_message}</span>
                    )}
                  </td>
                  <td>
                    <span className="report-cell-date">{formatDate(row.created_at)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      case "audit":
        return (
          <table className="report-data-table">
            <thead>
              <tr>
                <th>Event Action</th>
                <th>Result</th>
                <th>User / Operator</th>
                <th>Target Object</th>
                <th>IP Address</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <div className="report-cell-primary">
                      <Icon type="audit" size={16} />
                      <strong>{row.action}</strong>
                    </div>
                  </td>
                  <td>
                    <span className={`report-badge ${getStatusBadgeClass(row.result)}`}>
                      {row.result}
                    </span>
                  </td>
                  <td>{row.username || "System"}</td>
                  <td>
                    <span className="report-cell-text">
                      {row.target_type ? `${row.target_type} #${row.target_id || ""}` : "N/A"}
                    </span>
                  </td>
                  <td>{row.ip_address || "N/A"}</td>
                  <td>
                    <span className="report-cell-date">{formatDate(row.created_at)}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        );

      default:
        return null;
    }
  };

  return (
    <div className="report-table-card">
      <div className="report-table-responsive">{renderTableContent()}</div>

      {totalPages > 1 && (
        <div className="report-pagination-bar">
          <span className="report-pagination-info">
            Showing page <strong>{page}</strong> of <strong>{totalPages}</strong> (
            <strong>{totalCount}</strong> matching records)
          </span>

          <div className="report-pagination-controls">
            <button
              type="button"
              className="report-page-btn"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
            >
              <Icon type="chevron-left" size={16} />
              <span>Previous</span>
            </button>

            <span className="report-page-current">
              {page} / {totalPages}
            </span>

            <button
              type="button"
              className="report-page-btn"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
            >
              <span>Next</span>
              <Icon type="chevron-right" size={16} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default ReportTables;
