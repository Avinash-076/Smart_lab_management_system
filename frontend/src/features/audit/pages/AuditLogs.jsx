import { useAuditLogs } from "../hooks/useAuditLogs";
import AuditHeader from "../components/AuditHeader/AuditHeader";
import AuditStats from "../components/AuditStats/AuditStats";
import AuditFilters from "../components/AuditFilters/AuditFilters";
import AuditTable from "../components/AuditTable/AuditTable";
import AuditDetailModal from "../components/AuditDetailModal/AuditDetailModal";
import "./AuditLogs.css";

function AuditLogs() {
  const {
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
    refresh,
    handleExportCSV,
    selectedLog,
    handleOpenDetail,
    handleCloseDetail,
  } = useAuditLogs();

  return (
    <div className="audit-logs-page-wrapper" data-testid="audit-logs-page">
      <AuditHeader
        onRefresh={refresh}
        onExport={handleExportCSV}
        loading={loading}
        exporting={exporting}
        lastRefreshedAt={lastRefreshedAt}
        successMsg={successMsg}
        errorMsg={error}
      />

      <AuditStats
        stats={stats}
        loading={statsLoading}
      />

      <AuditFilters
        search={search}
        setSearch={setSearch}
        resultFilter={resultFilter}
        setResultFilter={setResultFilter}
        targetTypeFilter={targetTypeFilter}
        setTargetTypeFilter={setTargetTypeFilter}
        dateFrom={dateFrom}
        setDateFrom={setDateFrom}
        dateTo={dateTo}
        setDateTo={setDateTo}
        activeFiltersCount={activeFiltersCount}
        onResetFilters={resetFilters}
        setPage={setPage}
      />

      <AuditTable
        logs={logs}
        totalCount={totalCount}
        totalPages={totalPages}
        page={page}
        setPage={setPage}
        limit={limit}
        setLimit={setLimit}
        loading={loading}
        onInspect={handleOpenDetail}
      />

      {selectedLog && (
        <AuditDetailModal
          log={selectedLog}
          onClose={handleCloseDetail}
        />
      )}
    </div>
  );
}

export default AuditLogs;
