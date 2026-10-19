import { useReportsDashboard } from "../hooks/useReportsDashboard";
import { REPORT_CATEGORIES } from "../utils/reportUtils";
import ReportHeader from "../components/ReportHeader/ReportHeader";
import ReportTypeSelector from "../components/ReportTypeSelector/ReportTypeSelector";
import ReportSummaryCards from "../components/ReportSummaryCards/ReportSummaryCards";
import ReportFilters from "../components/ReportFilters/ReportFilters";
import ReportCharts from "../components/ReportCharts/ReportCharts";
import ReportTables from "../components/ReportTables/ReportTables";
import "./Reports.css";

function Reports() {
  const {
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
    refresh,
    handleExportCSV,
  } = useReportsDashboard();

  const currentCategoryObj =
    REPORT_CATEGORIES.find((c) => c.id === category) || REPORT_CATEGORIES[0];

  return (
    <div className="reports-page-wrapper">
      <ReportHeader
        onRefresh={refresh}
        onExport={handleExportCSV}
        loading={loading}
        exporting={exporting}
        lastRefreshedAt={lastRefreshedAt}
        successMsg={successMsg}
        errorMsg={error}
        categoryLabel={currentCategoryObj.label}
      />

      <ReportTypeSelector
        activeCategory={category}
        onSelectCategory={handleSelectCategory}
        overview={overview}
      />

      <ReportSummaryCards
        category={category}
        reportData={reportData}
        loading={loading}
      />

      <ReportFilters
        category={category}
        period={period}
        setPeriod={setPeriod}
        dateFrom={dateFrom}
        setDateFrom={setDateFrom}
        dateTo={dateTo}
        setDateTo={setDateTo}
        computerId={computerId}
        setComputerId={setComputerId}
        search={search}
        setSearch={setSearch}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        severityFilter={severityFilter}
        setSeverityFilter={setSeverityFilter}
        maintenanceTypeFilter={maintenanceTypeFilter}
        setMaintenanceTypeFilter={setMaintenanceTypeFilter}
        commandTypeFilter={commandTypeFilter}
        setCommandTypeFilter={setCommandTypeFilter}
        computersList={computersList}
        resetFilters={resetFilters}
        activeFiltersCount={activeFiltersCount}
      />

      <ReportCharts
        category={category}
        reportData={reportData}
        loading={loading}
      />

      <ReportTables
        category={category}
        reportData={reportData}
        loading={loading}
        page={page}
        onPageChange={setPage}
      />
    </div>
  );
}

export default Reports;