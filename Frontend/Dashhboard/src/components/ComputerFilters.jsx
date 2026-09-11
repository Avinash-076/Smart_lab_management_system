import Icon from "./Icon";

function ComputerFilters({
  search,
  setSearch,
  status,
  setStatus,
  os,
  setOs,
  lab,
  setLab,
  sortBy,
  setSortBy,
  filterOpen,
  setFilterOpen,
  reset,
}) {
  return (
    <div className="filters-section">
      <div className="filter-search">
        <Icon type="search" size={18} />

        <input
          type="text"
          placeholder="Search by name, IP, OS or CPU..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="filter-controls">
        <select
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option>All Status</option>
          <option>Online</option>
          <option>Offline</option>
        </select>

        <select
          value={os}
          onChange={(e) => setOs(e.target.value)}
        >
          <option>All OS</option>
          <option>Windows 10</option>
          <option>Windows 11</option>
          <option>Windows 7</option>
        </select>

        <select
          value={lab}
          onChange={(e) => setLab(e.target.value)}
        >
          <option>All Labs</option>
          <option>Lab 1</option>
          <option>Lab 2</option>
        </select>

        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
        >
          <option>Sort by: Name (A-Z)</option>
          <option>Sort by: Name (Z-A)</option>
          <option>Sort by: IP Address (A-Z)</option>
          <option>Sort by: IP Address (Z-A)</option>
          <option>Sort by: Status</option>
        </select>

        <div className="filter-popup-wrapper">
          <button
            className="filter-button"
            onClick={() =>
              setFilterOpen((prev) => !prev)
            }
          >
            <Icon type="filter" size={18} />
            Filter
          </button>

          {filterOpen && (
            <div className="slms-dropdown filter-dropdown">
              <div className="dropdown-heading">
                <div>
                  <b>Filters</b>
                  <small>
                    Narrow down computers
                  </small>
                </div>
              </div>

              <button
                className="dropdown-action"
                onClick={reset}
              >
                <span className="dropdown-action-icon">
                  <Icon type="refresh" size={18} />
                </span>

                <span>
                  <b>Reset Filters</b>
                  <small>
                    Clear all selected filters
                  </small>
                </span>
              </button>
            </div>
          )}
        </div>

        <button
          className="reset-button"
          onClick={reset}
        >
          <Icon type="refresh" size={17} />
          Reset
        </button>
      </div>
    </div>
  );
}

export default ComputerFilters;