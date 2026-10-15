import { useCallback, useEffect, useState, useMemo } from "react";
import {
  getComputers,
  deleteComputer,
  updateComputer,
} from "../../../services/computerService";
import Icon from "../../../components/ui/Icon";
import ComputerSummaryCards from "../components/computer-cards/ComputerSummaryCards";
import ComputerFilters from "../components/computer-list/ComputerFilters";
import ComputerTable from "../components/computer-list/ComputerTable";
import ComputerPagination from "../components/computer-list/ComputerPagination";
import EditComputerModal from "../components/computer-modals/EditComputerModal";
import DeleteConfirmModal from "../components/computer-modals/DeleteConfirmModal";
import AddComputerModal from "../components/computer-modals/AddComputerModal";
import "./ComputersPage.css";

function ComputersPage({ onViewComputer }) {
  /* =====================================================
     DATA FETCHING & REFRESH
  ===================================================== */
  const [computers, setComputers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);

  const loadComputers = useCallback(async (isManualRefresh = false) => {
    try {
      if (isManualRefresh) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError("");
      const data = await getComputers();
      setComputers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load computers:", err);
      setError(err.message || "Failed to load computers from server.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        setError("");
        const data = await getComputers();
        if (!ignore) {
          setComputers(Array.isArray(data) ? data : []);
        }
      } catch (err) {
        if (!ignore) {
          console.error("Failed to load computers:", err);
          setError(err.message || "Failed to load computers.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, []);

  /* =====================================================
     SEARCH, FILTERS, AND SORTING
  ===================================================== */
  const [search, setSearch] = useState("");
  const [os, setOs] = useState("All OS");
  const [status, setStatus] = useState("All Status");
  const [sortBy, setSortBy] = useState("Name (A-Z)");

  // Pagination state
  const [page, setPage] = useState(1);
  const [per, setPer] = useState(8);

  // Row selection state
  const [selectedIds, setSelectedIds] = useState(new Set());

  // Modals state
  const [editComputer, setEditComputer] = useState(null);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);

  /* =====================================================
     FILTERING LOGIC
  ===================================================== */
  const filteredComputers = useMemo(() => {
    const s = search.toLowerCase().trim();

    return computers.filter((item) => {
      const name = (item.hostname || item.name || "").toLowerCase();
      const ip = (item.ip_address || item.ip || "").toLowerCase();
      const mac = (item.mac_address || "").toLowerCase();
      const osStr = (
        item.os_name
          ? `${item.os_name} ${item.os_version || ""}`
          : item.os || ""
      ).toLowerCase();
      const itemStatus = (item.status || "offline").toLowerCase();

      // Search match across computer name, IP address, MAC address
      const matchesSearch =
        !s ||
        name.includes(s) ||
        ip.includes(s) ||
        mac.includes(s) ||
        osStr.includes(s);

      // Status match
      const matchesStatus =
        status === "All Status" || itemStatus === status.toLowerCase();

      // OS match
      let matchesOs = true;
      if (os !== "All OS") {
        if (os === "Windows") {
          matchesOs = osStr.includes("windows");
        } else if (os === "Linux") {
          matchesOs =
            osStr.includes("linux") ||
            osStr.includes("ubuntu") ||
            osStr.includes("debian");
        } else if (os === "macOS") {
          matchesOs =
            osStr.includes("mac") ||
            osStr.includes("darwin") ||
            osStr.includes("apple") ||
            osStr.includes("sonoma");
        } else {
          matchesOs = osStr.includes(os.toLowerCase());
        }
      }

      return matchesSearch && matchesStatus && matchesOs;
    });
  }, [computers, search, os, status]);

  /* =====================================================
     SORTING LOGIC
  ===================================================== */
  const sortedComputers = useMemo(() => {
    const list = [...filteredComputers];

    switch (sortBy) {
      case "Name (A-Z)":
        return list.sort((a, b) =>
          (a.hostname || a.name || "").localeCompare(b.hostname || b.name || "")
        );

      case "Name (Z-A)":
        return list.sort((a, b) =>
          (b.hostname || b.name || "").localeCompare(a.hostname || a.name || "")
        );

      case "IP Address (Asc)":
        return list.sort((a, b) =>
          (a.ip_address || a.ip || "").localeCompare(
            b.ip_address || b.ip || "",
            undefined,
            { numeric: true }
          )
        );

      case "IP Address (Desc)":
        return list.sort((a, b) =>
          (b.ip_address || b.ip || "").localeCompare(
            a.ip_address || a.ip || "",
            undefined,
            { numeric: true }
          )
        );

      case "Status":
        return list.sort((a, b) =>
          (b.status || "").localeCompare(a.status || "")
        );

      case "Last Seen":
        return list.sort((a, b) => {
          const dateA = a.last_seen ? new Date(a.last_seen).getTime() : 0;
          const dateB = b.last_seen ? new Date(b.last_seen).getTime() : 0;
          return dateB - dateA;
        });

      default:
        return list;
    }
  }, [filteredComputers, sortBy]);

  /* =====================================================
     PAGINATION SLICING
  ===================================================== */
  const totalPages = Math.max(1, Math.ceil(sortedComputers.length / per));
  const currentPage = Math.min(page, totalPages);
  const paginatedRows = useMemo(() => {
    const startIndex = (currentPage - 1) * per;
    return sortedComputers.slice(startIndex, startIndex + per);
  }, [sortedComputers, currentPage, per]);

  // Reset page to 1 when filter parameters change
  const filterKey = `${search}|${os}|${status}|${sortBy}|${per}`;
  const [prevFilterKey, setPrevFilterKey] = useState(filterKey);
  if (prevFilterKey !== filterKey) {
    setPrevFilterKey(filterKey);
    setPage(1);
  }

  /* =====================================================
     CLEAR FILTERS
  ===================================================== */
  const handleResetFilters = () => {
    setSearch("");
    setOs("All OS");
    setStatus("All Status");
    setSortBy("Name (A-Z)");
    setPage(1);
  };

  /* =====================================================
     HEADER COLUMN SORT CLICK
  ===================================================== */
  const handleColumnSort = (col) => {
    if (col === "name") {
      setSortBy((prev) => (prev === "Name (A-Z)" ? "Name (Z-A)" : "Name (A-Z)"));
    } else if (col === "ip") {
      setSortBy((prev) =>
        prev === "IP Address (Asc)" ? "IP Address (Desc)" : "IP Address (Asc)"
      );
    } else if (col === "status") {
      setSortBy("Status");
    } else if (col === "last_seen") {
      setSortBy("Last Seen");
    }
  };

  /* =====================================================
     SELECTION LOGIC
  ===================================================== */
  const handleToggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const currentPageIds = useMemo(
    () => paginatedRows.map((r) => r.id),
    [paginatedRows]
  );

  const selectedCurrentPageCount = currentPageIds.filter((id) =>
    selectedIds.has(id)
  ).length;

  const allPageSelected =
    currentPageIds.length > 0 &&
    selectedCurrentPageCount === currentPageIds.length;

  const isIndeterminate =
    selectedCurrentPageCount > 0 &&
    selectedCurrentPageCount < currentPageIds.length;

  const handleToggleSelectAll = (checked) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        currentPageIds.forEach((id) => next.add(id));
      } else {
        currentPageIds.forEach((id) => next.delete(id));
      }
      return next;
    });
  };

  /* =====================================================
     DELETE ACTION
  ===================================================== */
  const handleConfirmDelete = async (id) => {
    try {
      await deleteComputer(id);
      setComputers((prev) => prev.filter((c) => c.id !== id));
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      setDeleteTarget(null);
      setToast({
        type: "success",
        text: "Computer deleted successfully.",
      });
      setTimeout(() => setToast(null), 3500);
    } catch (err) {
      console.error("Failed to delete computer:", err);
      throw err;
    }
  };

  /* =====================================================
     SAVE EDIT ACTION
  ===================================================== */
  const handleSaveEdit = async (updatedComputer) => {
    try {
      // If backend update endpoint is available, sync update
      try {
        await updateComputer(updatedComputer.id, {
          hostname: updatedComputer.hostname,
          ip_address: updatedComputer.ip_address,
          mac_address: updatedComputer.mac_address,
          os_name: updatedComputer.os_name,
          os_version: updatedComputer.os_version || "1.0",
        });
      } catch (apiErr) {
        console.warn("Backend update API notice:", apiErr);
      }

      setComputers((prev) =>
        prev.map((c) => (c.id === updatedComputer.id ? updatedComputer : c))
      );
      setEditComputer(null);
      setToast({
        type: "success",
        text: "Computer details updated successfully.",
      });
      setTimeout(() => setToast(null), 3000);
    } catch (err) {
      console.error("Failed to update computer:", err);
      alert(err.message || "Failed to save changes.");
    }
  };

  /* =====================================================
     EXPORT CSV
  ===================================================== */
  const exportCSV = () => {
    if (sortedComputers.length === 0) return;

    const csvHeaders = [
      "ID",
      "Computer Name",
      "IP Address",
      "MAC Address",
      "Operating System",
      "Status",
      "Last Seen",
      "Registered At",
    ];

    const csvRows = sortedComputers.map((x) => [
      x.id,
      x.hostname || x.name || `PC-${x.id}`,
      x.ip_address || x.ip || "",
      x.mac_address || "",
      x.os_name ? `${x.os_name} ${x.os_version || ""}`.trim() : x.os || "",
      x.status || "offline",
      x.last_seen || "",
      x.registered_at || "",
    ]);

    const csvContent = [
      csvHeaders.join(","),
      ...csvRows.map((row) =>
        row.map((val) => `"${String(val).replace(/"/g, '""')}"`).join(",")
      ),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "SLMS-Computers.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="computers-page" data-testid="computers-page">
      {/* 1. Upper-Right Page Actions */}
      <div className="computers-top-actions">
        <button
          type="button"
          className="computers-action-btn computers-action-btn--secondary"
          onClick={exportCSV}
          disabled={computers.length === 0}
          title="Export computer inventory to CSV"
        >
          <Icon type="export" size={16} />
          Export
        </button>

        <button
          type="button"
          className="computers-action-btn computers-action-btn--primary"
          onClick={() => setShowAddModal(true)}
          title="Provision or register a new lab computer"
        >
          <Icon type="plus" size={16} />
          Add Computer
        </button>

        <button
          type="button"
          className="computers-action-btn computers-action-btn--secondary"
          onClick={() => loadComputers(true)}
          disabled={refreshing || loading}
          title="Refresh computer data from server"
        >
          <span className={refreshing ? "computers-spinning" : ""}>
            <Icon type="refresh" size={16} />
          </span>
          Refresh
        </button>
      </div>

      {/* Optional Feedback Toast */}
      {toast && (
        <div
          className={`computers-toast ${
            toast.type === "success"
              ? "computers-toast--success"
              : "computers-toast--error"
          }`}
          role="status"
        >
          <span>{toast.text}</span>
          <button
            type="button"
            onClick={() => setToast(null)}
            style={{
              background: "none",
              border: "none",
              cursor: "pointer",
              fontSize: "14px",
              color: "inherit",
            }}
          >
            ×
          </button>
        </div>
      )}

      {/* 2. Five Summary Cards */}
      <ComputerSummaryCards computers={computers} />

      {/* 3. Unified Search and Filter Panel */}
      <ComputerFilters
        search={search}
        setSearch={setSearch}
        os={os}
        setOs={setOs}
        status={status}
        setStatus={setStatus}
        sortBy={sortBy}
        setSortBy={setSortBy}
        reset={handleResetFilters}
      />

      {/* 4. Table & Pagination Card */}
      {loading && computers.length === 0 ? (
        /* Loading state */
        <div className="computers-state-card">
          <div className="computers-state-card__icon computers-spinning">
            <Icon type="refresh" size={28} />
          </div>
          <h3 className="computers-state-card__title">Loading computers...</h3>
          <p className="computers-state-card__desc">
            Fetching registered lab computers and telemetry from server.
          </p>
        </div>
      ) : error && computers.length === 0 ? (
        /* Error state */
        <div className="computers-state-card">
          <div
            className="computers-state-card__icon"
            style={{ background: "#fef2f2", color: "#dc2626" }}
          >
            <Icon type="details" size={28} />
          </div>
          <h3 className="computers-state-card__title" style={{ color: "#dc2626" }}>
            Failed to load computers
          </h3>
          <p className="computers-state-card__desc">{error}</p>
          <button
            type="button"
            className="computers-action-btn computers-action-btn--secondary"
            onClick={() => loadComputers(false)}
            style={{ marginTop: "16px" }}
          >
            <Icon type="refresh" size={16} />
            Try Again
          </button>
        </div>
      ) : computers.length === 0 ? (
        /* Empty database state */
        <div className="computers-state-card">
          <div className="computers-state-card__icon">
            <Icon type="computer" size={28} />
          </div>
          <h3 className="computers-state-card__title">No computers registered</h3>
          <p className="computers-state-card__desc">
            There are currently no laboratory computers enrolled in the database.
          </p>
          <button
            type="button"
            className="computers-action-btn computers-action-btn--primary"
            onClick={() => setShowAddModal(true)}
            style={{ marginTop: "16px" }}
          >
            <Icon type="plus" size={16} />
            Add First Computer
          </button>
        </div>
      ) : filteredComputers.length === 0 ? (
        /* No search/filter results */
        <div className="computers-state-card">
          <div className="computers-state-card__icon">
            <Icon type="search" size={28} />
          </div>
          <h3 className="computers-state-card__title">No matching computers</h3>
          <p className="computers-state-card__desc">
            No computers matched your current search and filter criteria.
          </p>
          <button
            type="button"
            className="computers-action-btn computers-action-btn--secondary"
            onClick={handleResetFilters}
            style={{ marginTop: "16px" }}
          >
            <Icon type="clear-filter" size={16} />
            Clear Filters
          </button>
        </div>
      ) : (
        /* Active Table and Pagination */
        <div>
          <ComputerTable
            rows={paginatedRows}
            selectedIds={selectedIds}
            onToggleSelect={handleToggleSelect}
            onToggleSelectAll={handleToggleSelectAll}
            allPageSelected={allPageSelected}
            isIndeterminate={isIndeterminate}
            onSort={handleColumnSort}
            sortBy={sortBy}
            setView={onViewComputer}
            setEdit={setEditComputer}
            del={setDeleteTarget}
          />

          <ComputerPagination
            page={currentPage}
            pages={totalPages}
            setPage={setPage}
            totalRows={sortedComputers.length}
            per={per}
            setPer={setPer}
          />
        </div>
      )}

      {/* Edit Computer Modal */}
      {editComputer && (
        <EditComputerModal
          computer={editComputer}
          onClose={() => setEditComputer(null)}
          onSave={handleSaveEdit}
        />
      )}

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <DeleteConfirmModal
          computer={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onConfirm={handleConfirmDelete}
        />
      )}

      {/* Add Computer Modal */}
      {showAddModal && (
        <AddComputerModal
          onClose={() => setShowAddModal(false)}
          onComputerAdded={() => loadComputers(true)}
        />
      )}
    </div>
  );
}

export default ComputersPage;
