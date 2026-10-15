import { useState } from "react";
import Icon from "../../../../components/ui/Icon";
import "./ProcessFilters.css";

export default function ProcessFilters({
  filters,
  availableUsers = [],
  onApply,
  onExport,
  loading = false,
}) {
  const [search, setSearch] = useState(filters.search || "");
  const [status, setStatus] = useState(filters.status || "all");
  const [cpuUsage, setCpuUsage] = useState(filters.cpu_usage || "all");
  const [memoryUsage, setMemoryUsage] = useState(filters.memory_usage || "all");
  const [user, setUser] = useState(filters.user || "all");

  const handleSubmit = (e) => {
    e.preventDefault();
    onApply({
      search: search.trim(),
      status: status === "all" ? "" : status,
      cpu_usage: cpuUsage === "all" ? "" : cpuUsage,
      memory_usage: memoryUsage === "all" ? "" : memoryUsage,
      user: user === "all" ? "" : user,
    });
  };

  const handleClear = () => {
    setSearch("");
    setStatus("all");
    setCpuUsage("all");
    setMemoryUsage("all");
    setUser("all");
    onApply({
      search: "",
      status: "",
      cpu_usage: "",
      memory_usage: "",
      user: "",
    });
  };

  const hasActiveFilters = Boolean(
    search.trim() ||
      (status && status !== "all") ||
      (cpuUsage && cpuUsage !== "all") ||
      (memoryUsage && memoryUsage !== "all") ||
      (user && user !== "all")
  );

  // Parse cpu_min value from select
  const cpuOptions = [
    { label: "All", value: "all" },
    { label: "> 1%", value: "1" },
    { label: "> 5%", value: "5" },
    { label: "> 10%", value: "10" },
    { label: "> 20%", value: "20" },
  ];

  // Parse memory_min value from select (in MB)
  const memoryOptions = [
    { label: "All", value: "all" },
    { label: "> 50 MB", value: "50" },
    { label: "> 100 MB", value: "100" },
    { label: "> 250 MB", value: "250" },
    { label: "> 500 MB", value: "500" },
    { label: "> 1 GB", value: "1024" },
  ];

  // Status options
  const defaultStatusOptions = [
    { label: "All Processes", value: "all" },
    { label: "Running", value: "running" },
    { label: "Suspended", value: "suspended" },
    { label: "Not Responding", value: "not responding" },
    { label: "Zombie", value: "zombie" },
    { label: "Others", value: "others" },
  ];

  return (
    <form className="process-filter-toolbar" onSubmit={handleSubmit}>
      {/* Search Input */}
      <div className="process-search-box">
        <Icon type="search" size={16} className="process-search-icon" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search process name, PID, or path..."
          className="process-search-input"
          id="process-search-input"
        />
        {search && (
          <button
            type="button"
            className="process-clear-btn"
            onClick={() => setSearch("")}
            title="Clear search query"
          >
            ×
          </button>
        )}
      </div>

      {/* Process Status Filter */}
      <div className="process-filter-select-wrapper">
        <label className="process-filter-label" htmlFor="process-status-select">
          Process Status
        </label>
        <select
          id="process-status-select"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          className="process-select-input"
        >
          {defaultStatusOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* CPU Usage Filter */}
      <div className="process-filter-select-wrapper">
        <label className="process-filter-label" htmlFor="process-cpu-select">
          CPU Usage
        </label>
        <select
          id="process-cpu-select"
          value={cpuUsage}
          onChange={(e) => setCpuUsage(e.target.value)}
          className="process-select-input"
        >
          {cpuOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Memory Usage Filter */}
      <div className="process-filter-select-wrapper">
        <label className="process-filter-label" htmlFor="process-memory-select">
          Memory Usage
        </label>
        <select
          id="process-memory-select"
          value={memoryUsage}
          onChange={(e) => setMemoryUsage(e.target.value)}
          className="process-select-input"
        >
          {memoryOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* User Filter */}
      <div className="process-filter-select-wrapper">
        <label className="process-filter-label" htmlFor="process-user-select">
          User
        </label>
        <select
          id="process-user-select"
          value={user}
          onChange={(e) => setUser(e.target.value)}
          className="process-select-input"
        >
          <option value="all">All Users</option>
          {availableUsers.map((u) => (
            <option key={u} value={u}>
              {u}
            </option>
          ))}
        </select>
      </div>

      {/* Action Buttons: Apply & Clear */}
      <div className="process-filter-buttons">
        <button
          type="submit"
          className="process-apply-btn"
          disabled={loading}
          id="process-apply-filters-btn"
        >
          Apply
        </button>

        {hasActiveFilters && (
          <button
            type="button"
            className="process-reset-btn"
            onClick={handleClear}
            title="Reset all filters to defaults"
          >
            Clear
          </button>
        )}
      </div>

      {/* Export Button */}
      <div className="process-toolbar-export-container">
        <button
          type="button"
          className="process-export-btn"
          onClick={onExport}
          disabled={loading}
          id="process-export-csv-btn"
          title="Export matching processes to CSV"
        >
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
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          <span>Export</span>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </div>
    </form>
  );
}
