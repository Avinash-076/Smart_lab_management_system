import Icon from "../../../../components/ui/Icon";
import "./MaintenanceFilters.css";

function MaintenanceFilters({
  search,
  onSearchChange,
  statusFilter,
  onStatusChange,
  typeFilter,
  onTypeChange,
  computerFilter,
  onComputerChange,
  computers = [],
  onRefresh,
  onReset,
  loading = false,
}) {
  const hasActiveFilters = Boolean(
    search ||
      (statusFilter && statusFilter !== "All Status") ||
      (typeFilter && typeFilter !== "All Types") ||
      (computerFilter && computerFilter !== "All Computers")
  );

  return (
    <div className="maint-filters-card" data-testid="maintenance-filters-card">
      <h2 className="sr-only">Filter Maintenance Records</h2>

      {/* Top Row: Search & Dropdowns */}
      <div className="maint-filters__top-row">
        {/* Search */}
        <div className="maint-filters__search-wrapper">
          <span className="maint-filters__search-icon" aria-hidden="true">
            <Icon type="search" size={16} />
          </span>
          <input
            type="text"
            className="maint-filters__search-input"
            placeholder="Search by computer, task title, description, or technician..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            aria-label="Search maintenance records"
          />
        </div>

        {/* Status Dropdown */}
        <select
          className="maint-filters__select"
          value={statusFilter}
          onChange={(e) => onStatusChange(e.target.value)}
          aria-label="Filter by Status"
        >
          <option value="All Status">All Status</option>
          <option value="Scheduled">Scheduled</option>
          <option value="In Progress">In Progress</option>
          <option value="Completed">Completed</option>
          <option value="Cancelled">Cancelled</option>
        </select>

        {/* Type Dropdown */}
        <select
          className="maint-filters__select"
          value={typeFilter}
          onChange={(e) => onTypeChange(e.target.value)}
          aria-label="Filter by Type"
        >
          <option value="All Types">All Types</option>
          <option value="Preventive">Preventive</option>
          <option value="Corrective">Corrective</option>
          <option value="Emergency">Emergency</option>
          <option value="Hardware">Hardware</option>
          <option value="Software">Software</option>
        </select>

        {/* Computer Dropdown */}
        <select
          className="maint-filters__select"
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
      </div>

      {/* Bottom Row: Active Filters & Actions */}
      <div className="maint-filters__bottom-row">
        <div className="maint-filters__active-group">
          <span className="maint-filters__active-title">
            <Icon type="filter" size={13} />
            <span>Active Filters:</span>
          </span>

          {!hasActiveFilters && (
            <span className="maint-filters__badge-none">None</span>
          )}

          {search && (
            <span className="maint-filters__chip">
              Search: &quot;{search}&quot;
              <button
                type="button"
                className="maint-filters__chip-remove"
                onClick={() => onSearchChange("")}
                title="Remove search filter"
              >
                ✕
              </button>
            </span>
          )}

          {statusFilter && statusFilter !== "All Status" && (
            <span className="maint-filters__chip">
              Status: {statusFilter}
              <button
                type="button"
                className="maint-filters__chip-remove"
                onClick={() => onStatusChange("All Status")}
                title="Remove status filter"
              >
                ✕
              </button>
            </span>
          )}

          {typeFilter && typeFilter !== "All Types" && (
            <span className="maint-filters__chip">
              Type: {typeFilter}
              <button
                type="button"
                className="maint-filters__chip-remove"
                onClick={() => onTypeChange("All Types")}
                title="Remove type filter"
              >
                ✕
              </button>
            </span>
          )}

          {computerFilter && computerFilter !== "All Computers" && (
            <span className="maint-filters__chip">
              Computer: {computerFilter}
              <button
                type="button"
                className="maint-filters__chip-remove"
                onClick={() => onComputerChange("All Computers")}
                title="Remove computer filter"
              >
                ✕
              </button>
            </span>
          )}
        </div>

        <div className="maint-filters__actions">
          <button
            type="button"
            className="maint-filters__reset-btn"
            onClick={onReset}
            disabled={loading}
            title="Reset all filters"
          >
            <span>Reset</span>
          </button>

          <button
            type="button"
            className="maint-filters__refresh-btn"
            onClick={onRefresh}
            disabled={loading}
            title="Refresh records"
          >
            <Icon
              type="refresh"
              size={13}
              className={loading ? "maint-spinning" : ""}
            />
            <span>Refresh</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default MaintenanceFilters;
