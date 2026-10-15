import { useState, useMemo } from "react";
import "./ProcessStatusDistribution.css";

const STATUS_COLORS = {
  Running: "#0962df",          // Blue
  Suspended: "#38bdf8",        // Cyan
  "Not Responding": "#ef4444", // Red
  Zombie: "#a855f7",           // Purple
  Others: "#f59e0b",           // Amber
};

export default function ProcessStatusDistribution({
  distribution = [],
  totalProcesses = 0,
  loading = false,
}) {
  const [hoveredStatus, setHoveredStatus] = useState(null);

  // Compute donut segments
  const { segments, totalCount } = useMemo(() => {
    const validItems = Array.isArray(distribution)
      ? distribution.filter((d) => d && d.count > 0)
      : [];
    const count =
      totalProcesses > 0
        ? totalProcesses
        : validItems.reduce((acc, d) => acc + d.count, 0);

    const radius = 64;
    const circumference = 2 * Math.PI * radius;
    const segs = [];
    let accumulatedAngle = 0;

    for (let i = 0; i < validItems.length; i += 1) {
      const item = validItems[i];
      const percentage = count > 0 ? item.count / count : 0;
      const strokeDasharray = `${percentage * circumference} ${circumference}`;
      const strokeDashoffset = -accumulatedAngle * circumference;
      accumulatedAngle += percentage;

      const color = STATUS_COLORS[item.status] || "#64748b";

      segs.push({
        ...item,
        color,
        strokeDasharray,
        strokeDashoffset,
        percentageDisplay: item.percentage ?? Math.round(percentage * 100),
      });
    }

    return { segments: segs, totalCount: count };
  }, [distribution, totalProcesses]);

  // All 5 canonical items for the legend
  const legendItems = useMemo(() => {
    const defaultStatuses = ["Running", "Suspended", "Not Responding", "Zombie", "Others"];
    const map = new Map();
    (distribution || []).forEach((d) => {
      if (d?.status) map.set(d.status, d);
    });

    return defaultStatuses.map((name) => {
      const match = map.get(name);
      const count = match ? match.count : 0;
      const pct =
        match?.percentage !== undefined
          ? match.percentage
          : totalCount > 0
          ? Math.round((count / totalCount) * 100)
          : 0;
      return {
        name,
        color: STATUS_COLORS[name] || "#64748b",
        count,
        percentage: pct,
      };
    });
  }, [distribution, totalCount]);

  return (
    <div className="process-analytics-card process-status-card">
      <div className="process-analytics-card-header">
        <div className="process-analytics-title-group">
          <div className="process-analytics-icon-badge">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </div>
          <h3 className="process-analytics-title">Process Status Distribution</h3>
        </div>
      </div>

      <div className="process-status-content">
        {/* Donut Chart */}
        <div className="process-donut-wrapper">
          <svg
            viewBox="0 0 180 180"
            className="process-donut-svg"
            aria-label="Process Status Distribution Donut Chart"
          >
            {/* Background track */}
            <circle
              cx="90"
              cy="90"
              r="64"
              fill="transparent"
              stroke="#f1f5f9"
              strokeWidth="24"
            />

            {/* Segments */}
            {segments.map((seg) => {
              const isHovered = hoveredStatus === seg.status;
              return (
                <circle
                  key={seg.status}
                  cx="90"
                  cy="90"
                  r="64"
                  fill="transparent"
                  stroke={seg.color}
                  strokeWidth={isHovered ? "28" : "24"}
                  strokeDasharray={seg.strokeDasharray}
                  strokeDashoffset={seg.strokeDashoffset}
                  transform="rotate(-90 90 90)"
                  className="process-donut-slice"
                  onMouseEnter={() => setHoveredStatus(seg.status)}
                  onMouseLeave={() => setHoveredStatus(null)}
                />
              );
            })}
          </svg>

          {/* Center total */}
          <div className="process-donut-center-label">
            <span className="process-donut-center-number">
              {loading && totalCount === 0 ? "—" : totalCount}
            </span>
            <span className="process-donut-center-sub">Processes</span>
          </div>
        </div>

        {/* Legend List */}
        <div className="process-status-legend">
          {legendItems.map((item) => (
            <div
              key={item.name}
              className={`process-legend-row ${
                hoveredStatus === item.name ? "hovered" : ""
              }`}
              onMouseEnter={() => setHoveredStatus(item.name)}
              onMouseLeave={() => setHoveredStatus(null)}
            >
              <div className="process-legend-name-group">
                <span
                  className="process-legend-color-dot"
                  style={{ backgroundColor: item.color }}
                />
                <span className="process-legend-status-name">{item.name}</span>
              </div>
              <div className="process-legend-stats">
                <span className="process-legend-count">
                  {item.count}{" "}
                  <span className="process-legend-pct">
                    ({Math.round(item.percentage)}%)
                  </span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
