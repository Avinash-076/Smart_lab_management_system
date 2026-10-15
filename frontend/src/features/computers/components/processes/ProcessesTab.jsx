import { useState, useEffect, useCallback, useTransition } from "react";
import ProcessFilters from "./ProcessFilters";
import ProcessStatusDistribution from "./ProcessStatusDistribution";
import TopProcessesByCPU from "./TopProcessesByCPU";
import RunningProcessesTable from "./RunningProcessesTable";
import {
  getComputerProcesses,
  getComputerProcessesSummary,
  exportProcessesToCsv,
} from "../../../../services/processService";
import "./ProcessesTab.css";

export default function ProcessesTab({
  computerId,
  computer = null,
  onSummaryUpdate = null,
}) {
  const [, startTransition] = useTransition();

  // Filters state
  const [filters, setFilters] = useState({
    search: "",
    status: "",
    cpu_usage: "",
    memory_usage: "",
    user: "",
  });

  // Sorting & Pagination state
  const [sortConfig, setSortConfig] = useState({
    key: "cpu_percent",
    direction: "desc",
  });
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Data state
  const [processList, setProcessList] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [summaryData, setSummaryData] = useState(null);

  // Status state
  const [loadingList, setLoadingList] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  // Parse numeric filter thresholds
  const cpuMin =
    filters.cpu_usage && filters.cpu_usage !== "all"
      ? parseFloat(filters.cpu_usage)
      : undefined;
  const memoryMinMb =
    filters.memory_usage && filters.memory_usage !== "all"
      ? parseFloat(filters.memory_usage)
      : undefined;

  // Load summary analytics
  const loadSummary = useCallback(async () => {
    if (!computerId) return;
    try {
      setLoadingSummary(true);
      const summary = await getComputerProcessesSummary(computerId, {
        search: filters.search,
        status: filters.status,
        cpu_min: cpuMin,
        memory_min_mb: memoryMinMb,
        user: filters.user,
      });

      setSummaryData(summary);
      if (onSummaryUpdate) {
        onSummaryUpdate(summary);
      }
    } catch (err) {
      console.warn("Could not load process summary:", err);
    } finally {
      setLoadingSummary(false);
    }
  }, [computerId, filters, cpuMin, memoryMinMb, onSummaryUpdate]);

  // Load paginated processes list
  const loadProcessTable = useCallback(async () => {
    if (!computerId) return;
    try {
      setLoadingList(true);
      setError("");

      const res = await getComputerProcesses(computerId, {
        search: filters.search,
        status: filters.status,
        cpu_min: cpuMin,
        memory_min_mb: memoryMinMb,
        user: filters.user,
        sort_by: sortConfig.key,
        sort_order: sortConfig.direction,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      });

      startTransition(() => {
        setProcessList(res.data || []);
        setTotalCount((prev) => {
          if (typeof res.totalCount === "number" && res.totalCount >= 0) {
            return res.totalCount;
          }
          return prev || (res.data?.length || 0);
        });
      });
    } catch (err) {
      console.error("Failed to load process inventory:", err);
      setError(err.message || "Failed to load process records.");
      setProcessList([]);
      setTotalCount(0);
    } finally {
      setLoadingList(false);
    }
  }, [computerId, filters, cpuMin, memoryMinMb, sortConfig, page]);

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
        loadProcessTable();
      }
    });
    return () => {
      ignore = true;
    };
  }, [loadProcessTable]);

  // Handle filter submission
  const handleApplyFilters = (newFilters) => {
    setFilters(newFilters);
    setPage(1); // reset to first page
  };

  // Handle sorting change
  const handleSortChange = (newSort) => {
    setSortConfig(newSort);
    setPage(1);
  };

  // Handle CSV export
  const handleExportCsv = async () => {
    if (!computerId) return;
    try {
      setExporting(true);
      // Fetch up to 2000 matching items
      const res = await getComputerProcesses(computerId, {
        search: filters.search,
        status: filters.status,
        cpu_min: cpuMin,
        memory_min_mb: memoryMinMb,
        user: filters.user,
        sort_by: sortConfig.key,
        sort_order: sortConfig.direction,
        limit: 2000,
        offset: 0,
      });

      const items = res.data || processList;
      exportProcessesToCsv(items, computer?.hostname || `computer_${computerId}`);
    } catch (err) {
      console.error("Failed to export processes CSV:", err);
      exportProcessesToCsv(processList, computer?.hostname || `computer_${computerId}`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="processes-tab-container">
      {/* 1. Filter Toolbar */}
      <ProcessFilters
        filters={filters}
        availableUsers={summaryData?.users || []}
        availableStatuses={summaryData?.statuses || []}
        onApply={handleApplyFilters}
        onExport={handleExportCsv}
        loading={loadingList || exporting}
      />

      {/* 2. Analytics Row (2 Cards: Status Donut + Top CPU Bars) */}
      <div className="processes-analytics-grid">
        <ProcessStatusDistribution
          distribution={summaryData?.status_distribution || []}
          totalProcesses={summaryData?.total_running || totalCount}
          loading={loadingSummary}
        />

        <TopProcessesByCPU
          processes={summaryData?.top_cpu_processes || []}
          totalCpuPercent={summaryData?.total_cpu_percent || 0}
          loading={loadingSummary}
        />
      </div>

      {/* 3. Full-width Running Processes Table */}
      <RunningProcessesTable
        processes={processList}
        totalCount={totalCount}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        sortConfig={sortConfig}
        onSortChange={handleSortChange}
        loading={loadingList}
        error={error}
      />
    </div>
  );
}
