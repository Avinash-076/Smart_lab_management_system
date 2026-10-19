import Icon from "../../../../components/ui/Icon";
import "./IssueFilters.css";

function IssueFilters({
  search,
  onSearchChange,
  statusFilter,
  onStatusChange,
  priorityFilter,
  onPriorityChange,
  computerFilter,
  onComputerChange,
  dateRangeFilter,
  onDateRangeChange,
  computers = [],
  onRefresh,
  onReset,
  loading = false,
}) {
  const hasActiveFilters = Boolean(
    search ||
      (statusFilter && statusFilter !== "All Status") ||
      (priorityFilter && priorityFilter !== "All Priority") ||
      (computerFilter && computerFilter !== "All Computers") ||
      (dateRangeFilter && dateRangeFilter !== "Last 30 Days")
  );

  return (
    <div className="issue-filters-card" data-testid="issue-filters-card">
      <h2 className="sr-only">Filter Issues</h2>

      {/* Top Row: Search & Dropdowns */}
      <div className="issue-filters__top-row">
        {/* Search */}
        <div className="issue-filters__search-wrapper">
          <span className="issue-filters__search-icon" aria-hidden="true">
            <Icon type="search" size={16} />
          </span>
          <input
            type="text"
            className="issue-filters__search-input"
            placeholder="Search issues, title, description or computer..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            aria-label="Search issues"
          />
        </div>

        {/* Status */}
        <select
          className="issue-filters__select"
          value={statusFilter}
          onChange={(e) => onStatusChange(e.target.value)}
          aria-label="Filter by Status"
        >
          <option value="All Status">All Status</option>
          <option value="Open">Open</option>
          <option value="In Progress">In Progress</option>
          <option value="Resolved">Resolved</option>
        </select>

        {/* Priority */}
        <select
          className="issue-filters__select"
          value={priorityFilter}
          onChange={(e) => onPriorityChange(e.target.value)}
          aria-label="Filter by Priority"
        >
          <option value="All Priority">All Priority</option>
          <option value="Critical">Critical</option>
          <option value="High">High</option>
          <option value="Medium">Medium</option>
          <option value="Low">Low</option>
        </select>

        {/* Computer */}
        <select
          className="issue-filters__select"
          value={computerFilter}
          onChange={(e) => onComputerChange(e.target.value)}
          aria-label="Filter by Computer"
        >
          <option value="All Computers">All Computers</option>
          {computers.map((comp) => (
            <option
              key={comp.id}
              value={comp.hostname || `PC-${comp.id}`}
            >
              {comp.hostname || `Computer #${comp.id}`}
            </option>
          ))}
        </select>

        {/* Date Range */}
        <select
          className="issue-filters__select"
          value={dateRangeFilter}
          onChange={(e) => onDateRangeChange(e.target.value)}
          aria-label="Filter by Date Range"
        >
          <option value="Last 30 Days">Last 30 Days</option>
          <option value="Today">Today</option>
          <option value="Last 7 Days">Last 7 Days</option>
          <option value="Last 90 Days">Last 90 Days</option>
          <option value="All Time">All Time</option>
        </select>
      </div>

      {/* Bottom Row: Active Filters & Actions */}
      <div className="issue-filters__bottom-row">
        <div className="issue-filters__active-group">
          <span className="issue-filters__active-title">
            <Icon type="filter" size={13} />
            <span>Active Filters:</span>
          </span>

          {!hasActiveFilters && (
            <span className="issue-filters__badge-none">None</span>
          )}

          {search && (
            <span className="issue-filters__chip">
              Search: &quot;{search}&quot;
              <button
                type="button"
                className="issue-filters__chip-remove"
                onClick={() => onSearchChange("")}
                title="Remove search filter"
              >
                ✕
              </button>
            </span>
          )}

          {statusFilter && statusFilter !== "All Status" && (
            <span className="issue-filters__chip">
              Status: {statusFilter}
              <button
                type="button"
                className="issue-filters__chip-remove"
                onClick={() => onStatusChange("All Status")}
                title="Remove status filter"
              >
                ✕
              </button>
            </span>
          )}

          {priorityFilter && priorityFilter !== "All Priority" && (
            <span className="issue-filters__chip">
              Priority: {priorityFilter}
              <button
                type="button"
                className="issue-filters__chip-remove"
                onClick={() => onPriorityChange("All Priority")}
                title="Remove priority filter"
              >
                ✕
              </button>
            </span>
          )}

          {computerFilter && computerFilter !== "All Computers" && (
            <span className="issue-filters__chip">
              Computer: {computerFilter}
              <button
                type="button"
                className="issue-filters__chip-remove"
                onClick={() => onComputerChange("All Computers")}
                title="Remove computer filter"
              >
                ✕
              </button>
            </span>
          )}

          {dateRangeFilter && dateRangeFilter !== "Last 30 Days" && (
            <span className="issue-filters__chip">
              Date: {dateRangeFilter}
              <button
                type="button"
                className="issue-filters__chip-remove"
                onClick={() => onDateRangeChange("Last 30 Days")}
                title="Reset date range"
              >
                ✕
              </button>
            </span>
          )}
        </div>

        <div className="issue-filters__actions">
          <button
            type="button"
            className="issue-filters__reset-btn"
            onClick={onReset}
            disabled={loading}
            title="Reset all filters"
          >
            <span>Reset</span>
          </button>

          <button
            type="button"
            className="issue-filters__refresh-btn"
            onClick={onRefresh}
            disabled={loading}
            title="Refresh issues"
          >
            <Icon
              type="refresh"
              size={13}
              className={loading ? "issue-spinning" : ""}
            />
            <span>Refresh</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default IssueFilters;
