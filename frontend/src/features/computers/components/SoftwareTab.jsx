import { useState, useEffect, useCallback, useTransition } from "react";
import SoftwareFilters from "./SoftwareFilters";
import SoftwareTypeDistribution from "./SoftwareTypeDistribution";
import TopSoftwarePublishers from "./TopSoftwarePublishers";
import InstalledSoftwareTable from "./InstalledSoftwareTable";
import {
  getComputerSoftware,
  getComputerSoftwareSummary,
  exportSoftwareToCsv,
} from "../../../services/softwareService";
import "./SoftwareTab.css";

export default function SoftwareTab({
  computerId,
  computer = null,
  onSummaryUpdate = null,
}) {
  const [, startTransition] = useTransition();

  // Filters state
  const [filters, setFilters] = useState({
    search: "",
    publisher: "",
    date_range: "",
    architecture: "",
  });

  // Sorting & Pagination state
  const [sortConfig, setSortConfig] = useState({
    key: "name",
    direction: "asc",
  });
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Data state
  const [softwareList, setSoftwareList] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [summaryData, setSummaryData] = useState(null);

  // Status state
  const [loadingList, setLoadingList] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState("");
  const [exporting, setExporting] = useState(false);

  // Load summary analytics (runs when filters change)
  const loadSummary = useCallback(async () => {
    if (!computerId) return;
    try {
      setLoadingSummary(true);
      const summary = await getComputerSoftwareSummary(computerId, {
        search: filters.search,
        publisher: filters.publisher,
        date_range: filters.date_range,
        architecture: filters.architecture,
      });

      setSummaryData(summary);
      if (onSummaryUpdate) {
        onSummaryUpdate(summary);
      }
    } catch (err) {
      console.warn("Could not load software summary:", err);
    } finally {
      setLoadingSummary(false);
    }
  }, [computerId, filters, onSummaryUpdate]);

  // Load paginated software table list
  const loadSoftwareTable = useCallback(async () => {
    if (!computerId) return;
    try {
      setLoadingList(true);
      setError("");

      const res = await getComputerSoftware(computerId, {
        search: filters.search,
        publisher: filters.publisher,
        date_range: filters.date_range,
        architecture: filters.architecture,
        sort_by: sortConfig.key,
        sort_order: sortConfig.direction,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      });

      startTransition(() => {
        setSoftwareList(res.data || []);
        setTotalCount((prev) => {
          if (typeof res.totalCount === "number" && res.totalCount > 0) {
            return res.totalCount;
          }
          return prev || (res.data?.length || 0);
        });
      });
    } catch (err) {
      console.error("Failed to load software inventory:", err);
      setError(err.message || "Failed to load software records.");
      setSoftwareList([]);
      setTotalCount(0);
    } finally {
      setLoadingList(false);
    }
  }, [computerId, filters, sortConfig, page]);

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
        loadSoftwareTable();
      }
    });
    return () => {
      ignore = true;
    };
  }, [loadSoftwareTable]);

  // Handle filter submission
  const handleApplyFilters = (newFilters) => {
    setFilters(newFilters);
    setPage(1); // reset to first page on new filter
  };

  // Handle table sorting change
  const handleSortChange = (newSort) => {
    setSortConfig(newSort);
    setPage(1);
  };

  // Handle CSV export
  const handleExportCsv = async () => {
    if (!computerId) return;
    try {
      setExporting(true);
      // Fetch full set of matching records up to 2000 items
      const res = await getComputerSoftware(computerId, {
        search: filters.search,
        publisher: filters.publisher,
        date_range: filters.date_range,
        architecture: filters.architecture,
        sort_by: sortConfig.key,
        sort_order: sortConfig.direction,
        limit: 2000,
        offset: 0,
      });

      const items = res.data || softwareList;
      exportSoftwareToCsv(items, computer?.hostname || `computer_${computerId}`);
    } catch (err) {
      console.error("Failed to export software CSV:", err);
      // Fallback export with current page items
      exportSoftwareToCsv(softwareList, computer?.hostname || `computer_${computerId}`);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="software-tab-container">
      {/* 1. Filter Toolbar */}
      <SoftwareFilters
        filters={filters}
        availablePublishers={summaryData?.available_publishers || []}
        availableArchitectures={summaryData?.available_architectures || []}
        onApply={handleApplyFilters}
        onExport={handleExportCsv}
        loading={loadingList || exporting}
      />

      {/* Global Error Banner if any */}
      {error && (
        <div className="software-error-banner">
          <span className="error-icon">⚠</span>
          <span className="error-text">{error}</span>
          <button
            type="button"
            className="error-retry-btn"
            onClick={loadSoftwareTable}
          >
            Retry
          </button>
        </div>
      )}

      {/* 2. Analytics Cards Grid (Donut Chart & Top Publishers) */}
      <div className="software-analytics-grid">
        <SoftwareTypeDistribution
          categories={summaryData?.categories || []}
          totalApplications={summaryData?.total_installed ?? totalCount}
          loading={loadingSummary}
        />

        <TopSoftwarePublishers
          publishers={summaryData?.top_publishers || []}
          totalApplications={summaryData?.total_installed ?? totalCount}
          loading={loadingSummary}
        />
      </div>

      {/* 3. Full-width Paginated Software Inventory Table */}
      <InstalledSoftwareTable
        softwareList={softwareList}
        totalCount={totalCount}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        sortConfig={sortConfig}
        onSortChange={handleSortChange}
        loading={loadingList}
      />
    </div>
  );
}
