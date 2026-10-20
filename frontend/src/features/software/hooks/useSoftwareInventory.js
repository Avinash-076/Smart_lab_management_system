import { useState, useEffect, useCallback, useMemo } from "react";
import { getComputers } from "../../../services/computerService";
import {
  getFleetSoftware,
  getFleetSoftwareSummary,
  getComputerSoftware,
  exportFleetSoftwareToCsv,
} from "../../../services/softwareService";

export function useSoftwareInventory() {
  // Computers
  const [computers, setComputers] = useState([]);

  // Software data
  const [softwareList, setSoftwareList] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [summary, setSummary] = useState(null);

  // Status
  const [loading, setLoading] = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [lastRefreshedAt, setLastRefreshedAt] = useState(null);

  // Filters
  const [search, setSearch] = useState("");
  const [osFilter, setOsFilter] = useState("All OS");
  const [publisherFilter, setPublisherFilter] = useState("All Publishers");
  const [computerFilter, setComputerFilter] = useState("All Computers");
  const [statusFilter, setStatusFilter] = useState("All Status");
  const [tableSearch, setTableSearch] = useState("");

  // Pagination & Sorting
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [sortConfig, setSortConfig] = useState({
    key: "name",
    direction: "asc",
  });

  // View mode
  const [viewMode, setViewMode] = useState("table"); // 'table' | 'cards'

  // Selection
  const [selectedSoftwareIds, setSelectedSoftwareIds] = useState(new Set());

  // Modals
  const [selectedSoftware, setSelectedSoftware] = useState(null);
  const [isExportReportOpen, setIsExportReportOpen] = useState(false);

  // Load computers once
  useEffect(() => {
    let ignore = false;
    async function fetchComputers() {
      try {
        const comps = await getComputers();
        if (!ignore && Array.isArray(comps)) {
          setComputers(comps);
        }
      } catch (err) {
        console.warn("Could not fetch computers:", err);
      }
    }
    fetchComputers();
    return () => {
      ignore = true;
    };
  }, []);

  // Fetch summary metrics
  const loadSummary = useCallback(async () => {
    try {
      setSummaryLoading(true);
      const data = await getFleetSoftwareSummary();
      if (data && typeof data === "object") {
        setSummary(data);
      }
    } catch (err) {
      console.warn("Could not fetch fleet software summary:", err);
      // Fallback summary will be computed from softwareList if needed
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  // Fetch paginated software list
  const loadSoftware = useCallback(async () => {
    try {
      setLoading(true);
      setError("");

      const computerIdParam =
        computerFilter && computerFilter !== "All Computers"
          ? Number(computerFilter)
          : undefined;

      const osNameParam =
        osFilter && osFilter !== "All OS" ? osFilter : undefined;

      const pubParam =
        publisherFilter && publisherFilter !== "All Publishers"
          ? publisherFilter
          : undefined;

      try {
        const res = await getFleetSoftware({
          search: search.trim() || undefined,
          publisher: pubParam,
          computer_id: computerIdParam,
          os_name: osNameParam,
          sort_by: sortConfig.key,
          sort_order: sortConfig.direction,
          limit: pageSize,
          offset: (page - 1) * pageSize,
        });

        if (res && Array.isArray(res.data)) {
          setSoftwareList(res.data);
          setTotalCount(res.totalCount ?? res.data.length);
          setLastRefreshedAt(new Date());
          setLoading(false);
          return;
        }
      } catch (fleetErr) {
        console.warn("Fleet software API failed, trying fallback:", fleetErr);
      }

      // Fallback: If fleet endpoint is not reachable, query per computer
      if (computers.length > 0) {
        const targetCompId = computerIdParam || computers[0]?.id;
        if (targetCompId) {
          const compRes = await getComputerSoftware(targetCompId, {
            search: search.trim() || undefined,
            publisher: pubParam,
            sort_by: sortConfig.key,
            sort_order: sortConfig.direction,
            limit: pageSize,
            offset: (page - 1) * pageSize,
          });

          const items = (compRes.data || []).map((it) => ({
            ...it,
            installed_count: 1,
            total_computers: computers.length || 1,
            os_display: computers.find((c) => c.id === targetCompId)?.os_name || "Windows 10/11",
            computers: [
              {
                id: targetCompId,
                hostname: computers.find((c) => c.id === targetCompId)?.hostname || `PC-${targetCompId}`,
                ip_address: computers.find((c) => c.id === targetCompId)?.ip_address,
                os: computers.find((c) => c.id === targetCompId)?.os_name,
                status: "online",
                install_date: it.install_date,
              },
            ],
          }));

          setSoftwareList(items);
          setTotalCount(compRes.totalCount || items.length);
        }
      } else {
        setSoftwareList([]);
        setTotalCount(0);
      }

      setLastRefreshedAt(new Date());
    } catch (err) {
      console.error("Failed to load software inventory:", err);
      setError(err.message || "Failed to load software inventory records.");
      setSoftwareList([]);
      setTotalCount(0);
    } finally {
      setLoading(false);
    }
  }, [
    search,
    osFilter,
    publisherFilter,
    computerFilter,
    sortConfig,
    page,
    pageSize,
    computers,
  ]);

  // Initial and reactive load
  useEffect(() => {
    let ignore = false;
    Promise.resolve().then(() => {
      if (!ignore) {
        loadSummary();
      }
    });
    return () => {
      ignore = true;
    };
  }, [loadSummary]);

  useEffect(() => {
    let ignore = false;
    Promise.resolve().then(() => {
      if (!ignore) {
        loadSoftware();
      }
    });
    return () => {
      ignore = true;
    };
  }, [loadSoftware]);

  // Filter within loaded results if tableSearch is active
  const displayedSoftware = useMemo(() => {
    if (!tableSearch.trim()) return softwareList;
    const q = tableSearch.toLowerCase().trim();
    return softwareList.filter(
      (item) =>
        (item.name && item.name.toLowerCase().includes(q)) ||
        (item.publisher && item.publisher.toLowerCase().includes(q)) ||
        (item.version && item.version.toLowerCase().includes(q)) ||
        (item.os_display && item.os_display.toLowerCase().includes(q))
    );
  }, [softwareList, tableSearch]);

  // Apply filters button handler
  const handleApplyFilters = () => {
    setPage(1);
    loadSoftware();
  };

  // Reset filters handler
  const handleResetFilters = () => {
    setSearch("");
    setOsFilter("All OS");
    setPublisherFilter("All Publishers");
    setComputerFilter("All Computers");
    setStatusFilter("All Status");
    setTableSearch("");
    setPage(1);
  };

  // Sorting handler
  const handleSortChange = (key) => {
    setSortConfig((prev) => {
      if (prev.key === key) {
        return {
          key,
          direction: prev.direction === "asc" ? "desc" : "asc",
        };
      }
      return { key, direction: "asc" };
    });
    setPage(1);
  };

  // Selection handlers
  const handleToggleSelectAll = () => {
    if (selectedSoftwareIds.size === displayedSoftware.length && displayedSoftware.length > 0) {
      setSelectedSoftwareIds(new Set());
    } else {
      setSelectedSoftwareIds(new Set(displayedSoftware.map((s) => s.id)));
    }
  };

  const handleToggleSelectItem = (id) => {
    setSelectedSoftwareIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleClearSelection = () => {
    setSelectedSoftwareIds(new Set());
  };

  // Export CSV handler
  const handleExportCSV = (selectedOnly = false) => {
    const itemsToExport = selectedOnly
      ? displayedSoftware.filter((s) => selectedSoftwareIds.has(s.id))
      : displayedSoftware;

    if (!itemsToExport.length) return;

    exportFleetSoftwareToCsv(itemsToExport, "software_inventory");
    setSuccessMsg(`Exported ${itemsToExport.length} software records to CSV.`);
    setTimeout(() => setSuccessMsg(""), 4000);
  };

  // Modal handlers
  const handleOpenDetail = (software) => {
    setSelectedSoftware(software);
  };

  const handleCloseDetail = () => {
    setSelectedSoftware(null);
  };

  const handleOpenExportModal = () => {
    setIsExportReportOpen(true);
  };

  const handleCloseExportModal = () => {
    setIsExportReportOpen(false);
  };

  return {
    computers,
    softwareList,
    displayedSoftware,
    totalCount,
    summary,
    loading,
    summaryLoading,
    error,
    successMsg,
    lastRefreshedAt,
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
    tableSearch,
    setTableSearch,
    page,
    setPage,
    pageSize,
    setPageSize,
    sortConfig,
    handleSortChange,
    viewMode,
    setViewMode,
    selectedSoftwareIds,
    handleToggleSelectAll,
    handleToggleSelectItem,
    handleClearSelection,
    selectedSoftware,
    handleOpenDetail,
    handleCloseDetail,
    isExportReportOpen,
    handleOpenExportModal,
    handleCloseExportModal,
    handleApplyFilters,
    handleResetFilters,
    refresh: () => {
      loadSummary();
      loadSoftware();
    },
    handleExportCSV,
  };
}
