import { useDashboardData } from "./hooks/useDashboardData";
import DashboardClock from "./components/DashboardClock/DashboardClock";
import DashboardSummaryCards from "./components/DashboardSummaryCards/DashboardSummaryCards";
import SystemOverviewCard from "./components/SystemOverviewCard/SystemOverviewCard";
import ResourceUsageCard from "./components/ResourceUsageCard/ResourceUsageCard";
import RecentAlertsCard from "./components/RecentAlertsCard/RecentAlertsCard";
import LiveSystemTable from "./components/LiveSystemTable/LiveSystemTable";
import QuickActionsCard from "./components/QuickActionsCard/QuickActionsCard";
import ReportsAnalyticsCard from "./components/ReportsAnalyticsCard/ReportsAnalyticsCard";
import DashboardCommandModals from "./components/DashboardModals/DashboardCommandModals";
import "./Dashboard.css";

export default function Dashboard({
  searchQuery = "",
  onSearchChange,
  onViewComputer,
  onNavigate,
}) {
  const {
    computers,
    metricsSummary,
    timeline,
    notifications,
    loading,
    refreshing,
    error,
    toast,
    // Metrics
    totalComputers,
    onlineComputers,
    offlineComputers,
    highRamCount,
    lowDiskCount,
    activeAlertsCount,
    // Selection
    selectedIds,
    selectedComputersList,
    selectedSystemId,
    setSelectedSystemId,
    handleToggleSelect,
    handleToggleSelectAll,
    // Modals
    modalState,
    setModalState,
    handleQuickActionClick,
    handleConfirmCommand,
    loadDashboardData,
  } = useDashboardData();

  const handleInspectComputer = (comp) => {
    if (onViewComputer) {
      onViewComputer(comp);
    } else if (onNavigate) {
      onNavigate("details", comp);
    }
  };

  const handleRemoteCommand = (comp) => {
    if (onNavigate) {
      onNavigate("remote-control", comp);
    }
  };

  const handlePowerCommand = (comp) => {
    // Select this computer and open restart confirmation
    handleToggleSelect(comp.id);
    handleQuickActionClick("restart");
  };

  return (
    <div className="dashboard-page" data-testid="dashboard-page">
      {/* Toast Alert Feedback */}
      {toast && (
        <div className={`dashboard-toast toast-${toast.type}`}>
          <span className="toast-icon">
            {toast.type === "success" ? "✓" : "⚠️"}
          </span>
          <span className="toast-message">{toast.message}</span>
        </div>
      )}

      {/* Error Retry Banner */}
      {error && (
        <div className="dashboard-error-banner" role="alert">
          <span>⚠️ {error}</span>
          <button
            type="button"
            className="dashboard-retry-btn"
            onClick={() => loadDashboardData(true)}
          >
            Retry
          </button>
        </div>
      )}

      {/* Top Section: Date & Time Ticker Card */}
      <div className="dashboard-top-bar">
        {loading && computers.length === 0 ? (
          <span className="dashboard-loading-text">Loading telemetry...</span>
        ) : (
          <div className="dashboard-top-bar-spacer" />
        )}
        <DashboardClock />
      </div>

      {/* Row 1: 6 Summary Metric Cards */}
      <section className="dashboard-section" aria-label="Summary Metrics">
        <DashboardSummaryCards
          totalComputers={totalComputers}
          onlineComputers={onlineComputers}
          offlineComputers={offlineComputers}
          highRamCount={highRamCount}
          lowDiskCount={lowDiskCount}
          activeAlertsCount={activeAlertsCount}
        />
      </section>

      {/* Main 2-Column Dashboard Layout: Left (Overview + Live Table), Right (Alerts + Actions + Reports) */}
      <div className="dashboard-main-layout" aria-label="Monitoring and Actions">
        {/* Left Column: Combined width of System Overview + Resource Usage Summary, with Live System Table below */}
        <div className="dashboard-left-column">
          {/* Top Row: System Overview & Resource Usage Summary side-by-side */}
          <section className="dashboard-overview-row" aria-label="System Analytics">
            {/* Card 1: System Overview (Donut chart & breakdown) */}
            <SystemOverviewCard
              totalComputers={totalComputers}
              onlineComputers={onlineComputers}
              offlineComputers={offlineComputers}
              highRamCount={highRamCount}
              lowDiskCount={lowDiskCount}
              onViewAll={() => onNavigate?.("computers")}
            />

            {/* Card 2: Resource Usage Summary (Circular Gauges + Trendline) */}
            <ResourceUsageCard
              avgCpu={metricsSummary.avg_cpu_percent}
              avgRam={metricsSummary.avg_ram_percent}
              avgDisk={metricsSummary.avg_disk_percent}
              timeline={timeline}
              computers={computers}
              selectedSystemId={selectedSystemId}
              onSelectSystem={setSelectedSystemId}
            />
          </section>

          {/* Bottom Row: Live System Status Table (spanning full width of overview + resource usage) */}
          <div className="dashboard-table-wrap">
            <LiveSystemTable
              computers={computers}
              selectedIds={selectedIds}
              onToggleSelect={handleToggleSelect}
              onToggleSelectAll={handleToggleSelectAll}
              searchQuery={searchQuery}
              onSearchChange={onSearchChange}
              onInspect={handleInspectComputer}
              onRemoteCommand={handleRemoteCommand}
              onPowerCommand={handlePowerCommand}
            />
          </div>
        </div>

        {/* Right Column: Recent Alerts, Quick Actions, Reports & Analytics with aligned widths */}
        <div className="dashboard-right-column">
          {/* Recent Alerts */}
          <RecentAlertsCard
            alerts={notifications}
            onViewAll={() => onNavigate?.("issues")}
          />

          {/* Quick Actions Card */}
          <QuickActionsCard
            selectedCount={selectedIds.size}
            onActionClick={handleQuickActionClick}
            onRefreshAll={() => loadDashboardData(true)}
            refreshing={refreshing}
          />

          {/* Reports & Analytics Card */}
          <ReportsAnalyticsCard onNavigate={onNavigate} />
        </div>
      </div>

      {/* Interactive Command & Message Modals */}
      <DashboardCommandModals
        modalType={modalState.type}
        actionType={modalState.action}
        selectedComputers={selectedComputersList}
        onConfirm={handleConfirmCommand}
        onClose={() => setModalState({ type: null, action: null })}
      />
    </div>
  );
}
