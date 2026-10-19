import Icon from "../../../../components/ui/Icon";
import {
  TARGET_RESOURCE_OPTIONS,
  OUTCOME_OPTIONS,
} from "../../utils/auditUtils";
import "./AuditFilters.css";

function AuditFilters({
  search,
  setSearch,
  resultFilter,
  setResultFilter,
  targetTypeFilter,
  setTargetTypeFilter,
  dateFrom,
  setDateFrom,
  dateTo,
  setDateTo,
  activeFiltersCount,
  onResetFilters,
  setPage,
}) {
  return (
    <div className="audit-filters-container" data-testid="audit-filters">
      <div className="audit-filters-header">
        <div className="audit-filters-title-group">
          <div className="audit-filters-icon-wrapper">
            <Icon type="filter" size={16} />
          </div>
          <div>
            <h3 className="audit-filters-heading">Audit Event Explorer</h3>
            <p className="audit-filters-subheading">
              Filter by actor, action type, target resource, outcome, and timestamp range.
            </p>
          </div>
        </div>

        {activeFiltersCount > 0 && (
          <button
            type="button"
            className="audit-filters-clear-btn"
            onClick={onResetFilters}
            title="Reset all active filters"
          >
            <Icon type="close" size={14} />
            <span>Clear Filters ({activeFiltersCount})</span>
          </button>
        )}
      </div>

      <div className="audit-filters-grid">
        {/* Search */}
        <div className="audit-filter-item audit-filter-item--search">
          <label className="audit-filter-label" htmlFor="audit-search-input">
            SEARCH KEYWORD
          </label>
          <div className="audit-search-input-wrapper">
            <Icon type="search" size={15} className="audit-search-icon" />
            <input
              id="audit-search-input"
              type="text"
              placeholder="Action, actor, target, IP..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="audit-filter-input audit-search-field"
            />
          </div>
        </div>

        {/* Outcome */}
        <div className="audit-filter-item">
          <label className="audit-filter-label" htmlFor="audit-outcome-select">
            OUTCOME
          </label>
          <select
            id="audit-outcome-select"
            value={resultFilter}
            onChange={(e) => {
              setResultFilter(e.target.value);
              setPage(1);
            }}
            className="audit-filter-select"
          >
            {OUTCOME_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Target Resource */}
        <div className="audit-filter-item">
          <label className="audit-filter-label" htmlFor="audit-target-select">
            TARGET RESOURCE
          </label>
          <select
            id="audit-target-select"
            value={targetTypeFilter}
            onChange={(e) => {
              setTargetTypeFilter(e.target.value);
              setPage(1);
            }}
            className="audit-filter-select"
          >
            {TARGET_RESOURCE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* From Date */}
        <div className="audit-filter-item">
          <label className="audit-filter-label" htmlFor="audit-date-from">
            FROM DATE
          </label>
          <input
            id="audit-date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => {
              setDateFrom(e.target.value);
              setPage(1);
            }}
            className="audit-filter-input"
          />
        </div>

        {/* To Date */}
        <div className="audit-filter-item">
          <label className="audit-filter-label" htmlFor="audit-date-to">
            TO DATE
          </label>
          <input
            id="audit-date-to"
            type="date"
            value={dateTo}
            onChange={(e) => {
              setDateTo(e.target.value);
              setPage(1);
            }}
            className="audit-filter-input"
          />
        </div>
      </div>
    </div>
  );
}

export default AuditFilters;
