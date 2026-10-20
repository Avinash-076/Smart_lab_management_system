import { useSoftwareInventory } from "../hooks/useSoftwareInventory";
import SoftwareHeader from "../components/SoftwareHeader/SoftwareHeader";
import SoftwareSummaryCards from "../components/SoftwareSummaryCards/SoftwareSummaryCards";
import SoftwareFilters from "../components/SoftwareFilters/SoftwareFilters";
import SoftwareCharts from "../components/SoftwareCharts/SoftwareCharts";
import SoftwareTable from "../components/SoftwareTable/SoftwareTable";
import SoftwareDetailModal from "../components/SoftwareDetailModal/SoftwareDetailModal";
import ExportReportModal from "../components/ExportReportModal/ExportReportModal";
import "./SoftwareInventory.css";

export default function SoftwareInventory({ onViewComputer }) {
  const {
    computers,
    displayedSoftware,
    totalCount,
    summary,
    loading,
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
    refresh,
    handleExportCSV,
  } = useSoftwareInventory();

  return (
    <div className="software-inventory-page" data-testid="software-inventory-page">
      {/* 1. Header with Title & Export Report action */}
      <SoftwareHeader
        onRefresh={refresh}
        onExportReport={handleOpenExportModal}
        loading={loading}
        lastRefreshedAt={lastRefreshedAt}
        successMsg={successMsg}
        errorMsg={error}
      />

      {/* 2. 4 KPI Summary Cards matching reference design */}
      <SoftwareSummaryCards
        summary={summary}
        computersCount={computers.length}
        totalRecords={totalCount}
        loading={loading}
      />

      {/* 3. Software Filters Toolbar */}
      <SoftwareFilters
        search={search}
        setSearch={setSearch}
        osFilter={osFilter}
        setOsFilter={setOsFilter}
        publisherFilter={publisherFilter}
        setPublisherFilter={setPublisherFilter}
        computerFilter={computerFilter}
        setComputerFilter={setComputerFilter}
        statusFilter={statusFilter}
        setStatusFilter={setStatusFilter}
        computers={computers}
        availablePublishers={summary?.available_publishers || []}
        availableOs={summary?.available_os || []}
        onApply={handleApplyFilters}
        onReset={handleResetFilters}
      />

      {/* 4. Analytics Row (Top Software, OS Donut Chart, Top Publishers) */}
      <SoftwareCharts
        summary={summary}
        totalComputers={computers.length || 5}
        totalRecords={totalCount}
      />

      {/* 5. Installed Software Data Table with Checkboxes & Pagination */}
      <SoftwareTable
        softwareList={displayedSoftware}
        totalCount={totalCount}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={setPageSize}
        sortConfig={sortConfig}
        onSortChange={handleSortChange}
        tableSearch={tableSearch}
        setTableSearch={setTableSearch}
        viewMode={viewMode}
        onToggleViewMode={() =>
          setViewMode((prev) => (prev === "table" ? "cards" : "table"))
        }
        selectedSoftwareIds={selectedSoftwareIds}
        onToggleSelectAll={handleToggleSelectAll}
        onToggleSelectItem={handleToggleSelectItem}
        onClearSelection={handleClearSelection}
        onInspect={handleOpenDetail}
        onExportCsv={handleExportCSV}
        onExportItem={() => handleExportCSV(false)}
        loading={loading}
      />

      {/* 6. Software Detail Modal (Inspect installations & computers) */}
      {selectedSoftware && (
        <SoftwareDetailModal
          software={selectedSoftware}
          onClose={handleCloseDetail}
          onViewComputer={onViewComputer}
        />
      )}

      {/* 7. Export Report Modal */}
      {isExportReportOpen && (
        <ExportReportModal
          isOpen={isExportReportOpen}
          onClose={handleCloseExportModal}
          softwareList={displayedSoftware}
          selectedSoftwareIds={selectedSoftwareIds}
          totalCount={totalCount}
        />
      )}
    </div>
  );
}