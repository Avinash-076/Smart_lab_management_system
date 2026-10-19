import Icon from "../../../../components/ui/Icon";
import "./ReportFilters.css";

function ReportFilters({
  category,
  period,
  setPeriod,
  dateFrom,
  setDateFrom,
  dateTo,
  setDateTo,
  computerId,
  setComputerId,
  search,
  setSearch,
  statusFilter,
  setStatusFilter,
  severityFilter,
  setSeverityFilter,
  maintenanceTypeFilter,
  setMaintenanceTypeFilter,
  commandTypeFilter,
  setCommandTypeFilter,
  computersList,
  resetFilters,
  activeFiltersCount,
}) {
  const supportsPeriod = ["utilization", "issues", "maintenance", "usage", "commands", "audit"].includes(category);
  const supportsComputer = ["inventory", "utilization", "software", "issues", "maintenance", "usage", "commands"].includes(category);
  const supportsSearch = ["inventory", "software", "usage", "audit"].includes(category);

  return (
    <div className="report-filters-card">
      <div className="report-filters-row">
        {/* Search Bar */}
        {supportsSearch && (
          <div className="report-filter-item report-search-item">
            <label className="report-filter-label" htmlFor="report-search-input">
              Search
            </label>
            <div className="report-input-with-icon">
              <span className="report-input-icon">
                <Icon type="search" size={16} />
              </span>
              <input
                id="report-search-input"
                type="text"
                placeholder={
                  category === "inventory"
                    ? "Search hostname, IP, OS, hardware..."
                    : category === "software"
                    ? "Search software name or publisher..."
                    : category === "usage"
                    ? "Search application or process..."
                    : "Search action..."
                }
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="report-filter-input"
              />
              {search && (
                <button
                  type="button"
                  className="report-input-clear-btn"
                  onClick={() => setSearch("")}
                  title="Clear search"
                >
                  &times;
                </button>
              )}
            </div>
          </div>
        )}

        {/* Time Window Selector */}
        {supportsPeriod && (
          <div className="report-filter-item">
            <label className="report-filter-label" htmlFor="report-period-select">
              Time Window
            </label>
            <select
              id="report-period-select"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="report-filter-select"
            >
              <option value="24h">Last 24 Hours</option>
              <option value="7d">Last 7 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="custom">Custom Date Range</option>
            </select>
          </div>
        )}

        {/* Custom Date Pickers */}
        {supportsPeriod && period === "custom" && (
          <>
            <div className="report-filter-item">
              <label className="report-filter-label" htmlFor="report-date-from">
                From Date
              </label>
              <input
                id="report-date-from"
                type="datetime-local"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="report-filter-input"
              />
            </div>
            <div className="report-filter-item">
              <label className="report-filter-label" htmlFor="report-date-to">
                To Date
              </label>
              <input
                id="report-date-to"
                type="datetime-local"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="report-filter-input"
              />
            </div>
          </>
        )}

        {/* Computer Selector */}
        {supportsComputer && (
          <div className="report-filter-item">
            <label className="report-filter-label" htmlFor="report-computer-select">
              Computer
            </label>
            <select
              id="report-computer-select"
              value={computerId}
              onChange={(e) => setComputerId(e.target.value)}
              className="report-filter-select"
            >
              <option value="">All Computers</option>
              {computersList.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.hostname} ({c.ip_address})
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Inventory Status */}
        {category === "inventory" && (
          <div className="report-filter-item">
            <label className="report-filter-label" htmlFor="report-inv-status">
              Status
            </label>
            <select
              id="report-inv-status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="report-filter-select"
            >
              <option value="">All Statuses</option>
              <option value="online">Online</option>
              <option value="offline">Offline</option>
            </select>
          </div>
        )}

        {/* Issue Status & Severity */}
        {category === "issues" && (
          <>
            <div className="report-filter-item">
              <label className="report-filter-label" htmlFor="report-issue-status">
                Status
              </label>
              <select
                id="report-issue-status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="report-filter-select"
              >
                <option value="">All Statuses</option>
                <option value="open">Open</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
            <div className="report-filter-item">
              <label className="report-filter-label" htmlFor="report-issue-severity">
                Severity
              </label>
              <select
                id="report-issue-severity"
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="report-filter-select"
              >
                <option value="">All Severities</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </>
        )}

        {/* Maintenance Status & Type */}
        {category === "maintenance" && (
          <>
            <div className="report-filter-item">
              <label className="report-filter-label" htmlFor="report-maint-status">
                Status
              </label>
              <select
                id="report-maint-status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="report-filter-select"
              >
                <option value="">All Statuses</option>
                <option value="scheduled">Scheduled</option>
                <option value="in_progress">In Progress</option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>
            <div className="report-filter-item">
              <label className="report-filter-label" htmlFor="report-maint-type">
                Type
              </label>
              <select
                id="report-maint-type"
                value={maintenanceTypeFilter}
                onChange={(e) => setMaintenanceTypeFilter(e.target.value)}
                className="report-filter-select"
              >
                <option value="">All Types</option>
                <option value="preventive">Preventive</option>
                <option value="corrective">Corrective</option>
                <option value="emergency">Emergency</option>
                <option value="software">Software</option>
                <option value="hardware">Hardware</option>
              </select>
            </div>
          </>
        )}

        {/* Command Type & Status */}
        {category === "commands" && (
          <>
            <div className="report-filter-item">
              <label className="report-filter-label" htmlFor="report-cmd-type">
                Command Type
              </label>
              <select
                id="report-cmd-type"
                value={commandTypeFilter}
                onChange={(e) => setCommandTypeFilter(e.target.value)}
                className="report-filter-select"
              >
                <option value="">All Commands</option>
                <option value="restart">Restart</option>
                <option value="shutdown">Shutdown</option>
                <option value="lock">Lock</option>
                <option value="message">Message</option>
              </select>
            </div>
            <div className="report-filter-item">
              <label className="report-filter-label" htmlFor="report-cmd-status">
                Status
              </label>
              <select
                id="report-cmd-status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="report-filter-select"
              >
                <option value="">All Outcomes</option>
                <option value="executed">Executed</option>
                <option value="failed">Failed</option>
                <option value="pending">Pending</option>
              </select>
            </div>
          </>
        )}

        {/* Audit Result */}
        {category === "audit" && (
          <div className="report-filter-item">
            <label className="report-filter-label" htmlFor="report-audit-result">
              Result
            </label>
            <select
              id="report-audit-result"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="report-filter-select"
            >
              <option value="">All Results</option>
              <option value="success">Success</option>
              <option value="failure">Failure</option>
            </select>
          </div>
        )}

        {/* Reset Filters Button */}
        {activeFiltersCount > 0 && (
          <div className="report-filter-actions">
            <button
              type="button"
              className="report-reset-filters-btn"
              onClick={resetFilters}
              title="Reset all active filters"
            >
              <Icon type="clear-filter" size={14} />
              <span>Reset ({activeFiltersCount})</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ReportFilters;
