import { useCallback, useEffect, useMemo, useState } from "react";
import {
  downloadReportCSV,
  getAuditReport,
  getCommandReport,
  getInventoryReport,
  getIssueReport,
  getMaintenanceReport,
  getReportOverview,
  getSoftwareReport,
  getUsageReport,
  getUtilizationReport,
} from "../../../services/reportService";
import { getComputers } from "../../../services/computerService";

export function useReportsDashboard() {
  const [category, setCategory] = useState("inventory");
  const [period, setPeriod] = useState("24h");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [computerId, setComputerId] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [maintenanceTypeFilter, setMaintenanceTypeFilter] = useState("");
  const [commandTypeFilter, setCommandTypeFilter] = useState("");
  const [page, setPage] = useState(1);
  const [limit] = useState(25);

  // Data states
  const [overview, setOverview] = useState(null);
  const [computersList, setComputersList] = useState([]);
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [lastRefreshedAt, setLastRefreshedAt] = useState(new Date());

  // Load computers dropdown list
  useEffect(() => {
    let active = true;
    async function fetchComputers() {
      try {
        const data = await getComputers();
        if (active && Array.isArray(data)) {
          setComputersList(data);
        }
      } catch {
        // Fallback silently if unavailable
      }
    }
    fetchComputers();
    return () => {
      active = false;
    };
  }, []);

  // Load global overview stats
  const fetchOverview = useCallback(async () => {
    try {
      const data = await getReportOverview();
      setOverview(data);
    } catch {
      // Ignored for unprivileged users
    }
  }, []);

  useEffect(() => {
    let isSubscribed = true;
    async function load() {
      try {
        const data = await getReportOverview();
        if (isSubscribed) setOverview(data);
      } catch {
        // Ignored
      }
    }
    load();
    return () => {
      isSubscribed = false;
    };
  }, []);

  // Main report data loader (for manual refreshes / button clicks)
  const loadReportData = useCallback(async () => {
    setLoading(true);
    setError("");
    setSuccessMsg("");
    try {
      const compIdNum = computerId ? Number(computerId) : undefined;
      const customFrom = period === "custom" && dateFrom ? dateFrom : undefined;
      const customTo = period === "custom" && dateTo ? dateTo : undefined;

      let result = null;

      switch (category) {
        case "inventory":
          result = await getInventoryReport({
            computer_id: compIdNum,
            status: statusFilter || undefined,
            search: search || undefined,
            page,
            limit,
          });
          break;

        case "utilization":
          result = await getUtilizationReport({
            period,
            from_date: customFrom,
            to_date: customTo,
            computer_id: compIdNum,
          });
          break;

        case "software":
          result = await getSoftwareReport({
            computer_id: compIdNum,
            search: search || undefined,
            page,
            limit,
          });
          break;

        case "issues":
          result = await getIssueReport({
            computer_id: compIdNum,
            severity: severityFilter || undefined,
            status: statusFilter || undefined,
            from_date: customFrom,
            to_date: customTo,
            page,
            limit,
          });
          break;

        case "maintenance":
          result = await getMaintenanceReport({
            computer_id: compIdNum,
            status: statusFilter || undefined,
            maintenance_type: maintenanceTypeFilter || undefined,
            from_date: customFrom,
            to_date: customTo,
            page,
            limit,
          });
          break;

        case "usage":
          result = await getUsageReport({
            computer_id: compIdNum,
            search: search || undefined,
            from_date: customFrom,
            to_date: customTo,
            page,
            limit,
          });
          break;

        case "commands":
          result = await getCommandReport({
            computer_id: compIdNum,
            command_type: commandTypeFilter || undefined,
            status: statusFilter || undefined,
            from_date: customFrom,
            to_date: customTo,
            page,
            limit,
          });
          break;

        case "audit":
          result = await getAuditReport({
            action: search || undefined,
            result: statusFilter || undefined,
            from_date: customFrom,
            to_date: customTo,
            page,
            limit,
          });
          break;

        default:
          result = null;
      }

      setReportData(result);
      setLastRefreshedAt(new Date());
    } catch (err) {
      setError(err.message || "Failed to load report data from server");
      setReportData(null);
    } finally {
      setLoading(false);
    }
  }, [
    category,
    period,
    dateFrom,
    dateTo,
    computerId,
    search,
    statusFilter,
    severityFilter,
    maintenanceTypeFilter,
    commandTypeFilter,
    page,
    limit,
  ]);

  // Synchronize effect with query parameters without synchronous setState in effect body
  useEffect(() => {
    let isSubscribed = true;
    async function runEffect() {
      try {
        const compIdNum = computerId ? Number(computerId) : undefined;
        const customFrom = period === "custom" && dateFrom ? dateFrom : undefined;
        const customTo = period === "custom" && dateTo ? dateTo : undefined;

        let result = null;

        switch (category) {
          case "inventory":
            result = await getInventoryReport({
              computer_id: compIdNum,
              status: statusFilter || undefined,
              search: search || undefined,
              page,
              limit,
            });
            break;

          case "utilization":
            result = await getUtilizationReport({
              period,
              from_date: customFrom,
              to_date: customTo,
              computer_id: compIdNum,
            });
            break;

          case "software":
            result = await getSoftwareReport({
              computer_id: compIdNum,
              search: search || undefined,
              page,
              limit,
            });
            break;

          case "issues":
            result = await getIssueReport({
              computer_id: compIdNum,
              severity: severityFilter || undefined,
              status: statusFilter || undefined,
              from_date: customFrom,
              to_date: customTo,
              page,
              limit,
            });
            break;

          case "maintenance":
            result = await getMaintenanceReport({
              computer_id: compIdNum,
              status: statusFilter || undefined,
              maintenance_type: maintenanceTypeFilter || undefined,
              from_date: customFrom,
              to_date: customTo,
              page,
              limit,
            });
            break;

          case "usage":
            result = await getUsageReport({
              computer_id: compIdNum,
              search: search || undefined,
              from_date: customFrom,
              to_date: customTo,
              page,
              limit,
            });
            break;

          case "commands":
            result = await getCommandReport({
              computer_id: compIdNum,
              command_type: commandTypeFilter || undefined,
              status: statusFilter || undefined,
              from_date: customFrom,
              to_date: customTo,
              page,
              limit,
            });
            break;

          case "audit":
            result = await getAuditReport({
              action: search || undefined,
              result: statusFilter || undefined,
              from_date: customFrom,
              to_date: customTo,
              page,
              limit,
            });
            break;

          default:
            result = null;
        }

        if (!isSubscribed) return;
        setReportData(result);
        setLastRefreshedAt(new Date());
        setError("");
      } catch (err) {
        if (!isSubscribed) return;
        setError(err.message || "Failed to load report data from server");
        setReportData(null);
      } finally {
        if (isSubscribed) setLoading(false);
      }
    }

    runEffect();
    return () => {
      isSubscribed = false;
    };
  }, [
    category,
    period,
    dateFrom,
    dateTo,
    computerId,
    search,
    statusFilter,
    severityFilter,
    maintenanceTypeFilter,
    commandTypeFilter,
    page,
    limit,
  ]);

  // Handle switching category
  const handleSelectCategory = (newCategory) => {
    if (newCategory === category) return;
    setCategory(newCategory);
    setPage(1);
    setSearch("");
    setStatusFilter("");
    setSeverityFilter("");
    setMaintenanceTypeFilter("");
    setCommandTypeFilter("");
  };

  // Reset filters
  const resetFilters = () => {
    setPeriod("24h");
    setDateFrom("");
    setDateTo("");
    setComputerId("");
    setSearch("");
    setStatusFilter("");
    setSeverityFilter("");
    setMaintenanceTypeFilter("");
    setCommandTypeFilter("");
    setPage(1);
  };

  // Export CSV
  const handleExportCSV = async () => {
    setExporting(true);
    setError("");
    setSuccessMsg("");
    try {
      const compIdNum = computerId ? Number(computerId) : undefined;
      const customFrom = period === "custom" && dateFrom ? dateFrom : undefined;
      const customTo = period === "custom" && dateTo ? dateTo : undefined;

      const filename = await downloadReportCSV(category, {
        period,
        from_date: customFrom,
        to_date: customTo,
        computer_id: compIdNum,
        search: search || undefined,
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
        maintenance_type: maintenanceTypeFilter || undefined,
        command_type: commandTypeFilter || undefined,
      });

      setSuccessMsg(`Successfully exported ${filename}`);
      setTimeout(() => setSuccessMsg(""), 4000);
    } catch (err) {
      setError(err.message || "Failed to generate CSV export");
    } finally {
      setExporting(false);
    }
  };

  // Count active filters
  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (period !== "24h") count++;
    if (computerId) count++;
    if (search) count++;
    if (statusFilter) count++;
    if (severityFilter) count++;
    if (maintenanceTypeFilter) count++;
    if (commandTypeFilter) count++;
    return count;
  }, [
    period,
    computerId,
    search,
    statusFilter,
    severityFilter,
    maintenanceTypeFilter,
    commandTypeFilter,
  ]);

  return {
    category,
    handleSelectCategory,
    // Filters
    period,
    setPeriod,
    dateFrom,
    setDateFrom,
    dateTo,
    setDateTo,
    computerId,
    setComputerId,
    search,
    setSearch,
    statusFilter,
    setStatusFilter,
    severityFilter,
    setSeverityFilter,
    maintenanceTypeFilter,
    setMaintenanceTypeFilter,
    commandTypeFilter,
    setCommandTypeFilter,
    page,
    setPage,
    limit,
    resetFilters,
    activeFiltersCount,
    // Data & UI states
    overview,
    computersList,
    reportData,
    loading,
    exporting,
    error,
    successMsg,
    lastRefreshedAt,
    // Actions
    refresh: () => {
      fetchOverview();
      loadReportData();
    },
    handleExportCSV,
  };
}
