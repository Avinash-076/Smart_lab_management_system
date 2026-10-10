import { useCallback, useEffect, useState } from "react";
import { getComputers } from "../../../services/api";
import Icon from "../../../components/ui/Icon";
import StatCard from "../../../components/ui/StatCard";
import ComputerFilters from "../components/ComputerFilters";
import ComputerTable from "../components/ComputerTable";
import Pagination from "../../../components/ui/Pagination";
import EditComputerModal from "../components/EditComputerModal";

/* =====================================================
   COMPONENT
===================================================== */

function ComputerList({ onViewComputer }) {
  /* =====================================================
     COMPUTERS & DATA FETCHING
  ===================================================== */

  const [computers, setComputers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadComputers = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getComputers();
      setComputers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load computers:", err);
      setError(err.message || "Failed to load computers.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;

    async function initialLoad() {
      try {
        setError("");
        const data = await getComputers();
        if (!ignore) {
          setComputers(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        console.error("Failed to load computers:", err);
        if (!ignore) {
          setError(err.message || "Failed to load computers.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }

    initialLoad();

    return () => {
      ignore = true;
    };
  }, []);

  /* =====================================================
     FILTERS & SEARCH
  ===================================================== */

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("All Status");
  const [os, setOs] = useState("All OS");
  const [lab, setLab] = useState("All Labs");
  const [sortBy, setSortBy] = useState("Sort by: Name (A-Z)");
  const [page, setPage] = useState(1);
  const [edit, setEdit] = useState(null);
  const [filterOpen, setFilterOpen] = useState(false);
  const per = 8;

  /* =====================================================
     FILTER
  ===================================================== */

  const filtered = computers.filter((x) => {
    const s = search.toLowerCase().trim();
    const name = (x.hostname || x.name || "").toLowerCase();
    const ip = (x.ip_address || x.ip || "").toLowerCase();
    const mac = (x.mac_address || "").toLowerCase();
    const osStr = (
      x.os_name
        ? `${x.os_name} ${x.os_version || ""}`
        : x.os || ""
    ).toLowerCase();
    const itemStatus = (x.status || "offline").toLowerCase();

    const matchesSearch =
      !s ||
      name.includes(s) ||
      ip.includes(s) ||
      mac.includes(s) ||
      osStr.includes(s);

    const matchesStatus =
      status === "All Status" ||
      itemStatus === status.toLowerCase();

    const matchesOs =
      os === "All OS" ||
      osStr.includes(os.toLowerCase());

    return matchesSearch && matchesStatus && matchesOs;
  });

  /* =====================================================
     SORT
  ===================================================== */

  const sortMap = {
    "Sort by: Name (A-Z)": (a, b) =>
      (a.hostname || a.name || "").localeCompare(
        b.hostname || b.name || ""
      ),

    "Sort by: Name (Z-A)": (a, b) =>
      (b.hostname || b.name || "").localeCompare(
        a.hostname || a.name || ""
      ),

    "Sort by: IP Address (A-Z)": (a, b) =>
      (a.ip_address || a.ip || "").localeCompare(
        b.ip_address || b.ip || "",
        undefined,
        { numeric: true }
      ),

    "Sort by: IP Address (Z-A)": (a, b) =>
      (b.ip_address || b.ip || "").localeCompare(
        a.ip_address || a.ip || "",
        undefined,
        { numeric: true }
      ),

    "Sort by: Status": (a, b) =>
      (a.status || "").localeCompare(b.status || ""),
  };

  const sorted = [...filtered].sort(
    sortMap[sortBy] || (() => 0)
  );

  /* =====================================================
     PAGINATION
  ===================================================== */

  const pages = Math.max(1, Math.ceil(sorted.length / per));
  const rows = sorted.slice((page - 1) * per, page * per);

  const filterKey = `${search}|${status}|${os}|${lab}|${sortBy}`;
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey);

  if (prevFilterKey !== filterKey) {
    setPrevFilterKey(filterKey);
    setPage(1);
  }

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
    const computer = computers.find((c) => c.id === id);
    const compName =
      computer?.hostname || computer?.name || `PC-${id}`;

    if (
      computer &&
      window.confirm(
        `Are you sure you want to delete ${compName}?`
      )
    ) {
      setComputers((prev) =>
        prev.filter((c) => c.id !== id)
      );
    }
  };

  /* =====================================================
     SAVE EDIT
  ===================================================== */

  const save = (computer) => {
    setComputers((prev) =>
      prev.map((c) =>
        c.id === computer.id ? { ...c, ...computer } : c
      )
    );
    setEdit(null);
  };

  /* =====================================================
     EXPORT CSV
  ===================================================== */

  const exportCSV = () => {
    const csv = [
      "Hostname,IP Address,MAC Address,Operating System,Status,Last Seen,Registered At",
      ...sorted.map((x) =>
        [
          x.hostname || x.name || `PC-${x.id}`,
          x.ip_address || x.ip || "",
          x.mac_address || "",
          x.os_name
            ? `${x.os_name} ${x.os_version || ""}`.trim()
            : x.os || "",
          x.status || "offline",
          x.last_seen || "",
          x.registered_at || "",
        ]
          .map((v) => `"${String(v).replace(/"/g, '""')}"`)
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
     STATS COUNTS
  ===================================================== */

  const totalComputers = computers.length;
  const onlineComputers = computers.filter(
    (x) => x.status && x.status.toLowerCase() === "online"
  ).length;
  const offlineComputers = computers.filter(
    (x) => !x.status || x.status.toLowerCase() === "offline"
  ).length;
  const windowsComputers = computers.filter(
    (x) => x.os_name && x.os_name.toLowerCase().includes("windows")
  ).length;

  /* =====================================================
     RETURN
  ===================================================== */

  return (
    <>
      <div className="content">
        {/* PAGE HEADER */}
        <div className="page-top">
          <div>
            <h2>Computer List</h2>
            <p>View and manage all lab computers.</p>
          </div>

          <div className="top-actions">
            <button
              className="export"
              onClick={exportCSV}
              disabled={computers.length === 0}
              title="Export computer list to CSV"
            >
              <Icon type="upload" size={18} />
              Export
            </button>

            <button
              className="refresh"
              onClick={loadComputers}
              disabled={loading}
              title="Refresh computer data from backend"
            >
              <Icon type="refresh" size={18} />
              Refresh
            </button>

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

        {/* STAT CARDS */}
        <div className="cards">
          <StatCard
            icon="computer"
            title="Total Computers"
            number={totalComputers}
            footer="All computers in lab"
            type="blue"
          />

          <StatCard
            icon="computer"
            title="Online"
            number={onlineComputers}
            footer="Online computers"
            type="green"
          />

          <StatCard
            icon="computer"
            title="Offline"
            number={offlineComputers}
            footer="Offline computers"
            type="orange"
          />

          <StatCard
            icon="windows"
            title="Windows Systems"
            number={windowsComputers}
            footer="Windows computers"
            type="purple"
          />
        </div>

        {/* LOADING STATE */}
        {loading && computers.length === 0 ? (
          <div
            className="table-card"
            style={{ padding: "40px 20px", textAlign: "center" }}
          >
            <div className="empty-state">
              <Icon type="refresh" size={32} />
              <h3>Loading computers...</h3>
              <p>Fetching real computer data from backend.</p>
            </div>
          </div>
        ) : error && computers.length === 0 ? (
          /* ERROR STATE */
          <div
            className="table-card"
            style={{ padding: "40px 20px", textAlign: "center" }}
          >
            <div className="empty-state">
              <Icon type="details" size={32} />
              <h3 style={{ color: "#dc2626" }}>
                Failed to load computers
              </h3>
              <p>{error}</p>
              <button
                className="refresh"
                onClick={loadComputers}
                style={{
                  marginTop: "15px",
                  display: "inline-flex",
                }}
              >
                <Icon type="refresh" size={18} />
                Try Again
              </button>
            </div>
          </div>
        ) : computers.length === 0 ? (
          /* EMPTY DATABASE STATE */
          <div
            className="table-card"
            style={{ padding: "40px 20px", textAlign: "center" }}
          >
            <div className="empty-state">
              <Icon type="computer" size={32} />
              <h3>No computers registered</h3>
              <p>No lab computers found in the database.</p>
              <button
                className="refresh"
                onClick={loadComputers}
                style={{
                  marginTop: "15px",
                  display: "inline-flex",
                }}
              >
                <Icon type="refresh" size={18} />
                Refresh
              </button>
            </div>
          </div>
        ) : (
          /* TABLE */
          <div className="table-card">
            <div className="filters">
              <div className="table-search">
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by hostname, IP, MAC, OS..."
                />
                <Icon type="search" size={18} />
              </div>

              <select
                value={os}
                onChange={(e) => setOs(e.target.value)}
              >
                <option>All OS</option>
                <option>Windows 11</option>
                <option>Windows 10</option>
                <option>Windows 7</option>
                <option>Ubuntu</option>
              </select>

              <select
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option>All Status</option>
                <option>Online</option>
                <option>Offline</option>
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
            </div>

            {filtered.length === 0 ? (
              <div className="empty-state" style={{ padding: "40px 20px" }}>
                <Icon type="search" size={32} />
                <h3>No matching computers</h3>
                <p>
                  No computers matched your current search and filter
                  criteria.
                </p>
                <button
                  className="refresh"
                  onClick={reset}
                  style={{
                    marginTop: "15px",
                    display: "inline-flex",
                  }}
                >
                  <Icon type="refresh" size={18} />
                  Reset Filters
                </button>
              </div>
            ) : (
              <>
                <ComputerTable
                  rows={rows}
                  setView={onViewComputer}
                  setEdit={setEdit}
                  del={del}
                />

                <Pagination
                  page={page}
                  pages={pages}
                  setPage={setPage}
                  totalRows={filtered.length}
                  per={per}
                />
              </>
            )}
          </div>
        )}
      </div>

      {/* EDIT MODAL */}
      {edit && (
        <EditComputerModal
          computer={edit}
          onClose={() => setEdit(null)}
          onSave={save}
        />
      )}
    </>
  );
}

export default ComputerList;
