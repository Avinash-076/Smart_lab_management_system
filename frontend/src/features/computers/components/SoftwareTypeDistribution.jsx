import { useState, useMemo } from "react";
import "./SoftwareTypeDistribution.css";

const CATEGORY_COLORS = {
  "System Utilities": "#0284c7",       // Sky/cyan blue
  "Web Browsers": "#2563eb",           // Blue
  "Development": "#f59e0b",            // Amber/orange
  "Multimedia": "#a855f7",             // Purple
  "Office & Productivity": "#ec4899",  // Pink/magenta
  "Security": "#10b981",               // Emerald green
  "Others": "#64748b",                 // Slate grey
  "Uncategorized": "#94a3b8",          // Muted slate
};

export default function SoftwareTypeDistribution({
  categories = [],
  totalApplications = 0,
  loading = false,
}) {
  const [hoveredCategory, setHoveredCategory] = useState(null);

  // Compute donut segments
  const { segments, totalCount } = useMemo(() => {
    const validCats = Array.isArray(categories) ? categories.filter((c) => c && c.count > 0) : [];
    const count = totalApplications > 0 ? totalApplications : validCats.reduce((acc, c) => acc + c.count, 0);

    const radius = 64;
    const circumference = 2 * Math.PI * radius;
    const segs = [];
    let accumulatedAngle = 0;

    for (let i = 0; i < validCats.length; i += 1) {
      const cat = validCats[i];
      const percentage = count > 0 ? (cat.count / count) : 0;
      const strokeDasharray = `${percentage * circumference} ${circumference}`;
      const strokeDashoffset = -accumulatedAngle * circumference;
      accumulatedAngle += percentage;

      const color = CATEGORY_COLORS[cat.category] || "#64748b";

      segs.push({
        ...cat,
        color,
        strokeDasharray,
        strokeDashoffset,
        percentageDisplay: cat.percentage ?? Math.round(percentage * 100),
      });
    }

    return { segments: segs, totalCount: count };
  }, [categories, totalApplications]);

  return (
    <div className="software-analytics-card software-type-card">
      <div className="analytics-card-header">
        <div className="analytics-card-title-group">
          <div className="analytics-icon-badge">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
          </div>
          <h3 className="analytics-card-title">Software Type Distribution</h3>
        </div>
      </div>

      <div className="software-type-content">
        {/* Donut Chart */}
        <div className="software-donut-wrapper">
          <svg
            viewBox="0 0 180 180"
            className="software-donut-svg"
            aria-label="Software Category Distribution Chart"
          >
            {/* Background empty track */}
            <circle
              cx="90"
              cy="90"
              r="64"
              fill="transparent"
              stroke="#f1f5f9"
              strokeWidth="24"
            />

            {/* Slices */}
            {segments.map((seg) => {
              const isHovered = hoveredCategory === seg.category;
              return (
                <circle
                  key={seg.category}
                  cx="90"
                  cy="90"
                  r="64"
                  fill="transparent"
                  stroke={seg.color}
                  strokeWidth={isHovered ? "28" : "24"}
                  strokeDasharray={seg.strokeDasharray}
                  strokeDashoffset={seg.strokeDashoffset}
                  transform="rotate(-90 90 90)"
                  className="software-donut-slice"
                  onMouseEnter={() => setHoveredCategory(seg.category)}
                  onMouseLeave={() => setHoveredCategory(null)}
                  style={{
                    transition: "stroke-width 0.2s ease, opacity 0.2s ease",
                    opacity: hoveredCategory && !isHovered ? 0.45 : 1,
                  }}
                />
              );
            })}
          </svg>

          {/* Centered Donut Text */}
          <div className="software-donut-center">
            <span className="donut-center-count">
              {loading && totalCount === 0 ? "—" : totalCount}
            </span>
            <span className="donut-center-label">Applications</span>
          </div>
        </div>

        {/* Legend List */}
        <div className="software-type-legend">
          {segments.length === 0 ? (
            <div className="software-legend-empty">
              {loading ? "Calculating distribution..." : "No application categories"}
            </div>
          ) : (
            segments.map((seg) => {
              const isHovered = hoveredCategory === seg.category;
              return (
                <div
                  key={seg.category}
                  className={`software-legend-item ${isHovered ? "highlighted" : ""}`}
                  onMouseEnter={() => setHoveredCategory(seg.category)}
                  onMouseLeave={() => setHoveredCategory(null)}
                >
                  <div className="legend-item-left">
                    <span
                      className="legend-color-dot"
                      style={{ backgroundColor: seg.color }}
                    />
                    <span className="legend-category-name">{seg.category}</span>
                  </div>
                  <div className="legend-item-right">
                    <span className="legend-count">{seg.count}</span>
                    <span className="legend-percentage">({seg.percentageDisplay}%)</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
