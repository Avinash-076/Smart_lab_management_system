import { useState } from "react";
import "./CommandHistoryFilters.css";

export default function CommandHistoryFilters({
  filters,
  onApply,
  onExport,
  loading = false,
}) {
  const [search, setSearch] = useState(filters.search || "");
  const [status, setStatus] = useState(filters.status || "all");
  const [dateRange, setDateRange] = useState(filters.date_range || "30d");

  const handleSubmit = (e) => {
    e?.preventDefault();
    onApply({
      search: search.trim(),
      status: status === "all" ? "" : status,
      date_range: dateRange,
    });
  };

  const handleClear = () => {
    setSearch("");
    setStatus("all");
    setDateRange("all");
    onApply({
      search: "",
      status: "",
      date_range: "all",
    });
  };

  const hasActiveFilters = Boolean(
    search.trim() ||
    (status && status !== "all") ||
    (dateRange && dateRange !== "all")
  );

  return (
    <form className="cmd-filters-bar" onSubmit={handleSubmit}>
      {/* 1. Search Bar */}
      <div className="cmd-search-wrapper">
        <span className="cmd-search-icon">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </span>
        <input
          type="text"
          className="cmd-search-input"
          placeholder="Search commands, message text, or user..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search && (
          <button
            type="button"
            className="cmd-search-clear"
            onClick={() => setSearch("")}
            title="Clear search"
          >
            ✕
          </button>
        )}
      </div>

      {/* 2. Status Select */}
      <div className="cmd-filter-item">
        <select
          className="cmd-filter-select"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="all">All Status</option>
          <option value="executed">Success</option>
          <option value="failed">Failed</option>
          <option value="pending">Pending</option>
          <option value="delivered">Delivered</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* 3. Date Range Select */}
      <div className="cmd-filter-item">
        <select
          className="cmd-filter-select"
          value={dateRange}
          onChange={(e) => setDateRange(e.target.value)}
        >
          <option value="all">All Time</option>
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
        </select>
      </div>

      {/* 4. Apply Button */}
      <button
        type="submit"
        className="cmd-apply-btn"
        disabled={loading}
      >
        Apply
      </button>

      {/* 5. Clear Filters Button */}
      {hasActiveFilters && (
        <button
          type="button"
          className="cmd-reset-btn"
          onClick={handleClear}
          title="Reset all filters"
        >
          Reset
        </button>
      )}

      {/* 6. Export Button */}
      {onExport && (
        <button
          type="button"
          className="cmd-export-btn"
          onClick={onExport}
          title="Export commands history as CSV"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          Export
        </button>
      )}
    </form>
  );
}
