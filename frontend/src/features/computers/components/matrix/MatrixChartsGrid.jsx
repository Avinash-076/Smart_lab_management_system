import { useState, useId } from "react";
import Icon from "../../../../components/ui/Icon";
import "./MatrixChartsGrid.css";

function formatTime(isoStr) {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
  } catch {
    return "";
  }
}

function formatFullTime(isoStr) {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr);
    if (isNaN(d.getTime())) return "";
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "";
  }
}

function SingleMetricCard({
  title,
  icon,
  iconColor,
  currentVal,
  unit = "%",
  color,
  stats = {},
  points = [],
  dataKey = "cpu_usage",
  loading = false,
}) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const gradId = useId();

  const width = 360;
  const height = 140;
  const padLeft = 32;
  const padRight = 14;
  const padTop = 15;
  const padBottom = 25;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const validPoints = points.filter((p) => p && typeof p[dataKey] === "number" && !isNaN(p[dataKey]));
  const count = validPoints.length;

  let pathD = "";
  let areaD = "";
  const coords = [];

  if (count > 0) {
    const maxVal = 100;
    const minVal = 0;

    validPoints.forEach((p, idx) => {
      const x = padLeft + (count === 1 ? chartW / 2 : (idx / (count - 1)) * chartW);
      const val = Math.max(minVal, Math.min(maxVal, p[dataKey]));
      const y = padTop + chartH - ((val - minVal) / (maxVal - minVal)) * chartH;
      coords.push({ x, y, val: p[dataKey], timestamp: p.timestamp });
    });

    pathD = coords.reduce((acc, c, idx) => {
      if (idx === 0) return `M ${c.x} ${c.y}`;
      // Smooth cubic bezier curve
      const prev = coords[idx - 1];
      const cx1 = prev.x + (c.x - prev.x) / 2;
      const cy1 = prev.y;
      const cx2 = prev.x + (c.x - prev.x) / 2;
      const cy2 = c.y;
      return `${acc} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${c.x} ${c.y}`;
    }, "");

    if (coords.length > 0) {
      const first = coords[0];
      const last = coords[coords.length - 1];
      areaD = `${pathD} L ${last.x} ${padTop + chartH} L ${first.x} ${padTop + chartH} Z`;
    }
  }

  // Generate 4-5 X-axis labels
  const xLabels = [];
  if (count >= 2) {
    const step = Math.max(1, Math.floor((count - 1) / 4));
    for (let i = 0; i < count; i += step) {
      xLabels.push({
        x: padLeft + (i / (count - 1)) * chartW,
        text: formatTime(validPoints[i].timestamp),
      });
    }
    // Ensure the last timestamp is displayed if not already
    const lastIdx = count - 1;
    if (xLabels.length > 0 && Math.abs(xLabels[xLabels.length - 1].x - (padLeft + chartW)) > 30) {
      xLabels.push({
        x: padLeft + chartW,
        text: formatTime(validPoints[lastIdx].timestamp),
      });
    }
  } else if (count === 1) {
    xLabels.push({ x: padLeft + chartW / 2, text: formatTime(validPoints[0].timestamp) });
  }

  const activeCoord = hoverIndex !== null && coords[hoverIndex] ? coords[hoverIndex] : null;

  return (
    <div className="matrix-chart-card">
      <div className="chart-card-header">
        <div className="chart-title-box">
          <div className="chart-icon-wrap" style={{ color: iconColor }}>
            <Icon type={icon} size={18} />
          </div>
          <span className="chart-card-title">{title}</span>
        </div>
        <div className="chart-current-display">
          {currentVal !== null && currentVal !== undefined ? (
            <span className="current-stat-value">
              {currentVal}
              <span className="current-stat-unit">{unit}</span>
            </span>
          ) : (
            <span className="current-stat-empty">—</span>
          )}
        </div>
      </div>

      <div className="chart-svg-container">
        {loading ? (
          <div className="chart-loading-placeholder">
            <span className="chart-pulse-bar" />
          </div>
        ) : count === 0 ? (
          <div className="chart-empty-placeholder">
            <Icon type="pulse" size={24} />
            <span>No metrics recorded in this window</span>
          </div>
        ) : (
          <svg
            className="chart-svg"
            viewBox={`0 0 ${width} ${height}`}
            preserveAspectRatio="none"
            onMouseLeave={() => setHoverIndex(null)}
          >
            <defs>
              <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity="0.25" />
                <stop offset="90%" stopColor={color} stopOpacity="0.02" />
                <stop offset="100%" stopColor={color} stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Horizontal Grid lines */}
            {[0, 25, 50, 75, 100].map((tick) => {
              const y = padTop + chartH - (tick / 100) * chartH;
              return (
                <g key={tick} className="grid-line-group">
                  <line
                    x1={padLeft}
                    y1={y}
                    x2={width - padRight}
                    y2={y}
                    className="chart-grid-line"
                  />
                  <text
                    x={padLeft - 6}
                    y={y + 3}
                    className="chart-y-axis-label"
                    textAnchor="end"
                  >
                    {tick}
                  </text>
                </g>
              );
            })}

            {/* Area Fill */}
            {areaD && <path d={areaD} fill={`url(#${gradId})`} />}

            {/* Line Stroke */}
            {pathD && (
              <path
                d={pathD}
                fill="none"
                stroke={color}
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* X Axis Time Labels */}
            {xLabels.map((xl, i) => (
              <text
                key={i}
                x={xl.x}
                y={height - 6}
                className="chart-x-axis-label"
                textAnchor="middle"
              >
                {xl.text}
              </text>
            ))}

            {/* Interactive hover overlays */}
            {coords.map((c, idx) => (
              <rect
                key={idx}
                x={c.x - (count > 1 ? chartW / (count - 1) / 2 : 15)}
                y={padTop}
                width={count > 1 ? chartW / (count - 1) : 30}
                height={chartH}
                fill="transparent"
                style={{ cursor: "pointer" }}
                onMouseEnter={() => setHoverIndex(idx)}
              />
            ))}

            {/* Active hover crosshair and point */}
            {activeCoord && (
              <g className="chart-active-overlay">
                <line
                  x1={activeCoord.x}
                  y1={padTop}
                  x2={activeCoord.x}
                  y2={padTop + chartH}
                  className="chart-crosshair-line"
                  strokeDasharray="2 2"
                />
                <circle
                  cx={activeCoord.x}
                  cy={activeCoord.y}
                  r="4.5"
                  fill="#ffffff"
                  stroke={color}
                  strokeWidth="2.5"
                />
              </g>
            )}
          </svg>
        )}

        {/* Floating Tooltip */}
        {activeCoord && (
          <div
            className="chart-tooltip"
            style={{
              left: `${(activeCoord.x / width) * 100}%`,
              top: `${(activeCoord.y / height) * 100}%`,
            }}
          >
            <div className="tooltip-time">{formatFullTime(activeCoord.timestamp)}</div>
            <div className="tooltip-val" style={{ color }}>
              {activeCoord.val !== null ? `${activeCoord.val}${unit}` : "—"}
            </div>
          </div>
        )}
      </div>

      <div className="chart-card-stats-row">
        <div className="stat-column">
          <span className="stat-label">Current</span>
          <span className="stat-num">{stats.current !== null && stats.current !== undefined ? `${stats.current}%` : "—"}</span>
        </div>
        <div className="stat-column">
          <span className="stat-label">Average</span>
          <span className="stat-num">{stats.average !== null && stats.average !== undefined ? `${stats.average}%` : "—"}</span>
        </div>
        <div className="stat-column">
          <span className="stat-label">Maximum</span>
          <span className="stat-num">{stats.maximum !== null && stats.maximum !== undefined ? `${stats.maximum}%` : "—"}</span>
        </div>
        <div className="stat-column">
          <span className="stat-label">Minimum</span>
          <span className="stat-num">{stats.minimum !== null && stats.minimum !== undefined ? `${stats.minimum}%` : "—"}</span>
        </div>
      </div>
    </div>
  );
}

function NetworkMetricCard({
  currentDown,
  currentUp,
  points = [],
  loading = false,
}) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const downGradId = useId();
  const upGradId = useId();

  const width = 360;
  const height = 140;
  const padLeft = 32;
  const padRight = 14;
  const padTop = 15;
  const padBottom = 25;
  const chartW = width - padLeft - padRight;
  const chartH = height - padTop - padBottom;

  const validPoints = points.filter((p) => p && p.timestamp);
  const count = validPoints.length;

  // Determine scale max for Mbps (minimum 40 to match reference design)
  let maxMbps = 40;
  validPoints.forEach((p) => {
    if (typeof p.download_mbps === "number" && p.download_mbps > maxMbps) {
      maxMbps = Math.ceil(p.download_mbps / 10) * 10;
    }
    if (typeof p.upload_mbps === "number" && p.upload_mbps > maxMbps) {
      maxMbps = Math.ceil(p.upload_mbps / 10) * 10;
    }
  });

  const downCoords = [];
  const upCoords = [];

  if (count > 0) {
    validPoints.forEach((p, idx) => {
      const x = padLeft + (count === 1 ? chartW / 2 : (idx / (count - 1)) * chartW);
      const dVal = typeof p.download_mbps === "number" ? p.download_mbps : 0;
      const uVal = typeof p.upload_mbps === "number" ? p.upload_mbps : 0;

      const yDown = padTop + chartH - (dVal / maxMbps) * chartH;
      const yUp = padTop + chartH - (uVal / maxMbps) * chartH;

      downCoords.push({ x, y: yDown, val: p.download_mbps, timestamp: p.timestamp });
      upCoords.push({ x, y: yUp, val: p.upload_mbps, timestamp: p.timestamp });
    });
  }

  const buildPath = (coords) => {
    if (coords.length === 0) return "";
    return coords.reduce((acc, c, idx) => {
      if (idx === 0) return `M ${c.x} ${c.y}`;
      const prev = coords[idx - 1];
      const cx1 = prev.x + (c.x - prev.x) / 2;
      const cy1 = prev.y;
      const cx2 = prev.x + (c.x - prev.x) / 2;
      const cy2 = c.y;
      return `${acc} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${c.x} ${c.y}`;
    }, "");
  };

  const downPath = buildPath(downCoords);
  const upPath = buildPath(upCoords);

  const downArea =
    downCoords.length > 0
      ? `${downPath} L ${downCoords[downCoords.length - 1].x} ${padTop + chartH} L ${downCoords[0].x} ${padTop + chartH} Z`
      : "";
  const upArea =
    upCoords.length > 0
      ? `${upPath} L ${upCoords[upCoords.length - 1].x} ${padTop + chartH} L ${upCoords[0].x} ${padTop + chartH} Z`
      : "";

  const xLabels = [];
  if (count >= 2) {
    const step = Math.max(1, Math.floor((count - 1) / 4));
    for (let i = 0; i < count; i += step) {
      xLabels.push({
        x: padLeft + (i / (count - 1)) * chartW,
        text: formatTime(validPoints[i].timestamp),
      });
    }
    const lastIdx = count - 1;
    if (xLabels.length > 0 && Math.abs(xLabels[xLabels.length - 1].x - (padLeft + chartW)) > 30) {
      xLabels.push({
        x: padLeft + chartW,
        text: formatTime(validPoints[lastIdx].timestamp),
      });
    }
  } else if (count === 1) {
    xLabels.push({ x: padLeft + chartW / 2, text: formatTime(validPoints[0].timestamp) });
  }

  const activeDown = hoverIndex !== null && downCoords[hoverIndex] ? downCoords[hoverIndex] : null;
  const activeUp = hoverIndex !== null && upCoords[hoverIndex] ? upCoords[hoverIndex] : null;

  return (
    <div className="matrix-chart-card">
      <div className="chart-card-header">
        <div className="chart-title-box">
          <div className="chart-icon-wrap" style={{ color: "#8b5cf6" }}>
            <Icon type="network" size={18} />
          </div>
          <span className="chart-card-title">Network Usage (Mbps)</span>
        </div>
        <div className="chart-legend-row">
          <span className="legend-item">
            <span className="legend-box download-box" />
            Download
          </span>
          <span className="legend-item">
            <span className="legend-box upload-box" />
            Upload
          </span>
        </div>
      </div>

      <div className="chart-svg-container">
        {loading ? (
          <div className="chart-loading-placeholder">
            <span className="chart-pulse-bar" />
          </div>
        ) : count === 0 ? (
          <div className="chart-empty-placeholder">
            <Icon type="network" size={24} />
            <span>No network metrics in this window</span>
          </div>
        ) : (
          <svg
            className="chart-svg"
            viewBox={`0 0 ${width} ${height}`}
            preserveAspectRatio="none"
            onMouseLeave={() => setHoverIndex(null)}
          >
            <defs>
              <linearGradient id={downGradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2563eb" stopOpacity="0.22" />
                <stop offset="90%" stopColor="#2563eb" stopOpacity="0.02" />
                <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
              </linearGradient>
              <linearGradient id={upGradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.22" />
                <stop offset="90%" stopColor="#8b5cf6" stopOpacity="0.02" />
                <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.0" />
              </linearGradient>
            </defs>

            {/* Grid Lines */}
            {[0, Math.round(maxMbps * 0.25), Math.round(maxMbps * 0.5), Math.round(maxMbps * 0.75), maxMbps].map(
              (tick, i) => {
                const y = padTop + chartH - (tick / maxMbps) * chartH;
                return (
                  <g key={i} className="grid-line-group">
                    <line
                      x1={padLeft}
                      y1={y}
                      x2={width - padRight}
                      y2={y}
                      className="chart-grid-line"
                    />
                    <text
                      x={padLeft - 6}
                      y={y + 3}
                      className="chart-y-axis-label"
                      textAnchor="end"
                    >
                      {tick}
                    </text>
                  </g>
                );
              }
            )}

            {/* Area Fills */}
            {downArea && <path d={downArea} fill={`url(#${downGradId})`} />}
            {upArea && <path d={upArea} fill={`url(#${upGradId})`} />}

            {/* Lines */}
            {downPath && (
              <path
                d={downPath}
                fill="none"
                stroke="#2563eb"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}
            {upPath && (
              <path
                d={upPath}
                fill="none"
                stroke="#8b5cf6"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* X Labels */}
            {xLabels.map((xl, i) => (
              <text
                key={i}
                x={xl.x}
                y={height - 6}
                className="chart-x-axis-label"
                textAnchor="middle"
              >
                {xl.text}
              </text>
            ))}

            {/* Overlays */}
            {downCoords.map((c, idx) => (
              <rect
                key={idx}
                x={c.x - (count > 1 ? chartW / (count - 1) / 2 : 15)}
                y={padTop}
                width={count > 1 ? chartW / (count - 1) : 30}
                height={chartH}
                fill="transparent"
                style={{ cursor: "pointer" }}
                onMouseEnter={() => setHoverIndex(idx)}
              />
            ))}

            {/* Active hover crosshair */}
            {activeDown && (
              <g className="chart-active-overlay">
                <line
                  x1={activeDown.x}
                  y1={padTop}
                  x2={activeDown.x}
                  y2={padTop + chartH}
                  className="chart-crosshair-line"
                  strokeDasharray="2 2"
                />
                <circle
                  cx={activeDown.x}
                  cy={activeDown.y}
                  r="4"
                  fill="#ffffff"
                  stroke="#2563eb"
                  strokeWidth="2"
                />
                {activeUp && (
                  <circle
                    cx={activeUp.x}
                    cy={activeUp.y}
                    r="4"
                    fill="#ffffff"
                    stroke="#8b5cf6"
                    strokeWidth="2"
                  />
                )}
              </g>
            )}
          </svg>
        )}

        {/* Floating Tooltip */}
        {activeDown && (
          <div
            className="chart-tooltip"
            style={{
              left: `${(activeDown.x / width) * 100}%`,
              top: `${(activeDown.y / height) * 100}%`,
            }}
          >
            <div className="tooltip-time">{formatFullTime(activeDown.timestamp)}</div>
            <div className="tooltip-val" style={{ color: "#2563eb" }}>
              Down: {activeDown.val !== null && activeDown.val !== undefined ? `${activeDown.val} Mbps` : "0.0 Mbps"}
            </div>
            {activeUp && (
              <div className="tooltip-val" style={{ color: "#8b5cf6" }}>
                Up: {activeUp.val !== null && activeUp.val !== undefined ? `${activeUp.val} Mbps` : "0.0 Mbps"}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="chart-card-stats-row network-stats-row">
        <div className="stat-column">
          <span className="stat-label">Down</span>
          <span className="stat-num network-down-text">
            {currentDown !== null && currentDown !== undefined ? `${currentDown} Mbps` : "—"}
          </span>
        </div>
        <div className="stat-column">
          <span className="stat-label">Up</span>
          <span className="stat-num network-up-text">
            {currentUp !== null && currentUp !== undefined ? `${currentUp} Mbps` : "—"}
          </span>
        </div>
      </div>
    </div>
  );
}

function MatrixChartsGrid({
  summary = null,
  timeSeries = [],
  loading = false,
}) {
  const cpuStats = summary?.cpu || {};
  const memStats = summary?.memory || {};
  const diskStats = summary?.disk || {};
  const netStats = summary?.network || {};

  return (
    <div className="matrix-charts-grid">
      <SingleMetricCard
        title="CPU Usage (%)"
        icon="cpu"
        iconColor="#2563eb"
        color="#2563eb"
        currentVal={cpuStats.current}
        stats={cpuStats}
        points={timeSeries}
        dataKey="cpu_usage"
        loading={loading}
      />

      <SingleMetricCard
        title="Memory Usage (%)"
        icon="ram"
        iconColor="#10b981"
        color="#10b981"
        currentVal={memStats.current}
        stats={memStats}
        points={timeSeries}
        dataKey="ram_usage"
        loading={loading}
      />

      <SingleMetricCard
        title="Disk Usage (%)"
        icon="disk"
        iconColor="#f59e0b"
        color="#f59e0b"
        currentVal={diskStats.current}
        stats={diskStats}
        points={timeSeries}
        dataKey="disk_usage"
        loading={loading}
      />

      <NetworkMetricCard
        currentDown={netStats.current_download_mbps}
        currentUp={netStats.current_upload_mbps}
        points={timeSeries}
        loading={loading}
      />
    </div>
  );
}

export default MatrixChartsGrid;
