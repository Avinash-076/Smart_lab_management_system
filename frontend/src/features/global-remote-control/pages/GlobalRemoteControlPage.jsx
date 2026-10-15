import { useState, useEffect, useCallback, useMemo } from "react";
import FleetOverview from "../components/FleetOverview/FleetOverview";
import TargetComputerTable from "../components/TargetComputerTable/TargetComputerTable";
import CommandCenter from "../components/CommandCenter/CommandCenter";
import ExecutionMonitor from "../components/ExecutionMonitor/ExecutionMonitor";
import GlobalCommandHistory from "../components/GlobalCommandHistory/GlobalCommandHistory";
import GlobalCommandDetailModal from "../components/GlobalCommandHistory/GlobalCommandDetailModal";
import {
  getFleetOverview,
  issueBatchCommand,
  getGlobalCommands,
  exportGlobalCommandsToCsv,
  getComputers,
} from "../services/globalRemoteService";
import "./GlobalRemoteControlPage.css";

const HISTORY_PAGE_SIZE = 10;
const AUTO_REFRESH_INTERVAL_MS = 10000;

function calculateDateRange(preset) {
  const now = new Date();
  switch (preset) {
    case "today": {
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      return { start_date: today.toISOString() };
    }
    case "last_24_hours": {
      const d = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      return { start_date: d.toISOString() };
    }
    case "last_7_days": {
      const d = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      return { start_date: d.toISOString() };
    }
    case "last_30_days": {
      const d = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      return { start_date: d.toISOString() };
    }
    case "all":
    default:
      return {};
  }
}

export default function GlobalRemoteControlPage({ onViewComputer }) {
  // Fleet metrics
  const [metrics, setMetrics] = useState(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);

  // Computers inventory
  const [computers, setComputers] = useState([]);
  const [loadingComputers, setLoadingComputers] = useState(true);

  // Selected computers (Set of IDs for persistent selection)
  const [selectedComputerIds, setSelectedComputerIds] = useState(new Set());

  // Recent commands for Execution Monitor
  const [recentCommands, setRecentCommands] = useState([]);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Global History state
  const [historyCommands, setHistoryCommands] = useState([]);
  const [historyTotalCount, setHistoryTotalCount] = useState(0);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyFilters, setHistoryFilters] = useState({
    dateRange: "last_7_days",
    commandType: "all",
    status: "all",
    search: "",
  });
  const [loadingHistory, setLoadingHistory] = useState(false);

  // In-flight state
  const [isExecuting, setIsExecuting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  /* -----------------------------------------------------------
   * 1. Fetch Fleet Overview & Recent Commands
   * ----------------------------------------------------------- */
  const fetchOverviewData = useCallback(async () => {
    try {
      const [overviewData, recentData] = await Promise.all([
        getFleetOverview(),
        getGlobalCommands({ limit: 10, offset: 0, includeHeaders: false }),
      ]);
      setMetrics(overviewData);
      setRecentCommands(Array.isArray(recentData) ? recentData : []);
    } catch (err) {
      console.error("Failed to fetch overview or recent commands:", err);
    } finally {
      setLoadingMetrics(false);
    }
  }, []);

  /* -----------------------------------------------------------
   * 2. Fetch Computers Inventory
   * ----------------------------------------------------------- */
  const fetchComputers = useCallback(async () => {
    try {
      setLoadingComputers(true);
      const data = await getComputers();
      setComputers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to fetch computers list:", err);
    } finally {
      setLoadingComputers(false);
    }
  }, []);

  /* -----------------------------------------------------------
   * 3. Fetch History Commands (Server-side paginated & filtered)
   * ----------------------------------------------------------- */
  const fetchHistory = useCallback(async () => {
    try {
      setLoadingHistory(true);
      const dateParams = calculateDateRange(historyFilters.dateRange);
      const options = {
        limit: HISTORY_PAGE_SIZE,
        offset: (historyPage - 1) * HISTORY_PAGE_SIZE,
        includeHeaders: true,
        ...dateParams,
      };

      if (historyFilters.commandType && historyFilters.commandType !== "all") {
        options.command_type = historyFilters.commandType;
      }
      if (historyFilters.status && historyFilters.status !== "all") {
        options.status = historyFilters.status;
      }
      if (historyFilters.search && historyFilters.search.trim()) {
        options.search = historyFilters.search.trim();
      }

      const res = await getGlobalCommands(options);
      setHistoryCommands(res.data || []);
      setHistoryTotalCount(res.totalCount || 0);
    } catch (err) {
      console.error("Failed to fetch history commands:", err);
    } finally {
      setLoadingHistory(false);
    }
  }, [historyPage, historyFilters]);

  // Initial load
  useEffect(() => {
    let isMounted = true;
    const loadInitial = async () => {
      if (isMounted) {
        await Promise.all([fetchOverviewData(), fetchComputers()]);
      }
    };
    loadInitial();
    return () => {
      isMounted = false;
    };
  }, [fetchOverviewData, fetchComputers]);

  useEffect(() => {
    let isMounted = true;
    const loadHistory = async () => {
      if (isMounted) {
        await fetchHistory();
      }
    };
    loadHistory();
    return () => {
      isMounted = false;
    };
  }, [fetchHistory]);

  // Auto-refresh timer for Execution Monitor and Overview metrics
  useEffect(() => {
    if (!autoRefresh) return;

    const timer = setInterval(() => {
      fetchOverviewData();
    }, AUTO_REFRESH_INTERVAL_MS);

    return () => clearInterval(timer);
  }, [autoRefresh, fetchOverviewData]);

  /* -----------------------------------------------------------
   * 4. Target Selection Handlers (Persisted by ID)
   * ----------------------------------------------------------- */
  const handleToggleSelect = useCallback((id) => {
    setSelectedComputerIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleSelectAllVisible = useCallback((ids, shouldSelect) => {
    setSelectedComputerIds((prev) => {
      const next = new Set(prev);
      ids.forEach((id) => {
        if (shouldSelect) {
          next.add(id);
        } else {
          next.delete(id);
        }
      });
      return next;
    });
  }, []);

  const handleClearSelection = useCallback(() => {
    setSelectedComputerIds(new Set());
  }, []);

  // Compute selected computer objects
  const selectedComputers = useMemo(() => {
    return computers.filter((c) => selectedComputerIds.has(c.id));
  }, [computers, selectedComputerIds]);

  /* -----------------------------------------------------------
   * 5. Batch Command Execution
   * ----------------------------------------------------------- */
  const handleExecuteBatch = async (commandType, payload = null) => {
    if (selectedComputerIds.size === 0) {
      throw new Error("No target computers selected.");
    }

    try {
      setIsExecuting(true);
      const batchPayload = {
        computer_ids: Array.from(selectedComputerIds),
        command_type: commandType,
        payload: payload || undefined,
      };

      const result = await issueBatchCommand(batchPayload);

      // Refresh overview, recent monitor, and history immediately
      await Promise.all([fetchOverviewData(), fetchHistory()]);

      return result;
    } finally {
      setIsExecuting(false);
    }
  };

  /* -----------------------------------------------------------
   * 6. CSV Export
   * ----------------------------------------------------------- */
  const handleExportCsv = async () => {
    try {
      setIsExporting(true);
      const dateParams = calculateDateRange(historyFilters.dateRange);
      const options = {
        ...dateParams,
      };
      if (historyFilters.commandType && historyFilters.commandType !== "all") {
        options.command_type = historyFilters.commandType;
      }
      if (historyFilters.status && historyFilters.status !== "all") {
        options.status = historyFilters.status;
      }
      if (historyFilters.search && historyFilters.search.trim()) {
        options.search = historyFilters.search.trim();
      }

      await exportGlobalCommandsToCsv(options);
    } catch (err) {
      console.error("Export to CSV failed:", err);
      alert("Failed to export command history to CSV.");
    } finally {
      setIsExporting(false);
    }
  };

  /* -----------------------------------------------------------
   * 7. Navigation to Computer Details
   * ----------------------------------------------------------- */
  const handleNavigateToComputer = (computerId) => {
    if (onViewComputer) {
      const comp = computers.find((c) => c.id === computerId) || { id: computerId };
      onViewComputer(comp);
    }
  };

  // Inspected command for Detail Modal (can be opened from Monitor or History)
  const [inspectedCommand, setInspectedCommand] = useState(null);

  return (
    <div className="global-remote-page">
      {/* 1. Fleet Overview Metric Cards */}
      <FleetOverview metrics={metrics} loading={loadingMetrics} />

      {/* 2. Target Computer Selection Table */}
      <TargetComputerTable
        computers={computers}
        selectedIds={selectedComputerIds}
        onToggleSelect={handleToggleSelect}
        onSelectAllVisible={handleSelectAllVisible}
        onClearSelection={handleClearSelection}
        loading={loadingComputers}
      />

      {/* 3. Command Center (Action Cards + Selected Targets) */}
      <CommandCenter
        selectedComputers={selectedComputers}
        onClearSelection={handleClearSelection}
        onExecuteBatch={handleExecuteBatch}
        isExecuting={isExecuting}
      />

      {/* 4. Command Execution Monitor */}
      <ExecutionMonitor
        commands={recentCommands}
        loading={loadingMetrics && recentCommands.length === 0}
        autoRefresh={autoRefresh}
        onToggleAutoRefresh={setAutoRefresh}
        onViewDetails={(cmd) => setInspectedCommand(cmd)}
        onNavigateToComputer={handleNavigateToComputer}
      />

      {/* 5. Global Command History */}
      <GlobalCommandHistory
        commands={historyCommands}
        totalCount={historyTotalCount}
        page={historyPage}
        pageSize={HISTORY_PAGE_SIZE}
        onPageChange={setHistoryPage}
        filters={historyFilters}
        onFilterChange={(newFilters) => {
          setHistoryFilters(newFilters);
          setHistoryPage(1);
        }}
        onExportCsv={handleExportCsv}
        loading={loadingHistory}
        isExporting={isExporting}
      />

      {/* Detail Modal opened from Monitor */}
      {inspectedCommand && (
        <GlobalCommandDetailModal
          command={inspectedCommand}
          onClose={() => setInspectedCommand(null)}
        />
      )}
    </div>
  );
}
