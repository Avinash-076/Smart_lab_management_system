import { useIssueManagement } from "../hooks/useIssueManagement";
import { exportIssuesToCsv } from "../utils/issueUtils";
import IssueHeader from "../components/IssueHeader/IssueHeader";
import IssueSummaryCards from "../components/IssueSummaryCards/IssueSummaryCards";
import IssueFilters from "../components/IssueFilters/IssueFilters";
import IssueTable from "../components/IssueTable/IssueTable";
import IssueDetailsPanel from "../components/IssueDetailsPanel/IssueDetailsPanel";
import ReportIssueModal from "../components/ReportIssueModal/ReportIssueModal";
import ResolveIssueModal from "../components/ResolveIssueModal/ResolveIssueModal";
import EditIssueModal from "../components/EditIssueModal/EditIssueModal";
import "./IssueManagement.css";

function IssueManagement({ onViewComputer }) {
  const {
    stats,
    computers,
    computerMap,
    loading,
    error,
    successMsg,
    selectedIssue,
    selectedComputer,
    setSelectedIssue,
    // Filters
    search,
    setSearch,
    statusFilter,
    setStatusFilter,
    priorityFilter,
    setPriorityFilter,
    computerFilter,
    setComputerFilter,
    dateRangeFilter,
    setDateRangeFilter,
    filteredIssues,
    resetFilters,
    // Actions & Modals
    loadData,
    handleCreateIssue,
    handleStatusChange,
    handleResolveIssue,
    handleUpdateIssue,
    handleDeleteIssue,
    handleAddComment,
    isReportOpen,
    setIsReportOpen,
    resolveModal,
    setResolveModal,
    editModal,
    setEditModal,
    actionLoadingId,
    realtimeAlert,
    setRealtimeAlert,
  } = useIssueManagement();

  const handleExportCsv = () => {
    exportIssuesToCsv(filteredIssues, computerMap);
  };

  const handleViewComputerClick = (issue) => {
    const comp =
      computers.find((c) => c.id === issue.computer_id) || {
        id: issue.computer_id,
        hostname: issue.computer_hostname || `PC-${issue.computer_id}`,
      };

    if (typeof onViewComputer === "function") {
      onViewComputer(comp);
    } else {
      // Fallback: trigger navigation event or alert
      window.dispatchEvent(
        new CustomEvent("slms:navigate-computer", { detail: comp })
      );
    }
  };

  return (
    <div className="issue-management-container" data-testid="issue-management-page">
      {/* 1. PAGE UPPER-RIGHT ACTIONS HEADER */}
      <IssueHeader
        onReportClick={() => setIsReportOpen(true)}
        onExportCsv={handleExportCsv}
        onRefresh={loadData}
        loading={loading}
        totalIssues={filteredIssues.length}
      />

      {/* 2. REAL-TIME WEBSOCKET LIVE ALERT BANNER */}
      {realtimeAlert && (
        <div
          className={`issue-live-alert ${realtimeAlert.type}`}
          role="alert"
        >
          <div className="issue-live-alert-left">
            <span style={{ fontSize: "18px" }}>
              {realtimeAlert.type === "created" ? "⚠️" : "✅"}
            </span>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span className="issue-live-alert-badge">
                  {realtimeAlert.type === "created" ? "Live Breach Alert" : "Auto-Recovery"}
                </span>
                <span style={{ fontSize: "11px", opacity: 0.8 }}>
                  {realtimeAlert.time}
                </span>
              </div>
              <div style={{ fontSize: "13px", marginTop: "2px", fontWeight: "500" }}>
                <strong>{realtimeAlert.computer}: </strong>
                <span>{realtimeAlert.title}</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            className="issue-live-alert-close"
            onClick={() => setRealtimeAlert(null)}
            aria-label="Dismiss alert"
          >
            ✕
          </button>
        </div>
      )}

      {/* 3. FEEDBACK BANNERS */}
      {successMsg && (
        <div className="issue-banner-success" role="status">
          <span>✓</span>
          <span>{successMsg}</span>
        </div>
      )}

      {error && (
        <div className="issue-banner-error" role="alert">
          <span>⚠ {error}</span>
          <button
            type="button"
            className="issue-banner-retry-btn"
            onClick={loadData}
          >
            Retry
          </button>
        </div>
      )}

      {/* 4. SUMMARY METRIC CARDS */}
      <IssueSummaryCards stats={stats} />

      {/* 5. FILTER SECTION */}
      <IssueFilters
        search={search}
        onSearchChange={setSearch}
        statusFilter={statusFilter}
        onStatusChange={setStatusFilter}
        priorityFilter={priorityFilter}
        onPriorityChange={setPriorityFilter}
        computerFilter={computerFilter}
        onComputerChange={setComputerFilter}
        dateRangeFilter={dateRangeFilter}
        onDateRangeChange={setDateRangeFilter}
        computers={computers}
        onRefresh={loadData}
        onReset={resetFilters}
        loading={loading}
      />

      {/* 6. MAIN SPLIT CONTENT: TABLE + RIGHT-HAND DETAILS PANEL */}
      <div className="issue-main-layout">
        <IssueTable
          issues={filteredIssues}
          selectedIssue={selectedIssue}
          onSelectIssue={setSelectedIssue}
          computerMap={computerMap}
          onStatusChange={handleStatusChange}
          onOpenResolve={(issue) => setResolveModal({ isOpen: true, issue })}
          onEditIssue={(issue) => setEditModal({ isOpen: true, issue })}
          onDeleteIssue={handleDeleteIssue}
          actionLoadingId={actionLoadingId}
          loading={loading}
        />

        {selectedIssue && (
          <IssueDetailsPanel
            issue={selectedIssue}
            computer={selectedComputer}
            onClose={() => setSelectedIssue(null)}
            onStatusChange={handleStatusChange}
            onOpenResolve={(issue) => setResolveModal({ isOpen: true, issue })}
            onAddComment={handleAddComment}
            onViewComputer={handleViewComputerClick}
            onEditIssue={(issue) => setEditModal({ isOpen: true, issue })}
            loading={Boolean(actionLoadingId)}
          />
        )}
      </div>

      {/* 7. MODALS */}
      <ReportIssueModal
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
        computers={computers}
        onSubmit={handleCreateIssue}
        loading={actionLoadingId === "create"}
      />

      <ResolveIssueModal
        isOpen={resolveModal.isOpen}
        issue={resolveModal.issue}
        onClose={() => setResolveModal({ isOpen: false, issue: null })}
        onSubmit={handleResolveIssue}
        loading={Boolean(actionLoadingId)}
      />

      <EditIssueModal
        isOpen={editModal.isOpen}
        issue={editModal.issue}
        onClose={() => setEditModal({ isOpen: false, issue: null })}
        onSubmit={handleUpdateIssue}
        loading={Boolean(actionLoadingId)}
      />
    </div>
  );
}

export default IssueManagement;