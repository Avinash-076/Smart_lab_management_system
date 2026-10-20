import "./ResourceUsageCard.css";

function CircularProgress({ value = 0, label = "", color = "#2563eb", unit = "%" }) {
  const radius = 35;
  const circumference = 2 * Math.PI * radius;
  const safeVal = Math.min(100, Math.max(0, parseFloat(value) || 0));
  const strokeDashoffset = circumference - (safeVal / 100) * circumference;

  return (
    <div className="resource-circular-item">
      <div className="resource-circular-gauge">
        <svg viewBox="0 0 86 86" className="resource-gauge-svg">
          {/* Background circle track */}
          <circle
            cx="43"
            cy="43"
            r={radius}
            fill="transparent"
            stroke="#f1f5f9"
            strokeWidth="7.5"
          />
          {/* Progress circle */}
          <circle
            cx="43"
            cy="43"
            r={radius}
            fill="transparent"
            stroke={color}
            strokeWidth="7.5"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            transform="rotate(-90 43 43)"
            style={{ transition: "stroke-dashoffset 0.5s ease" }}
          />
        </svg>
        <div className="resource-gauge-content">
          <span className="resource-gauge-value">
            {`${Math.round(safeVal)}${unit}`}
          </span>
          <span className="resource-gauge-sub">Average</span>
        </div>
      </div>
      <span className="resource-circular-label">{label}</span>
    </div>
  );
}

export default function ResourceUsageCard({
  avgCpu = 0,
  avgRam = 0,
  avgDisk = 0,
  timeline = [],
  computers = [],
  selectedSystemId = "all",
  onSelectSystem,
}) {
  // Generate SVG area chart points from timeline samples
  const width = 400;
  const height = 70;

  const validTimeline = Array.isArray(timeline) && timeline.length > 0 ? timeline : [];

  // Generate smooth cubic or polyline path for timeline
  let linePath;
  let areaPath;

  if (validTimeline.length > 1) {
    const pts = validTimeline.map((item, idx) => {
      const x = (idx / (validTimeline.length - 1)) * width;
      const rawVal = parseFloat(item.avg_cpu) || 0;
      const val = Math.min(100, Math.max(0, rawVal));
      const y = height - 10 - (val / 100) * (height - 22);
      return { x, y };
    });

    // Build smooth cubic Bezier spline
    linePath = `M ${pts[0].x} ${pts[0].y}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[i];
      const p1 = pts[i + 1];
      const cx1 = p0.x + (p1.x - p0.x) / 2;
      const cy1 = p0.y;
      const cx2 = p0.x + (p1.x - p0.x) / 2;
      const cy2 = p1.y;
      linePath += ` C ${cx1} ${cy1}, ${cx2} ${cy2}, ${p1.x} ${p1.y}`;
    }

    areaPath = `${linePath} L ${pts[pts.length - 1].x} ${height} L ${pts[0].x} ${height} Z`;
  } else {
    // Elegant smooth double-hump wave matching reference aesthetic
    linePath = `M 0 46 C 70 32, 110 50, 160 38 C 220 24, 280 48, 340 32 C 370 24, 390 35, 400 30`;
    areaPath = `${linePath} L 400 ${height} L 0 ${height} Z`;
  }

  return (
    <div className="resource-usage-card" data-testid="resource-usage-card">
      {/* Header */}
      <div className="resource-usage-header">
        <div className="resource-usage-title-group">
          <div className="resource-usage-badge-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 20V10" />
              <path d="M12 20V4" />
              <path d="M6 20v-6" />
            </svg>
          </div>
          <h3 className="resource-usage-title">Resource Usage Summary</h3>
        </div>

        {/* System dropdown */}
        <div className="resource-system-select-wrap">
          <select
            className="resource-system-select"
            value={selectedSystemId}
            onChange={(e) => onSelectSystem?.(e.target.value)}
            aria-label="Filter resource usage by computer"
          >
            <option value="all">All Systems</option>
            {computers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.hostname || `PC-${c.id}`}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Middle: 3 Circular Gauges */}
      <div className="resource-gauges-row">
        <CircularProgress
          value={avgCpu}
          label="CPU Usage"
          color="#2563eb"
        />
        <CircularProgress
          value={avgRam}
          label="RAM Usage"
          color="#10b981"
        />
        <CircularProgress
          value={avgDisk}
          label="Disk Usage"
          color="#8b5cf6"
        />
      </div>

      {/* Bottom: Smooth Area Trend Chart */}
      <div className="resource-trend-section">
        <div className="resource-trend-svg-wrap">
          <svg
            viewBox={`0 0 ${width} ${height}`}
            className="resource-trend-svg"
            preserveAspectRatio="none"
          >
            <defs>
              <linearGradient id="resourceAreaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2563eb" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
              </linearGradient>
            </defs>
            {/* Shaded Area */}
            <path d={areaPath} fill="url(#resourceAreaGrad)" />
            {/* Curved Line */}
            <path
              d={linePath}
              fill="none"
              stroke="#2563eb"
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
        <span className="resource-trend-caption">
          Real-time usage trends across all systems
        </span>
      </div>
    </div>
  );
}
