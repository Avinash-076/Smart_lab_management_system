import { useMaintenanceRecords } from "../hooks/useMaintenanceRecords";
import MaintenanceHeader from "../components/MaintenanceHeader/MaintenanceHeader";
import MaintenanceSummaryCards from "../components/MaintenanceSummaryCards/MaintenanceSummaryCards";
import MaintenanceFilters from "../components/MaintenanceFilters/MaintenanceFilters";
import MaintenanceTable from "../components/MaintenanceTable/MaintenanceTable";
import ScheduleMaintenanceModal from "../components/ScheduleMaintenanceModal/ScheduleMaintenanceModal";
import CompleteMaintenanceModal from "../components/CompleteMaintenanceModal/CompleteMaintenanceModal";
import MaintenanceDetailsModal from "../components/MaintenanceDetailsModal/MaintenanceDetailsModal";
import { exportMaintenanceToCsv } from "../utils/maintenanceUtils";
import "./MaintenanceRecords.css";

function MaintenanceRecords() {
  const {
    stats,
    computers,
    computerMap,
    loading,
    error,
    successMsg,
    selectedRecord,
    setSelectedRecord,
    editingRecord,
    setEditingRecord,
    search,
    setSearch,
    statusFilter,
    setStatusFilter,
    typeFilter,
    setTypeFilter,
    computerFilter,
    setComputerFilter,
    filteredRecords,
    resetFilters,
    loadData,
    handleStatusChange,
    handleDelete,
    isScheduleOpen,
    setIsScheduleOpen,
    scheduleLoading,
    scheduleError,
    handleSaveSchedule,
    completeModal,
    setCompleteModal,
    completeLoading,
    completeError,
    handleOpenComplete,
    handleCompleteSubmit,
    detailModal,
    setDetailModal,
  } = useMaintenanceRecords();

  const handleExportCsv = () => {
    exportMaintenanceToCsv(filteredRecords, computerMap);
  };

  const handleOpenScheduleModal = () => {
    setEditingRecord(null);
    setIsScheduleOpen(true);
  };

  const handleEditRecord = (record) => {
    setEditingRecord(record);
    setIsScheduleOpen(true);
  };

  const handleOpenDetails = (record) => {
    setDetailModal({
      isOpen: true,
      record,
    });
  };

  return (
    <div className="maintenance-management-page" data-testid="maintenance-management-page">
      {/* 1. Header with Breadcrumb & Quick Actions */}
      <MaintenanceHeader
        onRefresh={loadData}
        onSchedule={handleOpenScheduleModal}
        onExport={handleExportCsv}
        loading={loading}
      />

      {/* Alerts & Messages */}
      {error && (
        <div className="maintenance-alert-banner error" role="alert">
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="maintenance-alert-banner success" role="status">
          <span>{successMsg}</span>
        </div>
      )}

      {/* 2. Top 4 Metric KPI Cards */}
      <MaintenanceSummaryCards stats={stats} />

      {/* 3. Filtering Toolbar */}
      <MaintenanceFilters
        search={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusChange={setStatusFilter}
        typeFilter={typeFilter}
        onTypeChange={setTypeFilter}
        computerFilter={computerFilter}
        onComputerChange={setComputerFilter}
        computers={computers}
        onRefresh={loadData}
        onReset={resetFilters}
        loading={loading}
      />

      {/* 4. Full-Width Clean Records Table */}
      <MaintenanceTable
        records={filteredRecords}
        selectedRecord={selectedRecord}
        onSelectRecord={setSelectedRecord}
        computerMap={computerMap}
        onStatusChange={handleStatusChange}
        onOpenDetails={handleOpenDetails}
        onOpenComplete={handleOpenComplete}
        onEdit={handleEditRecord}
        onDelete={handleDelete}
        loading={loading}
      />

      {/* Floating Modal: Schedule / Edit Maintenance */}
      <ScheduleMaintenanceModal
        key={editingRecord ? `edit-${editingRecord.id}` : "new"}
        isOpen={isScheduleOpen}
        onClose={() => {
          setIsScheduleOpen(false);
          setEditingRecord(null);
        }}
        computers={computers}
        onSubmit={handleSaveSchedule}
        initialData={editingRecord}
        loading={scheduleLoading}
        error={scheduleError}
      />

      {/* Floating Modal: Complete Maintenance */}
      <CompleteMaintenanceModal
        isOpen={completeModal.isOpen}
        onClose={() =>
          setCompleteModal({
            isOpen: false,
            record: null,
            work_performed: "",
            notes: "",
          })
        }
        record={completeModal.record}
        workPerformed={completeModal.work_performed}
        onWorkPerformedChange={(val) =>
          setCompleteModal((prev) => ({ ...prev, work_performed: val }))
        }
        notes={completeModal.notes}
        onNotesChange={(val) =>
          setCompleteModal((prev) => ({ ...prev, notes: val }))
        }
        onSubmit={handleCompleteSubmit}
        loading={completeLoading}
        error={completeError}
      />

      {/* Floating Modal: Maintenance Details Inspector */}
      <MaintenanceDetailsModal
        isOpen={detailModal.isOpen}
        onClose={() => setDetailModal({ isOpen: false, record: null })}
        record={detailModal.record}
        onStartMaintenance={(id) => handleStatusChange(id, "in_progress")}
        onOpenComplete={(rec) => handleOpenComplete(rec)}
      />
    </div>
  );
}

export default MaintenanceRecords;
