import { useState } from "react";
import Icon from "../../../components/ui/Icon";
import "./SoftwareFilters.css";

export default function SoftwareFilters({
  filters,
  availablePublishers = [],
  availableArchitectures = [],
  onApply,
  onExport,
  loading = false,
}) {
  const [search, setSearch] = useState(filters.search || "");
  const [publisher, setPublisher] = useState(filters.publisher || "all");
  const [dateRange, setDateRange] = useState(filters.date_range || "all");
  const [architecture, setArchitecture] = useState(filters.architecture || "all");

  const handleSubmit = (e) => {
    e.preventDefault();
    onApply({
      search: search.trim(),
      publisher: publisher === "all" ? "" : publisher,
      date_range: dateRange === "all" ? "" : dateRange,
      architecture: architecture === "all" ? "" : architecture,
    });
  };

  const handleClear = () => {
    setSearch("");
    setPublisher("all");
    setDateRange("all");
    setArchitecture("all");
    onApply({
      search: "",
      publisher: "",
      date_range: "",
      architecture: "",
    });
  };

  const hasActiveFilters = Boolean(
    search.trim() ||
    (publisher && publisher !== "all") ||
    (dateRange && dateRange !== "all") ||
    (architecture && architecture !== "all")
  );

  return (
    <form className="software-filter-toolbar" onSubmit={handleSubmit}>
      {/* Search Input */}
      <div className="software-search-box">
        <Icon type="search" size={16} className="software-search-icon" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search software (name, publisher, etc.)..."
          className="software-search-input"
          id="software-search-input"
        />
        {search && (
          <button
            type="button"
            className="software-clear-btn"
            onClick={() => setSearch("")}
            title="Clear search query"
          >
            ×
          </button>
        )}
      </div>

      {/* Publisher Dropdown */}
      <div className="software-filter-select-wrapper">
        <label className="software-filter-label" htmlFor="software-publisher-select">
          Publisher
        </label>
        <select
          id="software-publisher-select"
          value={publisher}
          onChange={(e) => setPublisher(e.target.value)}
          className="software-select-input"
        >
          <option value="all">All Publishers</option>
          {availablePublishers.map((pub) => (
            <option key={pub} value={pub}>
              {pub}
            </option>
          ))}
        </select>
      </div>

      {/* Installation Date Filter */}
      <div className="software-filter-select-wrapper">
        <label className="software-filter-label" htmlFor="software-date-select">
          Installation Date
        </label>
        <select
          id="software-date-select"
          value={dateRange}
          onChange={(e) => setDateRange(e.target.value)}
          className="software-select-input"
        >
          <option value="all">All Time</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
          <option value="90d">Last 90 Days</option>
          <option value="365d">Last 1 Year</option>
        </select>
      </div>

      {/* Architecture Dropdown */}
      <div className="software-filter-select-wrapper">
        <label className="software-filter-label" htmlFor="software-arch-select">
          Architecture
        </label>
        <select
          id="software-arch-select"
          value={architecture}
          onChange={(e) => setArchitecture(e.target.value)}
          className="software-select-input"
        >
          <option value="all">All</option>
          <option value="64-bit">64-bit</option>
          <option value="32-bit">32-bit</option>
          {availableArchitectures
            .filter((a) => a && a !== "64-bit" && a !== "32-bit")
            .map((arch) => (
              <option key={arch} value={arch}>
                {arch}
              </option>
            ))}
        </select>
      </div>

      {/* Actions: Apply & Reset */}
      <div className="software-filter-buttons">
        <button
          type="submit"
          className="software-apply-btn"
          id="software-apply-filter-btn"
          disabled={loading}
        >
          Apply
        </button>

        {hasActiveFilters && (
          <button
            type="button"
            className="software-reset-btn"
            onClick={handleClear}
            title="Reset filters to default"
          >
            Reset
          </button>
        )}
      </div>

      {/* Right side: Export Button */}
      <div className="software-toolbar-export-container">
        <button
          type="button"
          className="software-export-btn"
          id="software-export-csv-btn"
          onClick={onExport}
          title="Export filtered inventory to CSV"
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          <span>Export</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </div>
    </form>
  );
}
