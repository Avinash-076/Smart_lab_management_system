import { useState } from "react";
import "./ApplicationUsageTrend.css";

function ApplicationUsageTrend({
  intervals = [],
  totalActiveFormatted = "0m",
  isLoading = false,
  error = "",
}) {
  const [hoveredBar, setHoveredBar] = useState(null);

  // SVG dimensions & padding
  const svgWidth = 640;
  const svgHeight = 220;
  const paddingLeft = 46;
  const paddingRight = 20;
  const paddingTop = 25;
  const paddingBottom = 32;

  const chartWidth = svgWidth - paddingLeft - paddingRight;
  const chartHeight = svgHeight - paddingTop - paddingBottom;

  // Max value for Y-axis (at least 60m to match the 0m-15m-30m-45m-60m scale in reference)
  const maxDataVal = Math.max(
    60,
    ...intervals.map((item) => item.duration_minutes || 0)
  );
  // Round up to nearest 60 if exceeds 60
  const yMax = maxDataVal <= 60 ? 60 : Math.ceil(maxDataVal / 60) * 60;
  const yTicks = [
    { label: `${yMax}m`, val: yMax },
    { label: `${Math.round((yMax * 3) / 4)}m`, val: (yMax * 3) / 4 },
    { label: `${Math.round(yMax / 2)}m`, val: yMax / 2 },
    { label: `${Math.round(yMax / 4)}m`, val: yMax / 4 },
    { label: "0m", val: 0 },
  ];

  const barCount = intervals.length || 9;
  const totalSlots = Math.max(barCount, 1);
  const slotWidth = chartWidth / totalSlots;
  const barWidth = Math.min(24, Math.max(12, slotWidth * 0.55));

  return (
    <div className="history-card usage-trend-card">
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
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
          </div>
          <h3 className="history-card-title">Application Usage Trend</h3>
        </div>
        <div className="history-card-stat">
          <span className="history-stat-label">Total Active Time:</span>{" "}
          <strong className="history-stat-value">{totalActiveFormatted}</strong>
        </div>
      </div>

      <div className="history-card-body trend-chart-container">
        {isLoading ? (
          <div className="history-chart-state">
            <div className="history-spinner" />
            <p>Loading usage trend...</p>
          </div>
        ) : error ? (
          <div className="history-chart-state error">
            <p>{error}</p>
          </div>
        ) : intervals.length === 0 ? (
          <div className="history-chart-state">
            <p>No usage recorded for this period.</p>
          </div>
        ) : (
          <div className="svg-responsive-wrapper">
            <svg
              viewBox={`0 0 ${svgWidth} ${svgHeight}`}
              className="trend-svg"
              preserveAspectRatio="xMidYMid meet"
            >
              {/* Horizontal Grid lines and Y labels */}
              {yTicks.map((tick) => {
                const yPos =
                  paddingTop +
                  chartHeight -
                  (tick.val / yMax) * chartHeight;
                return (
                  <g key={tick.label} className="grid-tick-group">
                    <line
                      x1={paddingLeft}
                      y1={yPos}
                      x2={svgWidth - paddingRight}
                      y2={yPos}
                      stroke="#e9eef5"
                      strokeDasharray={tick.val === 0 ? "none" : "3 3"}
                      strokeWidth={1}
                    />
                    <text
                      x={paddingLeft - 8}
                      y={yPos + 4}
                      textAnchor="end"
                      className="y-axis-label"
                    >
                      {tick.label}
                    </text>
                  </g>
                );
              })}

              {/* Bars */}
              {intervals.map((item, idx) => {
                const duration = item.duration_minutes || 0;
                const barHeight = Math.max(
                  0,
                  (duration / yMax) * chartHeight
                );
                const xCenter = paddingLeft + (idx + 0.5) * slotWidth;
                const xPos = xCenter - barWidth / 2;
                const yPos = paddingTop + chartHeight - barHeight;

                const isHovered = hoveredBar === idx;

                return (
                  <g
                    key={item.label || idx}
                    className="bar-group"
                    onMouseEnter={() => setHoveredBar(idx)}
                    onMouseLeave={() => setHoveredBar(null)}
                  >
                    {/* Invisible wider target for easier hover */}
                    <rect
                      x={xCenter - slotWidth / 2}
                      y={paddingTop}
                      width={slotWidth}
                      height={chartHeight}
                      fill="transparent"
                      cursor="pointer"
                    />

                    {/* Visible Bar */}
                    <rect
                      x={xPos}
                      y={barHeight > 0 ? yPos : paddingTop + chartHeight - 1}
                      width={barWidth}
                      height={Math.max(barHeight, 2)}
                      rx="3"
                      ry="3"
                      fill={isHovered ? "#1d4ed8" : "#3b82f6"}
                      className="chart-bar"
                    />

                    {/* X-axis label */}
                    <text
                      x={xCenter}
                      y={paddingTop + chartHeight + 18}
                      textAnchor="middle"
                      className="x-axis-label"
                    >
                      {item.label}
                    </text>
                  </g>
                );
              })}
            </svg>

            {/* Hover Tooltip */}
            {hoveredBar !== null && intervals[hoveredBar] && (
              <div
                className="trend-tooltip"
                style={{
                  left: `${
                    ((paddingLeft + (hoveredBar + 0.5) * slotWidth) /
                      svgWidth) *
                    100
                  }%`,
                  bottom: `${
                    (((intervals[hoveredBar].duration_minutes || 0) / yMax) *
                      chartHeight +
                      paddingBottom +
                      10) *
                    (100 / svgHeight)
                  }%`,
                }}
              >
                <div className="tooltip-title">{intervals[hoveredBar].label}</div>
                <div className="tooltip-val">
                  Active:{" "}
                  <strong>
                    {intervals[hoveredBar].duration_minutes < 60
                      ? `${intervals[hoveredBar].duration_minutes}m`
                      : `${Math.floor(
                          intervals[hoveredBar].duration_minutes / 60
                        )}h ${
                          intervals[hoveredBar].duration_minutes % 60
                        }m`}
                  </strong>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default ApplicationUsageTrend;
