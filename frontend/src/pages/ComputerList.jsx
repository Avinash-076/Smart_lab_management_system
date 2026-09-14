import { useEffect, useState } from "react";

import Icon from "../components/Icon";
import StatCard from "../components/StatCard";
import ComputerFilters from "../components/ComputerFilters";
import ComputerTable from "../components/ComputerTable";
import Pagination from "../components/Pagination";
import ViewComputerModal from "../components/ViewComputerModal";
import EditComputerModal from "../components/EditComputerModal";

/* =====================================================
   BASE COMPUTER DATA
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
      256,
      120,
      300,
      180,
      80,
      200,
      40,
      150,
      280,
      110,
      350,
      90,
      220,
      130,
      410,
      70,
      260,
      140,
      380,
      60,
      290,
      125,
      320,
      55,
    ][i],

    total,

    last: n <= 16 ? "21 May 2025" : "20 May 2025",

    time: "10:15 AM",

    status: off ? "Offline" : "Online",

    lab: n <= 12 ? "Lab 1" : "Lab 2",
  };
});

/* =====================================================
   COMPONENT
===================================================== */

function ComputerList() {
  const [computers, setComputers] = useState(() => {
    try {
      return (
        JSON.parse(
          localStorage.getItem("slms_computers")
        ) || base
      );
    } catch {
      return base;
    }
  });

  /* SAVE TO LOCAL STORAGE */

  useEffect(() => {
    localStorage.setItem(
      "slms_computers",
      JSON.stringify(computers)
    );
  }, [computers]);

  /* FILTERS */

  const [search, setSearch] = useState("");

  const [status, setStatus] =
    useState("All Status");

  const [os, setOs] =
    useState("All OS");

  const [lab, setLab] =
    useState("All Labs");

  const [sortBy, setSortBy] =
    useState("Sort by: Name (A-Z)");

  const [page, setPage] = useState(1);

  /* MODALS */

  const [view, setView] = useState(null);

  const [edit, setEdit] = useState(null);

  /* FILTER DROPDOWN */

  const [filterOpen, setFilterOpen] =
    useState(false);

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
      (status === "All Status" ||
        x.status === status) &&
      (os === "All OS" ||
        x.os.includes(os)) &&
      (lab === "All Labs" ||
        x.lab === lab)
    );
  });

  /* =====================================================
     SORT
  ===================================================== */

  const sortMap = {
    "Sort by: Name (A-Z)": (a, b) =>
      a.name.localeCompare(b.name),

    "Sort by: Name (Z-A)": (a, b) =>
      b.name.localeCompare(a.name),

    "Sort by: IP Address (A-Z)": (a, b) =>
      a.ip.localeCompare(
        b.ip,
        undefined,
        { numeric: true }
      ),

    "Sort by: IP Address (Z-A)": (a, b) =>
      b.ip.localeCompare(
        a.ip,
        undefined,
        { numeric: true }
      ),

    "Sort by: Status": (a, b) =>
      a.status.localeCompare(b.status),
  };

  filtered = [...filtered].sort(
    sortMap[sortBy] || (() => 0)
  );

  /* PAGINATION */

  const pages = Math.max(
    1,
    Math.ceil(filtered.length / per)
  );

  const rows = filtered.slice(
    (page - 1) * per,
    page * per
  );

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

    setSortBy(
      "Sort by: Name (A-Z)"
    );

    setPage(1);
  };

  /* =====================================================
     DELETE
  ===================================================== */

  const del = (id) => {
    const computer = computers.find(
      (c) => c.id === id
    );

    if (
      computer &&
      window.confirm(
        `Are you sure you want to delete ${computer.name}?`
      )
    ) {
      setComputers((previous) =>
        previous.filter(
          (c) => c.id !== id
        )
      );
    }
  };

  /* =====================================================
     SAVE EDIT
  ===================================================== */

  const save = (computer) => {
    setComputers((previous) =>
      previous.map((c) =>
        c.id === computer.id
          ? computer
          : c
      )
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

    const a =
      document.createElement("a");

    a.href = URL.createObjectURL(
      new Blob([csv], {
        type: "text/csv",
      })
    );

    a.download =
      "SLMS-Computer-List.csv";

    a.click();
  };

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

            <p>
              View and manage all lab computers.
            </p>
          </div>

          <div className="top-actions">

            <button
              className="export"
              onClick={exportCSV}
            >
              <Icon
                type="upload"
                size={18}
              />
              Export
            </button>

            <button
              className="refresh"
              onClick={reset}
            >
              <Icon
                type="refresh"
                size={18}
              />
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
            number={computers.length}
            footer="All computers in lab"
            type="blue"
          />

          <StatCard
            icon="computer"
            title="Online"
            number={
              computers.filter(
                (x) =>
                  x.status === "Online"
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
                (x) =>
                  x.status === "Offline"
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

        {/* TABLE */}

        <div className="table-card">

          <div className="filters">

            <div className="table-search">

              <input
                value={search}
                onChange={(e) =>
                  setSearch(
                    e.target.value
                  )
                }
                placeholder="Search by computer name, IP..."
              />

              <Icon
                type="search"
                size={18}
              />

            </div>

            <select
              value={os}
              onChange={(e) =>
                setOs(e.target.value)
              }
            >
              <option>
                All OS
              </option>

              <option>
                Windows 11
              </option>

              <option>
                Windows 10
              </option>

              <option>
                Windows 7
              </option>
            </select>

            <select
              value={status}
              onChange={(e) =>
                setStatus(e.target.value)
              }
            >
              <option>
                All Status
              </option>

              <option>
                Online
              </option>

              <option>
                Offline
              </option>
            </select>

            <select
              value={lab}
              onChange={(e) =>
                setLab(e.target.value)
              }
            >
              <option>
                All Labs
              </option>

              <option>
                Lab 1
              </option>

              <option>
                Lab 2
              </option>
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

      {/* VIEW MODAL */}

      {view && (
        <ViewComputerModal
          computer={view}
          onClose={() =>
            setView(null)
          }
        />
      )}

      {/* EDIT MODAL */}

      {edit && (
        <EditComputerModal
          computer={edit}
          onClose={() =>
            setEdit(null)
          }
          onSave={save}
        />
      )}
    </>
  );
}

export default ComputerList;