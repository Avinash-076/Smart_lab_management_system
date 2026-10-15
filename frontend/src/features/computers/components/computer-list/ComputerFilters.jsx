import Icon from "../../../../components/ui/Icon";
import "./ComputerFilters.css";

function ComputerFilters({
  search,
  setSearch,
  os,
  setOs,
  status,
  setStatus,
  sortBy,
  setSortBy,
  reset,
}) {
  const hasActiveFilters =
    Boolean(search.trim()) ||
    os !== "All OS" ||
    status !== "All Status" ||
    sortBy !== "Name (A-Z)";

  return (
    <div className="computer-filters-card" data-testid="computer-filters">
      {/* Top Controls Row */}
      <div className="computer-filters__top-row">
        {/* 1. Search by name, IP, or MAC */}
        <div className="computer-filters__search-wrapper">
          <span className="computer-filters__search-icon" aria-hidden="true">
            <Icon type="search" size={17} />
          </span>
          <input
            type="text"
            className="computer-filters__search-input"
            placeholder="Search by computer name, IP address, or MAC address..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search computers"
          />
        </div>

        {/* 2. OS Dropdown */}
        <select
          className="computer-filters__select"
          value={os}
          onChange={(e) => setOs(e.target.value)}
          aria-label="Filter by Operating System"
        >
          <option value="All OS">All OS</option>
          <option value="Windows">Windows</option>
          <option value="Linux">Linux</option>
          <option value="macOS">macOS</option>
        </select>

        {/* 3. Status Dropdown */}
        <select
          className="computer-filters__select"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
          aria-label="Filter by Status"
        >
          <option value="All Status">All Status</option>
          <option value="Online">Online</option>
          <option value="Offline">Offline</option>
        </select>

        {/* 4. Sort By Control */}
        <div className="computer-filters__sort-wrapper">
          <span className="computer-filters__sort-label">Sort by</span>
          <select
            className="computer-filters__select"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            aria-label="Sort order"
          >
            <option value="Name (A-Z)">Name (A-Z)</option>
            <option value="Name (Z-A)">Name (Z-A)</option>
            <option value="IP Address (Asc)">IP Address (Asc)</option>
            <option value="IP Address (Desc)">IP Address (Desc)</option>
            <option value="Status">Status</option>
            <option value="Last Seen">Last Seen</option>
          </select>
        </div>
      </div>

      {/* Bottom Status Row: Active Filters & Clear */}
      <div className="computer-filters__bottom-row">
        <div className="computer-filters__active-group">
          <span className="computer-filters__active-title">
            <Icon type="filter" size={14} />
            Active Filters:
          </span>

          {!hasActiveFilters ? (
            <span className="computer-filters__badge-none">None</span>
          ) : (
            <>
              {search.trim() && (
                <span className="computer-filters__chip">
                  {`Search: "${search.trim()}"`}
                  <button
                    type="button"
                    className="computer-filters__chip-remove"
                    onClick={() => setSearch("")}
                    title="Remove search filter"
                    aria-label="Remove search filter"
                  >
                    ×
                  </button>
                </span>
              )}

              {os !== "All OS" && (
                <span className="computer-filters__chip">
                  {`OS: ${os}`}
                  <button
                    type="button"
                    className="computer-filters__chip-remove"
                    onClick={() => setOs("All OS")}
                    title="Remove OS filter"
                    aria-label="Remove OS filter"
                  >
                    ×
                  </button>
                </span>
              )}

              {status !== "All Status" && (
                <span className="computer-filters__chip">
                  {`Status: ${status}`}
                  <button
                    type="button"
                    className="computer-filters__chip-remove"
                    onClick={() => setStatus("All Status")}
                    title="Remove status filter"
                    aria-label="Remove status filter"
                  >
                    ×
                  </button>
                </span>
              )}

              {sortBy !== "Name (A-Z)" && (
                <span className="computer-filters__chip">
                  {`Sort: ${sortBy}`}
                  <button
                    type="button"
                    className="computer-filters__chip-remove"
                    onClick={() => setSortBy("Name (A-Z)")}
                    title="Reset sort"
                    aria-label="Reset sort"
                  >
                    ×
                  </button>
                </span>
              )}
            </>
          )}
        </div>

        <button
          type="button"
          className="computer-filters__clear-btn"
          onClick={reset}
          title="Clear all filters and reset sort"
        >
          <Icon type="clear-filter" size={14} />
          Clear Filters
        </button>
      </div>
    </div>
  );
}

export default ComputerFilters;