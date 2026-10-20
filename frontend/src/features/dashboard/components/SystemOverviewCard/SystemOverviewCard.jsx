import "./SystemOverviewCard.css";

export default function SystemOverviewCard({
  totalComputers = 0,
  onlineComputers = 0,
  offlineComputers = 0,
  highRamCount = 0,
  lowDiskCount = 0,
  onViewAll,
}) {
  // Calculations
  const onlinePct =
    totalComputers > 0
      ? ((onlineComputers / totalComputers) * 100).toFixed(1)
      : "0.0";
  const offlinePct =
    totalComputers > 0
      ? ((offlineComputers / totalComputers) * 100).toFixed(1)
      : "0.0";
  const highRamPct =
    totalComputers > 0
      ? ((highRamCount / totalComputers) * 100).toFixed(1)
      : "0.0";
  const lowDiskPct =
    totalComputers > 0
      ? ((lowDiskCount / totalComputers) * 100).toFixed(1)
      : "0.0";

  // Compute SVG Donut Chart Slices
  // Radius: 54, Circumference: 2 * PI * 54 ~= 339.29
  const radius = 54;
  const circumference = 2 * Math.PI * radius;

  // We assign segments proportionally to the components:
  // For visual representation, if totalComputers === 0, show neutral ring
  const segmentsData = [
    { label: "Online", count: onlineComputers, color: "#10b981" },
    { label: "Offline", count: offlineComputers, color: "#ef4444" },
    { label: "High RAM Usage", count: highRamCount, color: "#f97316" },
    { label: "Low Disk Space", count: lowDiskCount, color: "#8b5cf6" },
  ];

  const sumCounts = segmentsData.reduce((acc, curr) => acc + curr.count, 0) || 1;

  const donutSlices = segmentsData.map((seg, idx) => {
    const fraction = totalComputers > 0 ? seg.count / sumCounts : 0;
    const strokeDasharray = `${fraction * circumference} ${circumference}`;
    const priorFraction = segmentsData
      .slice(0, idx)
      .reduce((acc, s) => acc + (totalComputers > 0 ? s.count / sumCounts : 0), 0);
    const strokeDashoffset = -(priorFraction * circumference);

    return {
      ...seg,
      strokeDasharray,
      strokeDashoffset,
    };
  });

  return (
    <div className="system-overview-card" data-testid="system-overview-card">
      {/* Header */}
      <div className="system-overview-header">
        <div className="system-overview-title-group">
          <div className="system-overview-badge-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
          </div>
          <h3 className="system-overview-title">System Overview</h3>
        </div>
        <button
          type="button"
          className="system-overview-view-all"
          onClick={onViewAll}
        >
          View All
        </button>
      </div>

      {/* Content: Donut + Breakdown */}
      <div className="system-overview-content">
        {/* Left: SVG Donut */}
        <div className="system-overview-donut-wrap">
          <svg className="system-overview-donut-svg" viewBox="0 0 150 150">
            {/* Background circle track */}
            <circle
              cx="75"
              cy="75"
              r={radius}
              fill="transparent"
              stroke="#f1f5f9"
              strokeWidth="16"
            />
            {/* Colored segments */}
            {donutSlices.map((slice, i) => (
              <circle
                key={i}
                cx="75"
                cy="75"
                r={radius}
                fill="transparent"
                stroke={slice.color}
                strokeWidth="16"
                strokeDasharray={slice.strokeDasharray}
                strokeDashoffset={slice.strokeDashoffset}
                strokeLinecap="round"
                transform="rotate(-90 75 75)"
              />
            ))}
          </svg>
          <div className="system-overview-donut-center">
            <span className="donut-center-number">{totalComputers}</span>
            <span className="donut-center-label">Total<br />Computers</span>
          </div>
        </div>

        {/* Right: Breakdown bars */}
        <div className="system-overview-breakdown">
          {/* 1. Online */}
          <div className="system-overview-item">
            <div className="system-overview-item-top">
              <span className="overview-item-label">
                <span className="overview-dot dot-online" /> Online
              </span>
              <span className="overview-item-val">
                {`${onlineComputers} (${onlinePct}%)`}
              </span>
            </div>
            <div className="overview-progress-track">
              <div
                className="overview-progress-bar bar-online"
                style={{ width: `${Math.min(100, parseFloat(onlinePct))}%` }}
              />
            </div>
          </div>

          {/* 2. Offline */}
          <div className="system-overview-item">
            <div className="system-overview-item-top">
              <span className="overview-item-label">
                <span className="overview-dot dot-offline" /> Offline
              </span>
              <span className="overview-item-val">
                {`${offlineComputers} (${offlinePct}%)`}
              </span>
            </div>
            <div className="overview-progress-track">
              <div
                className="overview-progress-bar bar-offline"
                style={{ width: `${Math.min(100, parseFloat(offlinePct))}%` }}
              />
            </div>
          </div>

          {/* 3. High RAM Usage */}
          <div className="system-overview-item">
            <div className="system-overview-item-top">
              <span className="overview-item-label">
                <span className="overview-dot dot-ram" /> High RAM Usage
              </span>
              <span className="overview-item-val">
                {`${highRamCount} (${highRamPct}%)`}
              </span>
            </div>
            <div className="overview-progress-track">
              <div
                className="overview-progress-bar bar-ram"
                style={{ width: `${Math.min(100, parseFloat(highRamPct))}%` }}
              />
            </div>
          </div>

          {/* 4. Low Disk Space */}
          <div className="system-overview-item">
            <div className="system-overview-item-top">
              <span className="overview-item-label">
                <span className="overview-dot dot-disk" /> Low Disk Space
              </span>
              <span className="overview-item-val">
                {`${lowDiskCount} (${lowDiskPct}%)`}
              </span>
            </div>
            <div className="overview-progress-track">
              <div
                className="overview-progress-bar bar-disk"
                style={{ width: `${Math.min(100, parseFloat(lowDiskPct))}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
