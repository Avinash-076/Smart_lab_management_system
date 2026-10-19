import { useState, useEffect, useCallback, useMemo } from "react";
import {
  getAuditLogs,
  getAuditLogDetails,
  getAuditStats,
  downloadAuditLogsCSV,
} from "../../../services/auditService";

export function useAuditLogs() {
  const [logs, setLogs] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(25);

  const [stats, setStats] = useState({
    total: 0,
    success: 0,
    failure: 0,
    commands: 0,
    last_24h: 0,
  });

  const [loading, setLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState(new Date());

  // Filter States
  const [search, setSearch] = useState("");
  const [resultFilter, setResultFilter] = useState("");
  const [targetTypeFilter, setTargetTypeFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");

  // Detail Modal
  const [selectedLog, setSelectedLog] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (search.trim()) count++;
    if (resultFilter) count++;
    if (targetTypeFilter) count++;
    if (dateFrom) count++;
    if (dateTo) count++;
    return count;
  }, [search, resultFilter, targetTypeFilter, dateFrom, dateTo]);

  // Synchronize effect with query parameters without synchronous setState in effect body
  useEffect(() => {
    let isSubscribed = true;

    async function syncLogs() {
      try {
        const params = {
          page,
          limit,
        };
        if (search.trim()) params.search = search.trim();
        if (resultFilter) params.result = resultFilter;
        if (targetTypeFilter) params.target_type = targetTypeFilter;
        if (dateFrom) params.date_from = dateFrom;
        if (dateTo) params.date_to = dateTo;

        const data = await getAuditLogs(params);
        if (!isSubscribed) return;
        setLogs(data.items || []);
        setTotalCount(data.total || 0);
        setTotalPages(data.total_pages || 1);
        setLastRefreshedAt(new Date());
        setLoading(false);
      } catch (err) {
        if (!isSubscribed) return;
        setError(err.message || "Failed to load audit logs");
        setLoading(false);
      }
    }

    syncLogs();

    return () => {
      isSubscribed = false;
    };
  }, [page, limit, search, resultFilter, targetTypeFilter, dateFrom, dateTo]);

  // Initial mount: load stats once
  useEffect(() => {
    let isSubscribed = true;

    async function initStats() {
      try {
        const data = await getAuditStats();
        if (!isSubscribed) return;
        if (data && typeof data === "object") {
          setStats({
            total: data.total || 0,
            success: data.success || 0,
            failure: data.failure || 0,
            commands: data.commands || 0,
            last_24h: data.last_24h || 0,
          });
        }
        setStatsLoading(false);
      } catch (err) {
        if (!isSubscribed) return;
        console.warn("Could not load audit stats:", err);
        setStatsLoading(false);
      }
    }

    initStats();

    return () => {
      isSubscribed = false;
    };
  }, []);

  // Manual Refresh
  const refresh = useCallback(async () => {
    setLoading(true);
    setStatsLoading(true);
    setError(null);
    try {
      const params = {
        page,
        limit,
      };
      if (search.trim()) params.search = search.trim();
      if (resultFilter) params.result = resultFilter;
      if (targetTypeFilter) params.target_type = targetTypeFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const [logsData, statsData] = await Promise.all([
        getAuditLogs(params),
        getAuditStats(),
      ]);

      setLogs(logsData.items || []);
      setTotalCount(logsData.total || 0);
      setTotalPages(logsData.total_pages || 1);
      if (statsData && typeof statsData === "object") {
        setStats({
          total: statsData.total || 0,
          success: statsData.success || 0,
          failure: statsData.failure || 0,
          commands: statsData.commands || 0,
          last_24h: statsData.last_24h || 0,
        });
      }
      setLastRefreshedAt(new Date());
    } catch (err) {
      setError(err.message || "Failed to refresh audit data");
    } finally {
      setLoading(false);
      setStatsLoading(false);
    }
  }, [page, limit, search, resultFilter, targetTypeFilter, dateFrom, dateTo]);

  // Reset Filters
  const resetFilters = useCallback(() => {
    setSearch("");
    setResultFilter("");
    setTargetTypeFilter("");
    setDateFrom("");
    setDateTo("");
    setPage(1);
  }, []);

  // Export CSV
  const handleExportCSV = useCallback(async () => {
    setExporting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      const params = {};
      if (search.trim()) params.search = search.trim();
      if (resultFilter) params.result = resultFilter;
      if (targetTypeFilter) params.target_type = targetTypeFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const res = await downloadAuditLogsCSV(params);
      setSuccessMsg(`Successfully exported ${res.filename}`);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(err.message || "Failed to export audit logs CSV");
      setTimeout(() => setError(null), 5000);
    } finally {
      setExporting(false);
    }
  }, [search, resultFilter, targetTypeFilter, dateFrom, dateTo]);

  // Detail Modal Handlers
  const handleOpenDetail = useCallback(async (logId) => {
    setDetailLoading(true);
    try {
      const detail = await getAuditLogDetails(logId);
      setSelectedLog(detail);
    } catch (err) {
      setError(err.message || "Failed to load event details");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedLog(null);
  }, []);

  return {
    logs,
    totalCount,
    totalPages,
    page,
    setPage,
    limit,
    setLimit,
    stats,
    statsLoading,
    loading,
    exporting,
    error,
    successMsg,
    lastRefreshedAt,
    // Filters
    search,
    setSearch,
    resultFilter,
    setResultFilter,
    targetTypeFilter,
    setTargetTypeFilter,
    dateFrom,
    setDateFrom,
    dateTo,
    setDateTo,
    activeFiltersCount,
    resetFilters,
    // Actions
    refresh,
    handleExportCSV,
    selectedLog,
    detailLoading,
    handleOpenDetail,
    handleCloseDetail,
  };
}
