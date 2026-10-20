import Icon from "../../../../components/ui/Icon";
import "./SoftwareFilters.css";

export default function SoftwareFilters({
  search,
  setSearch,
  osFilter,
  setOsFilter,
  publisherFilter,
  setPublisherFilter,
  computerFilter,
  setComputerFilter,
  statusFilter,
  setStatusFilter,
  computers = [],
  availablePublishers = [],
  availableOs = [],
  onApply,
  onReset,
}) {
  const handleKeyDown = (e) => {
    if (e.key === "Enter") {
      onApply();
    }
  };

  return (
    <div className="software-filters-card">
      <div className="software-filters-card-header">
        <div className="software-filters-header-title">
          <Icon type="filter" size={16} />
          <span>Software Filters</span>
        </div>
      </div>

      <div className="software-filters-row">
        {/* Search Input */}
        <div className="software-filter-field search-field">
          <label className="software-filter-label">Search</label>
          <div className="software-filter-input-wrap">
            <input
              type="text"
              placeholder="Search software name, publisher, or version..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleKeyDown}
              className="software-filter-input"
            />
            <span className="software-filter-input-icon">
              <Icon type="search" size={16} />
            </span>
          </div>
        </div>

        {/* Operating System */}
        <div className="software-filter-field">
          <label className="software-filter-label">Operating System</label>
          <select
            value={osFilter}
            onChange={(e) => setOsFilter(e.target.value)}
            className="software-filter-select"
          >
            <option value="All OS">All OS</option>
            <option value="Windows 10">Windows 10</option>
            <option value="Windows 11">Windows 11</option>
            {availableOs
              .filter((os) => !["Windows 10", "Windows 11"].includes(os))
              .map((os) => (
                <option key={os} value={os}>
                  {os}
                </option>
              ))}
          </select>
        </div>

        {/* Publisher */}
        <div className="software-filter-field">
          <label className="software-filter-label">Publisher</label>
          <select
            value={publisherFilter}
            onChange={(e) => setPublisherFilter(e.target.value)}
            className="software-filter-select"
          >
            <option value="All Publishers">All Publishers</option>
            {availablePublishers.map((pub) => (
              <option key={pub} value={pub}>
                {pub}
              </option>
            ))}
          </select>
        </div>

        {/* Computer */}
        <div className="software-filter-field">
          <label className="software-filter-label">Computer</label>
          <select
            value={computerFilter}
            onChange={(e) => setComputerFilter(e.target.value)}
            className="software-filter-select"
          >
            <option value="All Computers">All Computers</option>
            {computers.map((comp) => (
              <option key={comp.id} value={comp.id}>
                {comp.hostname} (#{comp.id})
              </option>
            ))}
          </select>
        </div>

        {/* Installation Status */}
        <div className="software-filter-field">
          <label className="software-filter-label">Installation Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="software-filter-select"
          >
            <option value="All Status">All Status</option>
            <option value="Installed">Installed</option>
            <option value="Active">Standard Application</option>
            <option value="Utility">System Utility</option>
          </select>
        </div>

        {/* Buttons */}
        <div className="software-filter-buttons">
          <button
            type="button"
            className="software-filter-apply-btn"
            onClick={onApply}
          >
            <Icon type="search" size={15} />
            <span>Apply Filters</span>
          </button>

          <button
            type="button"
            className="software-filter-reset-btn"
            onClick={onReset}
            title="Reset filters"
          >
            <Icon type="refresh" size={15} />
            <span>Reset</span>
          </button>
        </div>
      </div>
    </div>
  );
}
