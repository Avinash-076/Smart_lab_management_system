import { useState, useEffect, useCallback, startTransition } from "react";
import ExecuteCommandPanel from "./ExecuteCommandPanel";
import RecentCommandActivity from "./RecentCommandActivity";
import CommandHistoryFilters from "./CommandHistoryFilters";
import CommandHistoryTable from "./CommandHistoryTable";
import CommandDetailsPanel from "./CommandDetailsPanel";
import {
  issueCommand,
  getComputerCommands,
  getComputerCommandsSummary,
  cancelCommand,
  exportCommandsToCsv,
} from "../../../services/commandService";
import "./RemoteControlTab.css";

export default function RemoteControlTab({
  computerId,
  computer,
  onSummaryUpdate = null,
}) {
  // Filters and pagination state
  const [filters, setFilters] = useState({
    search: "",
    status: "all",
    date_range: "30d",
  });
  const [page, setPage] = useState(1);
  const pageSize = 10;

  // Data state
  const [commands, setCommands] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [summaryData, setSummaryData] = useState(null);
  const [selectedCommand, setSelectedCommand] = useState(null);

  // Status state
  const [loadingList, setLoadingList] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [error, setError] = useState("");

  const isOnline = (computer?.status || "").toLowerCase() === "online";
  const computerName = computer?.hostname || `PC-${computerId}`;

  // Calculate date range for filter
  const getDateRangeFilter = useCallback(() => {
    if (!filters.date_range || filters.date_range === "all") {
      return { start_date: undefined, end_date: undefined };
    }
    const now = new Date();
    let start = new Date();
    if (filters.date_range === "24h") {
      start.setHours(now.getHours() - 24);
    } else if (filters.date_range === "7d") {
      start.setDate(now.getDate() - 7);
    } else if (filters.date_range === "30d") {
      start.setDate(now.getDate() - 30);
    }
    return {
      start_date: start.toISOString(),
      end_date: now.toISOString(),
    };
  }, [filters.date_range]);

  // Load summary and recent activities
  const loadSummary = useCallback(async () => {
    if (!computerId) return;
    try {
      setLoadingSummary(true);
      const sum = await getComputerCommandsSummary(computerId);
      setSummaryData(sum);
      if (onSummaryUpdate) {
        onSummaryUpdate(sum);
      }
    } catch (err) {
      console.warn("Could not load command summary:", err);
    } finally {
      setLoadingSummary(false);
    }
  }, [computerId, onSummaryUpdate]);

  // Load paginated and filtered command history table
  const loadCommandsTable = useCallback(async () => {
    if (!computerId) return;
    try {
      setLoadingList(true);
      setError("");

      const { start_date, end_date } = getDateRangeFilter();

      const res = await getComputerCommands(computerId, {
        search: filters.search,
        status: filters.status,
        start_date,
        end_date,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      });

      startTransition(() => {
        setCommands(res.data || []);
        setTotalCount((prev) => {
          if (typeof res.totalCount === "number" && res.totalCount >= 0) {
            return res.totalCount;
          }
          return prev || (res.data?.length || 0);
        });

        // If previously selected command is in the list, keep it updated
        if (selectedCommand) {
          const updated = (res.data || []).find((c) => c.id === selectedCommand.id);
          if (updated) {
            setSelectedCommand(updated);
          }
        }
      });
    } catch (err) {
      console.error("Failed to load command history:", err);
      setError(err.message || "Failed to load command records.");
      setCommands([]);
      setTotalCount(0);
    } finally {
      setLoadingList(false);
    }
  }, [computerId, filters, page, getDateRangeFilter, selectedCommand]);

  // Initial load
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
        loadCommandsTable();
      }
    });
    return () => {
      ignore = true;
    };
  }, [loadCommandsTable]);

  // Apply filters
  const handleApplyFilters = (newFilters) => {
    setFilters(newFilters);
    setPage(1);
  };

  // Issue command handler
  const handleExecuteCommand = async (commandPayload) => {
    setExecuting(true);
    try {
      const res = await issueCommand(computerId, commandPayload);
      // Refresh summary and command table
      await loadSummary();
      await loadCommandsTable();
      return res;
    } finally {
      setExecuting(false);
    }
  };

  // Cancel command handler
  const handleCancelCommand = async (commandId) => {
    try {
      await cancelCommand(commandId, computerId);
      await loadSummary();
      await loadCommandsTable();
    } catch (err) {
      console.error("Failed to cancel command:", err);
      alert(err.message || "Failed to cancel command.");
    }
  };

  // Re-issue command handler
  const handleReissueCommand = async (cmd) => {
    if (!cmd?.command_type) return;
    try {
      await handleExecuteCommand({
        command_type: cmd.command_type,
        payload: cmd.payload,
      });
    } catch (err) {
      console.error("Failed to re-issue command:", err);
    }
  };

  // Export CSV handler
  const handleExportCsv = async () => {
    const { start_date, end_date } = getDateRangeFilter();
    try {
      await exportCommandsToCsv(
        computerId,
        {
          search: filters.search,
          status: filters.status,
          start_date,
          end_date,
        },
        computerName
      );
    } catch (err) {
      console.error("Failed to export command history CSV:", err);
      alert("Failed to export commands CSV.");
    }
  };

  return (
    <div className="remote-control-tab-container">
      {/* 1. Middle Row: Execute Command + Recent Activity */}
      <div className="remote-control-top-row">
        <div className="execute-command-column">
          <ExecuteCommandPanel
            isOnline={isOnline}
            onExecute={handleExecuteCommand}
            executing={executing}
          />
        </div>

        <div className="recent-activity-column">
          <RecentCommandActivity
            activities={summaryData?.recent_activities || []}
            loading={loadingSummary}
            onSelectActivity={(act) => setSelectedCommand(act)}
          />
        </div>
      </div>

      {/* 2. Bottom Card: Command History */}
      <div className="command-history-card">
        {/* Card Header & Filter Bar */}
        <div className="history-card-header">
          <div className="history-card-title-group">
            <div className="history-icon-badge">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="8" y1="6" x2="21" y2="6" />
                <line x1="8" y1="12" x2="21" y2="12" />
                <line x1="8" y1="18" x2="21" y2="18" />
                <line x1="3" y1="6" x2="3.01" y2="6" />
                <line x1="3" y1="12" x2="3.01" y2="12" />
                <line x1="3" y1="18" x2="3.01" y2="18" />
              </svg>
            </div>
            <h2 className="history-card-title">Command History</h2>
          </div>

          <div className="history-card-filters">
            <CommandHistoryFilters
              filters={filters}
              onApply={handleApplyFilters}
              onExport={handleExportCsv}
              loading={loadingList}
            />
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="history-error-banner">
            <span>{error}</span>
          </div>
        )}

        {/* Table & Split Details Layout */}
        <div className={`history-split-layout ${selectedCommand ? "with-details" : ""}`}>
          <div className="history-table-section">
            <CommandHistoryTable
              commands={commands}
              totalCount={totalCount}
              page={page}
              pageSize={pageSize}
              onPageChange={setPage}
              loading={loadingList}
              selectedCommandId={selectedCommand?.id}
              onSelectCommand={(cmd) => setSelectedCommand(cmd)}
              onCancelCommand={handleCancelCommand}
              onReissueCommand={handleReissueCommand}
            />
          </div>

          {selectedCommand && (
            <div className="history-details-section">
              <CommandDetailsPanel
                command={selectedCommand}
                onClose={() => setSelectedCommand(null)}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
