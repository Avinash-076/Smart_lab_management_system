import { useState, useEffect, useCallback, useRef } from "react";
import HistoryFilters from "./HistoryFilters";
import ApplicationUsageTrend from "./ApplicationUsageTrend";
import TopApplicationsChart from "./TopApplicationsChart";
import ApplicationUsageTable from "./ApplicationUsageTable";
import {
  getComputerUsage,
  getComputerUsageSummary,
} from "../../../../services/computerService";
import "./HistoryTab.css";

function computeTimeBounds(preset, customStart, customEnd) {
  const now = new Date();
  let startTime = undefined;
  let endTime = undefined;

  if (preset === "today") {
    // Start of today in local time converted to UTC ISO
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    startTime = startOfToday.toISOString();
  } else if (preset === "yesterday") {
    const startOfYesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1, 0, 0, 0);
    const endOfYesterday = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 0, 0, 0);
    startTime = startOfYesterday.toISOString();
    endTime = endOfYesterday.toISOString();
  } else if (preset === "7d") {
    startTime = new Date(now.getTime() - 7 * 86400000).toISOString();
  } else if (preset === "30d") {
    startTime = new Date(now.getTime() - 30 * 86400000).toISOString();
  } else if (preset === "all") {
    startTime = undefined;
    endTime = undefined;
  } else if (preset === "custom") {
    if (customStart) {
      startTime = new Date(customStart + "T00:00:00").toISOString();
    }
    if (customEnd) {
      endTime = new Date(customEnd + "T23:59:59").toISOString();
    }
  }
  return { startTime, endTime };
}

function formatDurationForCsv(seconds) {
  if (typeof seconds !== "number" || seconds <= 0) return "0s";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${secs}s`;
}

function HistoryTab({ computerId }) {
  // Filter Inputs state
  const [timeRange, setTimeRange] = useState("today");
  const [selectedUser, setSelectedUser] = useState("all");
  const [selectedApp, setSelectedApp] = useState("all");
  const [customStart, setCustomStart] = useState("");
  const [customEnd, setCustomEnd] = useState("");

  // Applied Filter values (applied on click "Apply")
  const [appliedFilters, setAppliedFilters] = useState({
    timeRange: "today",
    selectedUser: "all",
    selectedApp: "all",
    customStart: "",
    customEnd: "",
  });

  // Table pagination state
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Data states
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");

  const [sessions, setSessions] = useState([]);
  const [totalSessionsCount, setTotalSessionsCount] = useState(0);
  const [tableLoading, setTableLoading] = useState(false);
  const [tableError, setTableError] = useState("");

  const [isExporting, setIsExporting] = useState(false);
  const isMountedRef = useRef(true);

  // Load Summary (Trend & Top Apps)
  const loadSummaryData = useCallback(
    async (filters) => {
      if (!computerId) return;
      try {
        setSummaryLoading(true);
        setSummaryError("");
        const { startTime, endTime } = computeTimeBounds(
          filters.timeRange,
          filters.customStart,
          filters.customEnd
        );

        const options = {
          start_time: startTime,
          end_time: endTime,
        };
        if (filters.selectedUser !== "all") {
          options.user = filters.selectedUser;
        }
        if (filters.selectedApp !== "all") {
          options.application = filters.selectedApp;
        }

        const data = await getComputerUsageSummary(computerId, options);
        if (isMountedRef.current) {
          setSummary(data);
        }
      } catch (err) {
        console.warn("Could not load usage summary:", err);
        if (isMountedRef.current) {
          setSummaryError(err.message || "Failed to load usage summary.");
          setSummary(null);
        }
      } finally {
        if (isMountedRef.current) {
          setSummaryLoading(false);
        }
      }
    },
    [computerId]
  );

  // Load Table Sessions
  const loadTableData = useCallback(
    async (filters, currentPage) => {
      if (!computerId) return;
      try {
        setTableLoading(true);
        setTableError("");
        const { startTime, endTime } = computeTimeBounds(
          filters.timeRange,
          filters.customStart,
          filters.customEnd
        );

        const options = {
          limit: pageSize,
          offset: (currentPage - 1) * pageSize,
          start_time: startTime,
          end_time: endTime,
          includeHeaders: true,
        };
        if (filters.selectedUser !== "all") {
          options.user = filters.selectedUser;
        }
        if (filters.selectedApp !== "all") {
          options.application = filters.selectedApp;
        }

        const response = await getComputerUsage(computerId, options);
        let list = [];
        let totalCount = 0;

        if (response && response.data && Array.isArray(response.data)) {
          list = response.data;
          const headerTotal = response.headers?.get?.("x-total-count");
          totalCount = headerTotal ? parseInt(headerTotal, 10) : list.length;
        } else if (Array.isArray(response)) {
          list = response;
          totalCount = list.length;
        }

        if (isMountedRef.current) {
          setSessions(list);
          setTotalSessionsCount(totalCount);
        }
      } catch (err) {
        console.warn("Could not load usage sessions:", err);
        if (isMountedRef.current) {
          setTableError(err.message || "Failed to load usage history.");
          setSessions([]);
          setTotalSessionsCount(0);
        }
      } finally {
        if (isMountedRef.current) {
          setTableLoading(false);
        }
      }
    },
    [computerId, pageSize]
  );

  // Initial load on mount or computerId change
  useEffect(() => {
    isMountedRef.current = true;
    let ignore = false;

    const timer = setTimeout(() => {
      if (!ignore) {
        loadSummaryData(appliedFilters);
        loadTableData(appliedFilters, 1);
      }
    }, 0);

    return () => {
      ignore = true;
      clearTimeout(timer);
      isMountedRef.current = false;
    };
  }, [computerId, appliedFilters, loadSummaryData, loadTableData]);

  // Handle Apply button click
  const handleApplyFilters = () => {
    const newFilters = {
      timeRange,
      selectedUser,
      selectedApp,
      customStart,
      customEnd,
    };
    setAppliedFilters(newFilters);
    setPage(1);
    loadSummaryData(newFilters);
    loadTableData(newFilters, 1);
  };

  // Handle Page Change
  const handlePageChange = (newPage) => {
    setPage(newPage);
    loadTableData(appliedFilters, newPage);
  };

  // Handle CSV Export
  const handleExport = async () => {
    if (!computerId) return;
    try {
      setIsExporting(true);
      const { startTime, endTime } = computeTimeBounds(
        appliedFilters.timeRange,
        appliedFilters.customStart,
        appliedFilters.customEnd
      );

      const options = {
        limit: 1000,
        offset: 0,
        start_time: startTime,
        end_time: endTime,
      };
      if (appliedFilters.selectedUser !== "all") {
        options.user = appliedFilters.selectedUser;
      }
      if (appliedFilters.selectedApp !== "all") {
        options.application = appliedFilters.selectedApp;
      }

      const res = await getComputerUsage(computerId, options);
      const exportList = Array.isArray(res) ? res : res?.data || [];

      if (exportList.length === 0) {
        alert("No usage records found to export for the selected filter.");
        return;
      }

      // Build CSV
      const headers = [
        "Row",
        "Application Name",
        "Process Name",
        "User",
        "Start Time",
        "End Time",
        "Duration Seconds",
        "Duration Formatted",
      ];

      const csvRows = [headers.join(",")];

      exportList.forEach((item, idx) => {
        const row = [
          idx + 1,
          `"${(item.application_name || "").replace(/"/g, '""')}"`,
          `"${(item.process_name || item.application_name || "").replace(/"/g, '""')}"`,
          `"${(item.user || "").replace(/"/g, '""')}"`,
          `"${item.start_time || ""}"`,
          `"${item.end_time || "Active"}"`,
          item.duration_seconds || 0,
          `"${formatDurationForCsv(item.duration_seconds)}"`,
        ];
        csvRows.push(row.join(","));
      });

      const blob = new Blob([csvRows.join("\n")], {
        type: "text/csv;charset=utf-8;",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const timestamp = new Date().toISOString().slice(0, 10);
      link.setAttribute("href", url);
      link.setAttribute(
        "download",
        `computer_${computerId}_usage_history_${timestamp}.csv`
      );
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
      alert("Failed to export usage history: " + (err.message || "Unknown error"));
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="history-tab-container">
      {/* 1. Filter Toolbar */}
      <HistoryFilters
        timeRange={timeRange}
        setTimeRange={setTimeRange}
        selectedUser={selectedUser}
        setSelectedUser={setSelectedUser}
        selectedApp={selectedApp}
        setSelectedApp={setSelectedApp}
        customStart={customStart}
        setCustomStart={setCustomStart}
        customEnd={customEnd}
        setCustomEnd={setCustomEnd}
        availableUsers={summary?.available_users || []}
        availableApps={summary?.available_applications || []}
        onApply={handleApplyFilters}
        onExport={handleExport}
        isExporting={isExporting}
        isLoading={summaryLoading || tableLoading}
      />

      {/* 2. Side-by-side Cards: Trend Chart & Top Apps Donut */}
      <div className="history-charts-row">
        <ApplicationUsageTrend
          intervals={summary?.trend_intervals || []}
          totalActiveFormatted={summary?.formatted_total_active || "0m"}
          isLoading={summaryLoading}
          error={summaryError}
        />

        <TopApplicationsChart
          topApps={summary?.top_applications || []}
          totalActiveFormatted={summary?.formatted_total_active || "0m"}
          totalActiveSeconds={summary?.total_active_seconds || 0}
          isLoading={summaryLoading}
          error={summaryError}
        />
      </div>

      {/* 3. Full-width Application Usage History Table */}
      <ApplicationUsageTable
        sessions={sessions}
        totalEntries={totalSessionsCount}
        page={page}
        pageSize={pageSize}
        onPageChange={handlePageChange}
        isLoading={tableLoading}
        error={tableError}
      />
    </div>
  );
}

export default HistoryTab;
