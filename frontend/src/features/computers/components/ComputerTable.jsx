import { useState, useEffect, useRef } from "react";
import Icon from "../../../components/ui/Icon";
import {
  getOsIconInfo,
  formatLastSeen,
  getDiskMetrics,
} from "../utils/computerUtils";
import "./ComputerTable.css";

function ComputerTable({
  rows = [],
  selectedIds = new Set(),
  onToggleSelect,
  onToggleSelectAll,
  allPageSelected = false,
  isIndeterminate = false,
  onSort,
  setView,
  setEdit,
  del,
}) {
  const headerCheckboxRef = useRef(null);
  const [openMenuId, setOpenMenuId] = useState(null);

  // Sync indeterminate property on header checkbox
  useEffect(() => {
    if (headerCheckboxRef.current) {
      headerCheckboxRef.current.indeterminate = isIndeterminate;
    }
  }, [isIndeterminate]);

  // Close more menu on click outside
  useEffect(() => {
    function handleOutside(e) {
      if (!e.target.closest(".computer-table__actions")) {
        setOpenMenuId(null);
      }
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  return (
    <div className="computer-table-card" data-testid="computer-table-card">
      <div className="computer-table-scroll">
        <table className="computer-table" data-testid="computer-table">
          <thead>
            <tr>
              {/* 1. Selection Checkbox */}
              <th className="computer-table__checkbox-col">
                <input
                  type="checkbox"
                  ref={headerCheckboxRef}
                  checked={allPageSelected}
                  onChange={(e) => onToggleSelectAll?.(e.target.checked)}
                  aria-label="Select all computers on current page"
                  className="computer-table__checkbox"
                />
              </th>

              {/* 2. Computer Name */}
              <th className="sortable" onClick={() => onSort?.("name")}>
                <span className="computer-table__th-content">
                  Computer Name
                  <span className="computer-table__sort-icon">↕</span>
                </span>
              </th>

              {/* 3. IP Address */}
              <th className="sortable" onClick={() => onSort?.("ip")}>
                <span className="computer-table__th-content">
                  IP Address
                  <span className="computer-table__sort-icon">↕</span>
                </span>
              </th>

              {/* 4. Operating System */}
              <th className="sortable" onClick={() => onSort?.("os")}>
                <span className="computer-table__th-content">
                  Operating System
                  <span className="computer-table__sort-icon">↕</span>
                </span>
              </th>

              {/* 5. CPU */}
              <th>
                <span className="computer-table__th-content">
                  CPU
                  <span className="computer-table__sort-icon">↕</span>
                </span>
              </th>

              {/* 6. RAM */}
              <th>
                <span className="computer-table__th-content">
                  RAM
                  <span className="computer-table__sort-icon">↕</span>
                </span>
              </th>

              {/* 7. Disk */}
              <th>
                <span className="computer-table__th-content">
                  Disk (Free / Total)
                  <span className="computer-table__sort-icon">↕</span>
                </span>
              </th>

              {/* 8. Last Seen */}
              <th className="sortable" onClick={() => onSort?.("last_seen")}>
                <span className="computer-table__th-content">
                  Last Seen
                  <span className="computer-table__sort-icon">↕</span>
                </span>
              </th>

              {/* 9. Status */}
              <th className="sortable" onClick={() => onSort?.("status")}>
                <span className="computer-table__th-content">
                  Status
                  <span className="computer-table__sort-icon">↕</span>
                </span>
              </th>

              {/* 10. Actions */}
              <th>Actions</th>
            </tr>
          </thead>

          <tbody>
            {rows.map((pc) => {
              const isSelected = selectedIds.has(pc.id);
              const hostname = pc.hostname || pc.name || `PC-${pc.id}`;
              const ip = pc.ip_address || pc.ip || "—";
              const os = pc.os_name
                ? `${pc.os_name} ${pc.os_version || ""}`.trim()
                : pc.os || "—";
              const isOnline = (pc.status || "").toLowerCase() === "online";
              const osIcon = getOsIconInfo(pc);
              const lastSeen = formatLastSeen(pc.last_seen);
              const disk = getDiskMetrics(pc);

              // CPU formatting
              const rawCpu = pc.cpu || "";
              let cpuLine1 = rawCpu;
              let cpuLine2 = "";
              if (rawCpu.includes("@")) {
                const parts = rawCpu.split("@");
                cpuLine1 = parts[0].trim();
                cpuLine2 = `@ ${parts[1].trim()}`;
              }

              // RAM formatting
              const rawRam = pc.ram;
              const ramText = rawRam
                ? typeof rawRam === "number"
                  ? `${rawRam} GB`
                  : String(rawRam).toUpperCase().includes("GB")
                  ? rawRam
                  : `${rawRam} GB`
                : "—";

              return (
                <tr key={pc.id} className={isSelected ? "selected" : ""}>
                  {/* 1. Checkbox */}
                  <td className="computer-table__checkbox-col">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelect?.(pc.id)}
                      aria-label={`Select ${hostname}`}
                      className="computer-table__checkbox"
                    />
                  </td>

                  {/* 2. Computer Name with OS Icon */}
                  <td>
                    <div className="computer-table__name-cell">
                      <span className={`computer-table__os-icon ${osIcon.className}`}>
                        <Icon type={osIcon.type} size={18} />
                      </span>
                      <button
                        type="button"
                        className="computer-table__hostname"
                        onClick={() => setView?.(pc)}
                        title={`View details for ${hostname}`}
                      >
                        {hostname}
                      </button>
                    </div>
                  </td>

                  {/* 3. IP Address */}
                  <td>{ip}</td>

                  {/* 4. Operating System */}
                  <td>{os}</td>

                  {/* 5. CPU */}
                  <td>
                    {rawCpu ? (
                      <div className="computer-table__cpu-text">
                        <div>{cpuLine1}</div>
                        {cpuLine2 && <div className="computer-table__cpu-sub">{cpuLine2}</div>}
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>

                  {/* 6. RAM */}
                  <td>
                    <span className="computer-table__ram-text">{ramText}</span>
                  </td>

                  {/* 7. Disk (Free / Total) */}
                  <td className="computer-table__disk-cell">
                    {disk ? (
                      <div>
                        <div className="computer-table__disk-info">
                          <span>{`${disk.freeGB} GB / ${disk.totalGB} GB`}</span>
                          <span className="computer-table__disk-pct">{`${disk.usedPct}%`}</span>
                        </div>
                        <div className="computer-table__disk-bar">
                          <div
                            className="computer-table__disk-fill"
                            style={{ width: `${disk.usedPct}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      "—"
                    )}
                  </td>

                  {/* 8. Last Seen */}
                  <td>
                    <div className="computer-table__last-seen">
                      <div className="computer-table__last-seen-date">{lastSeen.date}</div>
                      {lastSeen.time && (
                        <div className="computer-table__last-seen-time">{lastSeen.time}</div>
                      )}
                    </div>
                  </td>

                  {/* 9. Status */}
                  <td>
                    <span
                      className={`status-pill ${
                        isOnline ? "status-pill--online" : "status-pill--offline"
                      }`}
                    >
                      <span className="status-pill__dot" aria-hidden="true" />
                      {isOnline ? "Online" : "Offline"}
                    </span>
                  </td>

                  {/* 10. Actions */}
                  <td>
                    <div className="computer-table__actions">
                      <button
                        type="button"
                        className="action-btn action-btn--view"
                        onClick={() => setView?.(pc)}
                        title="View Details"
                        aria-label={`View details for ${hostname}`}
                      >
                        <Icon type="eye" size={15} />
                      </button>

                      <button
                        type="button"
                        className="action-btn action-btn--edit"
                        onClick={() => setEdit?.(pc)}
                        title="Edit Computer"
                        aria-label={`Edit ${hostname}`}
                      >
                        <Icon type="edit" size={15} />
                      </button>

                      <button
                        type="button"
                        className="action-btn action-btn--delete"
                        onClick={() => del?.(pc)}
                        title="Delete Computer"
                        aria-label={`Delete ${hostname}`}
                      >
                        <Icon type="trash" size={15} />
                      </button>

                      <button
                        type="button"
                        className="action-btn action-btn--more"
                        onClick={() =>
                          setOpenMenuId((cur) => (cur === pc.id ? null : pc.id))
                        }
                        title="More Actions"
                        aria-label={`More actions for ${hostname}`}
                        aria-expanded={openMenuId === pc.id}
                      >
                        <Icon type="more-vertical" size={15} />
                      </button>

                      {openMenuId === pc.id && (
                        <div className="more-dropdown" role="menu">
                          <button
                            type="button"
                            className="more-dropdown__item"
                            role="menuitem"
                            onClick={() => {
                              setOpenMenuId(null);
                              setView?.(pc);
                            }}
                          >
                            <Icon type="eye" size={14} />
                            View Details
                          </button>

                          <button
                            type="button"
                            className="more-dropdown__item"
                            role="menuitem"
                            onClick={() => {
                              setOpenMenuId(null);
                              setEdit?.(pc);
                            }}
                          >
                            <Icon type="edit" size={14} />
                            Edit Computer
                          </button>

                          <button
                            type="button"
                            className="more-dropdown__item more-dropdown__item--danger"
                            role="menuitem"
                            onClick={() => {
                              setOpenMenuId(null);
                              del?.(pc);
                            }}
                          >
                            <Icon type="trash" size={14} />
                            Delete
                          </button>
                        </div>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default ComputerTable;