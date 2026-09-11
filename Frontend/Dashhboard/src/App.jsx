import { useEffect, useState } from "react";
import "./App.css";
import Icon from "./components/Icon";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import StatCard from "./components/StatCard";
import ComputerFilters from "./components/ComputerFilters";
import ComputerTable from "./components/ComputerTable";
import Pagination from "./components/Pagination";
import ViewComputerModal from "./components/ViewComputerModal";
import EditComputerModal from "./components/EditComputerModal";
import OtherPage from "./components/OtherPage";

/* =====================================================
   NAVIGATION
===================================================== */

const navItems = [
  ["home", "Dashboard", "dashboard"],
  ["computer", "Computer List", "computers"],
  ["details", "Computer Details", "details"],
  ["software", "Software Inventory", "software"],
  ["issue", "Issue Management", "issues"],
  ["maintenance", "Maintenance Records", "maintenance"],
  ["reports", "Reports", "reports"],
  ["settings", "Settings", "settings"],
  ["users", "User & Role Management", "users"],
];

/* =====================================================
   COMPUTER DATA
===================================================== */

const base = Array.from({ length: 24 }, (_, i) => {
  const n = i + 1;
  const off = [5, 7, 12, 16, 20, 24].includes(n);
  const w11 = n % 2 === 1;
  const total = w11 ? 512 : 256;

  return {
    id: n,
    name: `PC-${String(n).padStart(2, "0")}`,
    ip: `192.168.1.${100 + n}`,
    os:
      n === 7
        ? "Windows 7 Ultimate 64-bit"
        : `${w11 ? "Windows 11" : "Windows 10"} Pro 64-bit`,
    cpu: w11
      ? "Intel Core i5-10400 @ 2.90GHz"
      : "Intel Core i5-9400 @ 2.90GHz",
    ram: w11 ? "16 GB" : "8 GB",
    free: [
      256, 120, 300, 180, 80, 200, 40, 150, 280, 110, 350, 90, 220, 130,
      410, 70, 260, 140, 380, 60, 290, 125, 320, 55,
    ][i],
    total,
    last: n <= 16 ? "21 May 2025" : "20 May 2025",
    time: "10:15 AM",
    status: off ? "Offline" : "Online",
    lab: n <= 12 ? "Lab 1" : "Lab 2",
  };
});

/* =====================================================
   MAIN APP
===================================================== */

function App() {
  const [active, setActive] = useState("computers");

  /* SIDEBAR */
  const [sidebarOpen, setSidebarOpen] = useState(true);

  /* COMPUTER DATA */
  const [computers, setComputers] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("slms_computers")) || base;
    } catch {
      return base;
    }
  });

  useEffect(() => {
    localStorage.setItem("slms_computers", JSON.stringify(computers));
  }, [computers]);

  /* FILTERS */
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("All Status");
  const [os, setOs] = useState("All OS");
  const [lab, setLab] = useState("All Labs");
  const [sortBy, setSortBy] = useState("Sort by: Name (A-Z)");

  const [page, setPage] = useState(1);

  /* MODALS */
  const [view, setView] = useState(null);
  const [edit, setEdit] = useState(null);

  /* DROPDOWNS */
  const [filterOpen, setFilterOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  const per = 8;

  /* =====================================================
     FILTER
  ===================================================== */

  let filtered = computers.filter((x) => {
    const s = search.toLowerCase().trim();

    return (
      (!s ||
        [x.name, x.ip, x.os, x.cpu].some((v) =>
          v.toLowerCase().includes(s)
        )) &&
      (status === "All Status" || x.status === status) &&
      (os === "All OS" || x.os.includes(os)) &&
      (lab === "All Labs" || x.lab === lab)
    );
  });

  /* =====================================================
     SORT
  ===================================================== */

  const sortMap = {
    "Sort by: Name (A-Z)": (a, b) => a.name.localeCompare(b.name),

    "Sort by: Name (Z-A)": (a, b) => b.name.localeCompare(a.name),

    "Sort by: IP Address (A-Z)": (a, b) =>
      a.ip.localeCompare(b.ip, undefined, { numeric: true }),

    "Sort by: IP Address (Z-A)": (a, b) =>
      b.ip.localeCompare(a.ip, undefined, { numeric: true }),

    "Sort by: Status": (a, b) => a.status.localeCompare(b.status),
  };

  filtered = [...filtered].sort(sortMap[sortBy] || (() => 0));

  const pages = Math.max(1, Math.ceil(filtered.length / per));

  const rows = filtered.slice((page - 1) * per, page * per);

  useEffect(() => {
    setPage(1);
  }, [search, status, os, lab, sortBy]);

  /* =====================================================
     RESET
  ===================================================== */

  const reset = () => {
    setSearch("");
    setStatus("All Status");
    setOs("All OS");
    setLab("All Labs");
    setSortBy("Sort by: Name (A-Z)");
    setPage(1);
  };

  /* =====================================================
     DELETE
  ===================================================== */

  const del = (id) => {
    const x = computers.find((c) => c.id === id);

    if (
      x &&
      window.confirm(`Are you sure you want to delete ${x.name}?`)
    ) {
      setComputers((p) => p.filter((c) => c.id !== id));
    }
  };

  /* =====================================================
     SAVE EDIT
  ===================================================== */

  const save = (x) => {
    setComputers((p) =>
      p.map((c) => (c.id === x.id ? x : c))
    );

    setEdit(null);
  };

  /* =====================================================
     EXPORT
  ===================================================== */

  const exportCSV = () => {
    const csv = [
      "Computer Name,IP Address,Operating System,CPU,RAM,Free Disk,Total Disk,Last Seen,Status,Lab",

      ...filtered.map((x) =>
        [
          x.name,
          x.ip,
          x.os,
          x.cpu,
          x.ram,
          `${x.free} GB`,
          `${x.total} GB`,
          `${x.last} ${x.time}`,
          x.status,
          x.lab,
        ]
          .map((v) => `"${v}"`)
          .join(",")
      ),
    ].join("\n");

    const a = document.createElement("a");

    a.href = URL.createObjectURL(
      new Blob([csv], { type: "text/csv" })
    );

    a.download = "SLMS-Computer-List.csv";

    a.click();
  };

  /* =====================================================
     NAVIGATION
  ===================================================== */

  const navigate = (id) => {
    setActive(id);
    setBellOpen(false);
    setProfileOpen(false);
    setFilterOpen(false);
  };

  /* =====================================================
     RETURN
  ===================================================== */

  return (
    <div
      className={`app ${
        sidebarOpen ? "" : "sidebar-collapsed"
      }`}
    >
     <Sidebar
  active={active}
  navigate={navigate}
/>
      {/* =================================================
          MAIN
      ================================================= */}

      <main className="main">
        {/* =================================================
            HEADER
        ================================================= */}
        <Header
          active={active}
          navItems={navItems}
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          search={search}
          setSearch={setSearch}
          bellOpen={bellOpen}
          setBellOpen={setBellOpen}
  profileOpen={profileOpen}
  setProfileOpen={setProfileOpen}
  setFilterOpen={setFilterOpen}
  navigate={navigate}
/>

        {/* =================================================
            COMPUTER LIST
        ================================================= */}

        {active === "computers" ? (
          <>
            <div className="content">

              {/* PAGE TOP */}
              <div className="page-top">
                <div>
                  <h2>Computer List</h2>

                  <p>
                    View and manage all lab computers.
                  </p>
                </div>

                <div className="top-actions">

                  {/* EXPORT */}
                  <button
                    className="export"
                    onClick={exportCSV}
                  >
                    <Icon type="upload" size={18} />
                    Export
                  </button>

                  {/* REFRESH */}
                  <button
                    className="refresh"
                    onClick={reset}
                  >
                    <Icon type="refresh" size={18} />
                    Refresh
                  </button>

                  {/* FILTER */}
                  <ComputerFilters
  search={search}
  setSearch={setSearch}
  status={status}
  setStatus={setStatus}
  os={os}
  setOs={setOs}
  lab={lab}
  setLab={setLab}
  sortBy={sortBy}
  setSortBy={setSortBy}
  filterOpen={filterOpen}
  setFilterOpen={setFilterOpen}
  reset={reset}
/>
                </div>
              </div>

              {/* =================================================
                  CARDS
              ================================================= */}

              <div className="cards">
                <StatCard
                  icon="computer"
                  title="Total Computers"
                  number={computers.length}
                  footer="All computers in lab"
                  type="blue"
                />

                <StatCard
                  icon="computer"
                  title="Online"
                  number={
                    computers.filter(
                      (x) => x.status === "Online"
                    ).length
                  }
                  footer="Online computers"
                  type="green"
                />

                <StatCard
                  icon="computer"
                  title="Offline"
                  number={
                    computers.filter(
                      (x) => x.status === "Offline"
                    ).length
                  }
                  footer="Offline computers"
                  type="orange"
                />

                <StatCard
                  icon="windows"
                  title="Windows"
                  number={computers.length}
                  footer="Windows systems"
                  type="purple"
                />
              </div>

              {/* =================================================
                  TABLE
              ================================================= */}

              <div className="table-card">

                <div className="filters">

                  <div className="table-search">
                    <input
                      value={search}
                      onChange={(e) =>
                        setSearch(e.target.value)
                      }
                      placeholder="Search by computer name, IP..."
                    />

                    <Icon type="search" size={18} />
                  </div>

                  <select
                    value={os}
                    onChange={(e) =>
                      setOs(e.target.value)
                    }
                  >
                    <option>All OS</option>
                    <option>Windows 11</option>
                    <option>Windows 10</option>
                    <option>Windows 7</option>
                  </select>

                  <select
                    value={status}
                    onChange={(e) =>
                      setStatus(e.target.value)
                    }
                  >
                    <option>All Status</option>
                    <option>Online</option>
                    <option>Offline</option>
                  </select>

                  <select
                    value={lab}
                    onChange={(e) =>
                      setLab(e.target.value)
                    }
                  >
                    <option>All Labs</option>
                    <option>Lab 1</option>
                    <option>Lab 2</option>
                  </select>

                  <select
                    value={sortBy}
                    onChange={(e) =>
                      setSortBy(e.target.value)
                    }
                  >
                    <option>
                      Sort by: Name (A-Z)
                    </option>
                    <option>
                      Sort by: Name (Z-A)
                    </option>
                    <option>
                      Sort by: IP Address (A-Z)
                    </option>
                    <option>
                      Sort by: IP Address (Z-A)
                    </option>
                    <option>
                      Sort by: Status
                    </option>
                  </select>
                </div>
                
                <ComputerTable
  rows={rows}
  setView={setView}
  setEdit={setEdit}
  del={del}
/>

                {/* PAGINATION */}
                <Pagination
  page={page}
  pages={pages}
  setPage={setPage}
  rows={rows}
  totalRows={filtered.length}
  per={per}
/>
              </div>
            </div>
          </>
        ) : (
          <OtherPage
  active={active}
  setActive={setActive}
  navItems={navItems}
/>
        )}
      </main>

      {/* VIEW */}
      {view && (
  <ViewComputerModal
    computer={view}
    onClose={() => setView(null)}
  />
)}

      {/* EDIT */}
      {edit && (
  <EditComputerModal
    computer={edit}
    onClose={() => setEdit(null)}
    onSave={save}
  />
)}
    </div>
  );
}

/* =====================================================
   VIEW MODAL
===================================================== */

function ViewModal({ computer, onClose }) {
  const u = Math.round(
    ((computer.total - computer.free) /
      computer.total) *
      100
  );

  return (
    <div
      className="wizard-overlay"
      onClick={onClose}
    >
      <div
        className="computer-wizard"
        onClick={(e) =>
          e.stopPropagation()
        }
      >
        <div className="wizard-header">
          <div className="wizard-title">
            <div className="wizard-computer-icon">
              <Icon
                type="windows"
                size={26}
              />
            </div>

            <div>
              <h2>{computer.name}</h2>
              <p>Computer Details</p>
            </div>
          </div>

          <button
            className="wizard-close"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="wizard-body">
          <h3>
            Computer Information
          </h3>

          <p className="wizard-description">
            Complete information about this lab
            computer.
          </p>

          <div className="details-grid">
            {[
              ["Computer Name", computer.name],
              ["IP Address", computer.ip],
              [
                "Operating System",
                computer.os,
              ],
              ["CPU", computer.cpu],
              ["RAM", computer.ram],
              [
                "Last Seen",
                <>
                  {computer.last}
                  <br />
                  {computer.time}
                </>,
              ],
              ["Status", computer.status],
              ["Lab", computer.lab],
            ].map(([a, b], i) => (
              <div
                className={`detail-box ${
                  i === 2 ? "full" : ""
                }`}
                key={a}
              >
                <span>{a}</span>
                <strong>{b}</strong>
              </div>
            ))}

            <div className="detail-box full">
              <div className="wizard-disk-label">
                <span>Disk Usage</span>
                <b>{u}%</b>
              </div>

              <div className="wizard-disk-track">
                <div
                  className="wizard-disk-fill"
                  style={{
                    width: `${u}%`,
                  }}
                />
              </div>

              <div className="storage-text">
                {computer.free} GB free of{" "}
                {computer.total} GB total
              </div>
            </div>
          </div>
        </div>

        <div className="wizard-footer">
          <button
            className="wizard-cancel"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

/* =====================================================
   EDIT MODAL
===================================================== */

function EditModal({
  computer,
  onClose,
  onSave,
}) {
  const [f, setF] = useState({
    ...computer,
  });

  const update = (k, v) => {
    setF((p) => ({
      ...p,
      [k]: v,
    }));
  };

  return (
    <div
      className="wizard-overlay"
      onClick={onClose}
    >
      <div
        className="edit-modal"
        onClick={(e) =>
          e.stopPropagation()
        }
      >
        <div className="edit-header">
          <div>
            <h2>Edit Computer</h2>
            <p>
              Update computer information
            </p>
          </div>

          <button
            className="wizard-close"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <div className="edit-body">
          <div className="form-grid">
            {[
              ["name", "Computer Name"],
              ["ip", "IP Address"],
              ["cpu", "CPU"],
              ["free", "Free Disk (GB)"],
              ["total", "Total Disk (GB)"],
              ["last", "Last Seen Date"],
              ["time", "Last Seen Time"],
            ].map(([k, l]) => (
              <div
                className="form-group"
                key={k}
              >
                <label>{l}</label>

                <input
                  type={
                    k === "free" ||
                    k === "total"
                      ? "number"
                      : "text"
                  }
                  value={f[k]}
                  onChange={(e) =>
                    update(
                      k,
                      e.target.value
                    )
                  }
                />
              </div>
            ))}

            <div className="form-group">
              <label>
                Operating System
              </label>

              <select
                value={
                  f.os.includes("Windows 11")
                    ? "Windows 11 Pro 64-bit"
                    : f.os.includes("Windows 10")
                    ? "Windows 10 Pro 64-bit"
                    : "Windows 7 Ultimate 64-bit"
                }
                onChange={(e) =>
                  update(
                    "os",
                    e.target.value
                  )
                }
              >
                <option>
                  Windows 11 Pro 64-bit
                </option>
                <option>
                  Windows 10 Pro 64-bit
                </option>
                <option>
                  Windows 7 Ultimate 64-bit
                </option>
              </select>
            </div>

            <div className="form-group">
              <label>RAM</label>

              <select
                value={f.ram}
                onChange={(e) =>
                  update(
                    "ram",
                    e.target.value
                  )
                }
              >
                <option>4 GB</option>
                <option>8 GB</option>
                <option>16 GB</option>
                <option>32 GB</option>
              </select>
            </div>

            <div className="form-group">
              <label>Status</label>

              <select
                value={f.status}
                onChange={(e) =>
                  update(
                    "status",
                    e.target.value
                  )
                }
              >
                <option>Online</option>
                <option>Offline</option>
              </select>
            </div>

            <div className="form-group">
              <label>Lab</label>

              <select
                value={f.lab}
                onChange={(e) =>
                  update(
                    "lab",
                    e.target.value
                  )
                }
              >
                <option>Lab 1</option>
                <option>Lab 2</option>
              </select>
            </div>
          </div>
        </div>

        <div className="edit-footer">
          <button
            className="cancel-edit"
            onClick={onClose}
          >
            Cancel
          </button>

          <button
            className="save-edit"
            onClick={() => {
              const free = Number(f.free);
              const total = Number(f.total);

              if (
                !f.name.trim() ||
                !f.ip.trim() ||
                free < 0 ||
                total <= 0 ||
                free > total
              ) {
                return alert(
                  "Please enter valid details."
                );
              }

              onSave({
                ...f,
                free,
                total,
              });
            }}
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;