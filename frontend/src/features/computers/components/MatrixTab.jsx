import { useState, useEffect, useCallback, useRef } from "react";
import LiveResourceHeader from "./LiveResourceHeader";
import MatrixChartsGrid from "./MatrixChartsGrid";
import ResourceDetailsRow from "./ResourceDetailsRow";
import TopProcessesRow from "./TopProcessesRow";
import { getComputerMetricSummary } from "../../../services/computerService";
import { getComputerProcessRankings } from "../../../services/processService";
import "./MatrixTab.css";

function MatrixTab({
  computerId,
  computer = null,
  onTabChange,
}) {
  const [timeRange, setTimeRange] = useState("1h");
  const [customRange, setCustomRange] = useState({ start: "", end: "" });
  const [summaryData, setSummaryData] = useState(null);
  const [processRankings, setProcessRankings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const isMountedRef = useRef(true);

  // Compute start/end dates for API query
  const getQueryWindow = useCallback((preset, custom) => {
    const now = Date.now();
    if (preset === "custom" && custom.start && custom.end) {
      return {
        start_time: new Date(custom.start),
        end_time: new Date(custom.end),
        range_preset: "custom",
      };
    }
    let durationMs = 60 * 60 * 1000; // 1 hour
    if (preset === "6h") {
      durationMs = 6 * 60 * 60 * 1000;
    } else if (preset === "24h") {
      durationMs = 24 * 60 * 60 * 1000;
    }
    return {
      start_time: new Date(now - durationMs),
      end_time: new Date(now),
      range_preset: preset,
    };
  }, []);

  const loadData = useCallback(
    async (preset = timeRange, custom = customRange, isBackground = false) => {
      if (!computerId) return;

      if (!isBackground) {
        setLoading(true);
      }
      setError("");

      try {
        const queryWindow = getQueryWindow(preset, custom);

        // Parallel fetch of metrics summary and process rankings
        const [metricSummary, rankings] = await Promise.allSettled([
          getComputerMetricSummary(computerId, queryWindow),
          getComputerProcessRankings(computerId, 5),
        ]);

        if (!isMountedRef.current) return;

        if (metricSummary.status === "fulfilled") {
          setSummaryData(metricSummary.value);
        } else {
          console.error("Metric summary error:", metricSummary.reason);
          setError(metricSummary.reason?.message || "Failed to load telemetry metrics.");
        }

        if (rankings.status === "fulfilled") {
          setProcessRankings(rankings.value);
        } else {
          console.warn("Process rankings error:", rankings.reason);
        }
      } catch (err) {
        if (!isMountedRef.current) return;
        console.error("MatrixTab load error:", err);
        setError(err.message || "Failed to load Matrix telemetry.");
      } finally {
        if (isMountedRef.current) {
          setLoading(false);
        }
      }
    },
    [computerId, getQueryWindow, timeRange, customRange]
  );

  // Initial load and whenever timeRange / customRange changes
  useEffect(() => {
    isMountedRef.current = true;
    let ignore = false;

    const timer = setTimeout(() => {
      if (!ignore) {
        loadData(timeRange, customRange, false);
      }
    }, 0);

    // Auto-refresh cadence (15s live polling)
    const intervalId = setInterval(() => {
      if (!ignore) {
        loadData(timeRange, customRange, true);
      }
    }, 15000);

    return () => {
      ignore = true;
      clearTimeout(timer);
      isMountedRef.current = false;
      clearInterval(intervalId);
    };
  }, [loadData, timeRange, customRange]);

  const handleTimeRangeChange = (preset) => {
    setTimeRange(preset);
  };

  const handleCustomRangeApply = ({ start, end }) => {
    setTimeRange("custom");
    setCustomRange({ start, end });
  };

  const isOnline = computer?.status?.toLowerCase() === "online";

  return (
    <div className="matrix-monitoring-tab">
      {/* 1. Header with live status and time range selector */}
      <LiveResourceHeader
        timeRange={timeRange}
        onTimeRangeChange={handleTimeRangeChange}
        customRange={customRange}
        onCustomRangeChange={setCustomRange}
        onApplyCustomRange={handleCustomRangeApply}
        onRefresh={() => loadData(timeRange, customRange, false)}
        loading={loading}
        isLive={isOnline}
      />

      {/* Error Banner */}
      {error && (
        <div className="matrix-error-banner" role="alert">
          <span className="error-icon">⚠️</span>
          <span className="error-msg">{error}</span>
          <button
            type="button"
            className="matrix-retry-btn"
            onClick={() => loadData(timeRange, customRange, false)}
          >
            Retry
          </button>
        </div>
      )}

      {/* 2. Four Time-Series Charts Grid */}
      <MatrixChartsGrid
        summary={summaryData}
        timeSeries={summaryData?.time_series || []}
        loading={loading && !summaryData}
      />

      {/* 3. Middle Row: Disk, Memory, and Network Details */}
      <ResourceDetailsRow
        diskPartitions={summaryData?.disk_partitions || []}
        memoryDetails={summaryData?.memory_details || {}}
        networkDetails={summaryData?.network_details || {}}
        loading={loading && !summaryData}
      />

      {/* 4. Bottom Row: Process Rankings */}
      <TopProcessesRow
        rankings={processRankings}
        loading={loading && !processRankings}
        onViewAll={() => {
          if (onTabChange) {
            onTabChange("processes");
          }
        }}
      />
    </div>
  );
}

export default MatrixTab;
