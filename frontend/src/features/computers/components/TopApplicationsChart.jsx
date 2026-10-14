import { useState } from "react";
import "./TopApplicationsChart.css";

const PALETTE = [
  "#1877f2", // Blue (chrome.exe / 1st)
  "#06b6d4", // Sky (Code.exe / 2nd)
  "#10b981", // Emerald (msedge.exe / 3rd)
  "#8b5cf6", // Purple (explorer.exe / 4th)
  "#94a3b8", // Slate (Others)
  "#f59e0b", // Amber (Fallback)
  "#ec4899", // Rose (Fallback)
];

function TopApplicationsChart({
  topApps = [],
  totalActiveFormatted = "0m",
  totalActiveSeconds = 0,
  isLoading = false,
  error = "",
}) {
  const [hoveredIdx, setHoveredIdx] = useState(null);

  // SVG parameters
  const size = 200;
  const strokeWidth = 26;
  const radius = (size - strokeWidth) / 2;
  const center = size / 2;
  const circumference = 2 * Math.PI * radius;

  // Compute donut segments
  const totalVal = topApps.reduce((acc, curr) => acc + (curr.duration_seconds || 0), 0);

  const segments = topApps.reduce(
    (acc, app, idx) => {
      const duration = app.duration_seconds || 0;
      const percent = totalVal > 0 ? duration / totalVal : 0;
      const strokeDasharray = `${percent * circumference} ${circumference}`;
      const strokeDashoffset = -acc.accumulated * circumference;

      const color =
        app.process_name?.toLowerCase() === "others"
          ? "#94a3b8"
          : PALETTE[idx % PALETTE.length];

      const displayPercent =
        typeof app.percentage === "number"
          ? Math.round(app.percentage)
          : Math.round(percent * 100);

      acc.list.push({
        ...app,
        color,
        percent: displayPercent,
        strokeDasharray,
        strokeDashoffset,
      });

      return {
        list: acc.list,
        accumulated: acc.accumulated + percent,
      };
    },
    { list: [], accumulated: 0 }
  ).list;

  return (
    <div className="history-card top-apps-card">
      <div className="history-card-header">
        <div className="history-card-title-group">
          <div className="history-card-icon-box">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#1877f2"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <h3 className="history-card-title">Top Applications by Usage Time</h3>
        </div>
      </div>

      <div className="history-card-body top-apps-body">
        {isLoading ? (
          <div className="history-chart-state">
            <div className="history-spinner" />
            <p>Loading top applications...</p>
          </div>
        ) : error ? (
          <div className="history-chart-state error">
            <p>{error}</p>
          </div>
        ) : topApps.length === 0 || totalActiveSeconds === 0 ? (
          <div className="history-chart-state">
            <p>No application usage recorded.</p>
          </div>
        ) : (
          <div className="donut-content-layout">
            {/* Donut Chart SVG */}
            <div className="donut-chart-wrapper">
              <svg
                width={size}
                height={size}
                viewBox={`0 0 ${size} ${size}`}
                className="donut-svg"
              >
                {/* Background Track */}
                <circle
                  cx={center}
                  cy={center}
                  r={radius}
                  fill="transparent"
                  stroke="#f1f5f9"
                  strokeWidth={strokeWidth}
                />

                {/* Slices */}
                {segments.map((seg, idx) => (
                  <circle
                    key={seg.process_name || idx}
                    cx={center}
                    cy={center}
                    r={radius}
                    fill="transparent"
                    stroke={seg.color}
                    strokeWidth={hoveredIdx === idx ? strokeWidth + 3 : strokeWidth}
                    strokeDasharray={seg.strokeDasharray}
                    strokeDashoffset={seg.strokeDashoffset}
                    transform={`rotate(-90 ${center} ${center})`}
                    className="donut-slice"
                    onMouseEnter={() => setHoveredIdx(idx)}
                    onMouseLeave={() => setHoveredIdx(null)}
                  />
                ))}
              </svg>

              {/* Centered Total Active Time */}
              <div className="donut-center-info">
                <span className="donut-center-time">{totalActiveFormatted}</span>
                <span className="donut-center-label">Total</span>
              </div>
            </div>

            {/* Legend List */}
            <div className="donut-legend">
              {segments.map((seg, idx) => (
                <div
                  key={seg.process_name || idx}
                  className={`legend-item ${hoveredIdx === idx ? "hovered" : ""}`}
                  onMouseEnter={() => setHoveredIdx(idx)}
                  onMouseLeave={() => setHoveredIdx(null)}
                >
                  <div className="legend-left">
                    <span
                      className="legend-color-dot"
                      style={{ backgroundColor: seg.color }}
                    />
                    <span className="legend-proc-name" title={seg.process_name}>
                      {seg.process_name || seg.application_name}
                    </span>
                  </div>
                  <div className="legend-right">
                    <span className="legend-duration">
                      {seg.formatted_duration || `${Math.round((seg.duration_seconds || 0) / 60)}m`}
                    </span>
                    <span className="legend-percent">{`(${seg.percent}%)`}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default TopApplicationsChart;
