import { useState } from "react";
import Icon from "./Icon";

function formatTimeLabel(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function formatFullDateTime(dateStr) {
  if (!dateStr) return "";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleString([], {
      dateStyle: "medium",
      timeStyle: "medium",
    });
  } catch {
    return "";
  }
}

function MetricChart({
  metrics = [],
  loading = false,
  error = "",
  timeRange = "1h",
  onTimeRangeChange,
  onRefresh,
}) {
  const [activeMetric, setActiveMetric] = useState("all"); // 'all' | 'cpu' | 'ram' | 'disk'
  const [hoverIndex, setHoverIndex] = useState(null);

  // Chronological sorting (oldest to newest for X-axis left to right)
  const sortedMetrics = [...metrics].sort(
    (a, b) => new Date(a.recorded_at) - new Date(b.recorded_at)
  );

  const count = sortedMetrics.length;

  // Compute summary stats
  const cpuValues = sortedMetrics.map((m) => m.cpu_usage).filter((v) => typeof v === "number");
  const ramValues = sortedMetrics.map((m) => m.ram_usage).filter((v) => typeof v === "number");
  const diskValues = sortedMetrics.map((m) => m.disk_usage).filter((v) => typeof v === "number");

  const calcStats = (vals) => {
    if (vals.length === 0) return { avg: null, min: null, max: null, latest: null };
    const sum = vals.reduce((a, b) => a + b, 0);
    return {
      avg: (sum / vals.length).toFixed(1),
      min: Math.min(...vals).toFixed(1),
      max: Math.max(...vals).toFixed(1),
      latest: vals[vals.length - 1].toFixed(1),
    };
  };

  const cpuStats = calcStats(cpuValues);
  const ramStats = calcStats(ramValues);
  const diskStats = calcStats(diskValues);

  // Chart dimensions & scaling
  const width = 800;
  const height = 260;
  const padding = { top: 20, right: 30, bottom: 35, left: 45 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const getX = (index) => {
    if (count <= 1) return padding.left + chartWidth / 2;
    return padding.left + (index / (count - 1)) * chartWidth;
  };

  const getY = (val) => {
    const clamped = Math.max(0, Math.min(100, val || 0));
    return padding.top + chartHeight - (clamped / 100) * chartHeight;
  };

  const createPath = (key) => {
    if (count === 0) return "";
    if (count === 1) {
      const x = getX(0);
      const y = getY(sortedMetrics[0][key]);
      return `M ${x} ${y}`;
    }
    return sortedMetrics.reduce((acc, item, idx) => {
      const x = getX(idx);
      const y = getY(item[key]);
      return `${acc} ${idx === 0 ? "M" : "L"} ${x} ${y}`;
    }, "");
  };

  const createAreaPath = (key) => {
    if (count <= 1) return "";
    const line = createPath(key);
    const startX = getX(0);
    const endX = getX(count - 1);
    const bottomY = padding.top + chartHeight;
    return `${line} L ${endX} ${bottomY} L ${startX} ${bottomY} Z`;
  };

  const cpuPath = createPath("cpu_usage");
  const ramPath = createPath("ram_usage");
  const diskPath = createPath("disk_usage");

  const cpuArea = createAreaPath("cpu_usage");
  const ramArea = createAreaPath("ram_usage");
  const diskArea = createAreaPath("disk_usage");

  const hoveredItem = hoverIndex !== null && sortedMetrics[hoverIndex] ? sortedMetrics[hoverIndex] : null;

  return (
    <div className="table-card" style={{ marginTop: "24px", overflow: "hidden" }}>
      {/* HEADER & CONTROLS */}
      <div
        style={{
          padding: "18px 22px",
          borderBottom: "1px solid #edf0f4",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "14px",
          background: "#ffffff",
        }}
      >
        <div>
          <h3 style={{ margin: 0, fontSize: "16px", color: "#101a3d" }}>
            Historical Telemetry Charts
          </h3>
          <p style={{ margin: "4px 0 0", fontSize: "12px", color: "#68748b" }}>
            Query historical CPU, RAM, and Disk utilization over time.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* METRIC FILTER TABS */}
          <div
            style={{
              display: "inline-flex",
              background: "#f1f5f9",
              padding: "3px",
              borderRadius: "8px",
              fontSize: "12px",
            }}
          >
            {[
              { id: "all", label: "All" },
              { id: "cpu", label: "CPU" },
              { id: "ram", label: "RAM" },
              { id: "disk", label: "Disk" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveMetric(tab.id)}
                style={{
                  border: "none",
                  background: activeMetric === tab.id ? "#ffffff" : "transparent",
                  color: activeMetric === tab.id ? "#0962df" : "#475569",
                  fontWeight: activeMetric === tab.id ? "600" : "500",
                  padding: "5px 12px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  boxShadow: activeMetric === tab.id ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
                  transition: "all 0.15s ease",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* TIME RANGE SELECTOR */}
          <div
            style={{
              display: "inline-flex",
              background: "#eaf2ff",
              padding: "3px",
              borderRadius: "8px",
              fontSize: "12px",
            }}
          >
            {[
              { id: "1h", label: "Last 1h" },
              { id: "6h", label: "Last 6h" },
              { id: "24h", label: "Last 24h" },
            ].map((range) => (
              <button
                key={range.id}
                onClick={() => onTimeRangeChange && onTimeRangeChange(range.id)}
                style={{
                  border: "none",
                  background: timeRange === range.id ? "#0962df" : "transparent",
                  color: timeRange === range.id ? "#ffffff" : "#0962df",
                  fontWeight: timeRange === range.id ? "600" : "500",
                  padding: "5px 12px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {range.label}
              </button>
            ))}
          </div>

          {/* REFRESH BUTTON */}
          <button
            className="export"
            onClick={onRefresh}
            disabled={loading}
            title="Reload historical metrics"
            style={{ width: "auto", padding: "0 12px", height: "34px", fontSize: "12px" }}
          >
            <Icon type="refresh" size={14} />
            Refresh
          </button>
        </div>
      </div>

      {/* BODY CONTENT */}
      {loading ? (
        <div style={{ padding: "60px 20px", textAlign: "center" }}>
          <div className="empty-state">
            <Icon type="refresh" size={36} />
            <h3 style={{ color: "#101a3d" }}>Loading historical telemetry...</h3>
            <p>Fetching time-series records for {timeRange === "1h" ? "last 1 hour" : timeRange === "6h" ? "last 6 hours" : "last 24 hours"}.</p>
          </div>
        </div>
      ) : error ? (
        <div style={{ padding: "50px 20px", textAlign: "center" }}>
          <div className="empty-state">
            <Icon type="details" size={36} />
            <h3 style={{ color: "#dc2626" }}>Failed to load historical metrics</h3>
            <p>{error}</p>
            <button
              className="refresh"
              onClick={onRefresh}
              style={{ marginTop: "14px", display: "inline-flex" }}
            >
              <Icon type="refresh" size={16} />
              Try Again
            </button>
          </div>
        </div>
      ) : count === 0 ? (
        <div style={{ padding: "60px 20px", textAlign: "center" }}>
          <div className="empty-state">
            <Icon type="computer" size={36} />
            <h3 style={{ color: "#101a3d" }}>No metric data available for this time range</h3>
            <p>
              No telemetry data was recorded in the selected window ({timeRange === "1h" ? "last 1 hour" : timeRange === "6h" ? "last 6 hours" : "last 24 hours"}).
            </p>
          </div>
        </div>
      ) : (
        <div style={{ padding: "20px 22px" }}>
          {/* LEGEND & SUMMARY STATS */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "14px",
              marginBottom: "18px",
            }}
          >
            {(activeMetric === "all" || activeMetric === "cpu") && (
              <div
                style={{
                  background: "#f0f6ff",
                  border: "1px solid #dbeafe",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  borderLeft: "4px solid #0962df",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <b style={{ color: "#0962df", fontSize: "13px" }}>CPU Usage</b>
                  <span style={{ fontSize: "11px", color: "#64748b" }}>Latest: {cpuStats.latest}%</span>
                </div>
                <div style={{ fontSize: "11px", color: "#475569", display: "flex", gap: "10px" }}>
                  <span>Avg: <b>{cpuStats.avg}%</b></span>
                  <span>Min: <b>{cpuStats.min}%</b></span>
                  <span>Max: <b>{cpuStats.max}%</b></span>
                </div>
              </div>
            )}

            {(activeMetric === "all" || activeMetric === "ram") && (
              <div
                style={{
                  background: "#f0fdf4",
                  border: "1px solid #dcfce7",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  borderLeft: "4px solid #159b55",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <b style={{ color: "#159b55", fontSize: "13px" }}>RAM Usage</b>
                  <span style={{ fontSize: "11px", color: "#64748b" }}>Latest: {ramStats.latest}%</span>
                </div>
                <div style={{ fontSize: "11px", color: "#475569", display: "flex", gap: "10px" }}>
                  <span>Avg: <b>{ramStats.avg}%</b></span>
                  <span>Min: <b>{ramStats.min}%</b></span>
                  <span>Max: <b>{ramStats.max}%</b></span>
                </div>
              </div>
            )}

            {(activeMetric === "all" || activeMetric === "disk") && (
              <div
                style={{
                  background: "#fffbeb",
                  border: "1px solid #fef3c7",
                  borderRadius: "8px",
                  padding: "10px 14px",
                  borderLeft: "4px solid #f39b13",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "4px" }}>
                  <b style={{ color: "#f39b13", fontSize: "13px" }}>Disk Usage</b>
                  <span style={{ fontSize: "11px", color: "#64748b" }}>Latest: {diskStats.latest}%</span>
                </div>
                <div style={{ fontSize: "11px", color: "#475569", display: "flex", gap: "10px" }}>
                  <span>Avg: <b>{diskStats.avg}%</b></span>
                  <span>Min: <b>{diskStats.min}%</b></span>
                  <span>Max: <b>{diskStats.max}%</b></span>
                </div>
              </div>
            )}
          </div>

          {/* SVG CHART */}
          <div style={{ position: "relative", width: "100%", overflowX: "auto" }}>
            <svg
              viewBox={`0 0 ${width} ${height}`}
              style={{ width: "100%", height: "auto", minWidth: "550px", display: "block" }}
              onMouseLeave={() => setHoverIndex(null)}
            >
              <defs>
                <linearGradient id="cpuGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#0962df" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#0962df" stopOpacity="0.0" />
                </linearGradient>
                <linearGradient id="ramGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#159b55" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#159b55" stopOpacity="0.0" />
                </linearGradient>
                <linearGradient id="diskGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#f39b13" stopOpacity="0.25" />
                  <stop offset="100%" stopColor="#f39b13" stopOpacity="0.0" />
                </linearGradient>
              </defs>

              {/* HORIZONTAL GRID LINES & Y-AXIS LABELS */}
              {[0, 25, 50, 75, 100].map((val) => {
                const y = getY(val);
                return (
                  <g key={val}>
                    <line
                      x1={padding.left}
                      y1={y}
                      x2={width - padding.right}
                      y2={y}
                      stroke="#e2e8f0"
                      strokeDasharray={val === 0 ? "none" : "3,3"}
                      strokeWidth={val === 0 ? "1.5" : "1"}
                    />
                    <text
                      x={padding.left - 8}
                      y={y + 4}
                      textAnchor="end"
                      fontSize="10"
                      fill="#94a3b8"
                      fontFamily="sans-serif"
                    >
                      {val}%
                    </text>
                  </g>
                );
              })}

              {/* AREA FILLS */}
              {(activeMetric === "all" || activeMetric === "cpu") && cpuArea && (
                <path d={cpuArea} fill="url(#cpuGradient)" />
              )}
              {(activeMetric === "all" || activeMetric === "ram") && ramArea && (
                <path d={ramArea} fill="url(#ramGradient)" />
              )}
              {(activeMetric === "all" || activeMetric === "disk") && diskArea && (
                <path d={diskArea} fill="url(#diskGradient)" />
              )}

              {/* LINE PATHS */}
              {(activeMetric === "all" || activeMetric === "cpu") && cpuPath && (
                <path
                  d={cpuPath}
                  fill="none"
                  stroke="#0962df"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}
              {(activeMetric === "all" || activeMetric === "ram") && ramPath && (
                <path
                  d={ramPath}
                  fill="none"
                  stroke="#159b55"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}
              {(activeMetric === "all" || activeMetric === "disk") && diskPath && (
                <path
                  d={diskPath}
                  fill="none"
                  stroke="#f39b13"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              )}

              {/* DATA POINTS (If small number of items or single item) */}
              {count <= 25 &&
                sortedMetrics.map((item, idx) => {
                  const x = getX(idx);
                  return (
                    <g key={item.id || idx}>
                      {(activeMetric === "all" || activeMetric === "cpu") && (
                        <circle
                          cx={x}
                          cy={getY(item.cpu_usage)}
                          r={hoverIndex === idx ? "5" : "3.5"}
                          fill="#0962df"
                          stroke="#ffffff"
                          strokeWidth="1.5"
                        />
                      )}
                      {(activeMetric === "all" || activeMetric === "ram") && (
                        <circle
                          cx={x}
                          cy={getY(item.ram_usage)}
                          r={hoverIndex === idx ? "5" : "3.5"}
                          fill="#159b55"
                          stroke="#ffffff"
                          strokeWidth="1.5"
                        />
                      )}
                      {(activeMetric === "all" || activeMetric === "disk") && (
                        <circle
                          cx={x}
                          cy={getY(item.disk_usage)}
                          r={hoverIndex === idx ? "5" : "3.5"}
                          fill="#f39b13"
                          stroke="#ffffff"
                          strokeWidth="1.5"
                        />
                      )}
                    </g>
                  );
                })}

              {/* X-AXIS TIME LABELS */}
              {count > 0 &&
                [0, Math.floor(count / 4), Math.floor(count / 2), Math.floor((3 * count) / 4), count - 1]
                  .filter((v, i, a) => a.indexOf(v) === i)
                  .map((idx) => {
                    const item = sortedMetrics[idx];
                    if (!item) return null;
                    const x = getX(idx);
                    return (
                      <text
                        key={idx}
                        x={x}
                        y={height - 8}
                        textAnchor="middle"
                        fontSize="10"
                        fill="#64748b"
                        fontFamily="sans-serif"
                      >
                        {formatTimeLabel(item.recorded_at)}
                      </text>
                    );
                  })}

              {/* HOVER INTERACTIVE OVERLAY RECTS */}
              {sortedMetrics.map((_, idx) => {
                const step = chartWidth / (count > 1 ? count - 1 : 1);
                const rectWidth = Math.max(step, 16);
                const x = getX(idx) - rectWidth / 2;
                return (
                  <rect
                    key={idx}
                    x={x}
                    y={padding.top}
                    width={rectWidth}
                    height={chartHeight}
                    fill="transparent"
                    style={{ cursor: "pointer" }}
                    onMouseEnter={() => setHoverIndex(idx)}
                  />
                );
              })}

              {/* HOVER GUIDELINE & MARKER */}
              {hoverIndex !== null && sortedMetrics[hoverIndex] && (
                <line
                  x1={getX(hoverIndex)}
                  y1={padding.top}
                  x2={getX(hoverIndex)}
                  y2={padding.top + chartHeight}
                  stroke="#94a3b8"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
              )}
            </svg>

            {/* HOVER TOOLTIP CARD */}
            {hoveredItem && (
              <div
                style={{
                  position: "absolute",
                  top: "10px",
                  left: `${Math.min(
                    85,
                    Math.max(15, (getX(hoverIndex) / width) * 100)
                  )}%`,
                  transform: "translateX(-50%)",
                  background: "#1e293b",
                  color: "#ffffff",
                  padding: "8px 12px",
                  borderRadius: "6px",
                  fontSize: "11px",
                  boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
                  pointerEvents: "none",
                  zIndex: 10,
                  whiteSpace: "nowrap",
                }}
              >
                <div style={{ color: "#94a3b8", marginBottom: "4px" }}>
                  {formatFullDateTime(hoveredItem.recorded_at)}
                </div>
                <div style={{ display: "flex", gap: "12px" }}>
                  {(activeMetric === "all" || activeMetric === "cpu") && (
                    <span style={{ color: "#60a5fa" }}>
                      CPU: <b>{hoveredItem.cpu_usage.toFixed(1)}%</b>
                    </span>
                  )}
                  {(activeMetric === "all" || activeMetric === "ram") && (
                    <span style={{ color: "#4ade80" }}>
                      RAM: <b>{hoveredItem.ram_usage.toFixed(1)}%</b>
                    </span>
                  )}
                  {(activeMetric === "all" || activeMetric === "disk") && (
                    <span style={{ color: "#fbbf24" }}>
                      Disk: <b>{hoveredItem.disk_usage.toFixed(1)}%</b>
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default MetricChart;
