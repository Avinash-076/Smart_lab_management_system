import { SoftwareIcon } from "../../utils/softwareUtils";
import "./SoftwareCharts.css";

export default function SoftwareCharts({ summary, totalComputers = 5, totalRecords = 217 }) {
  // 1. Top software data
  const defaultTopSoftware = [
    { name: "Google Chrome", publisher: "Google LLC", count: 5, color: "#3b82f6" },
    { name: "Microsoft Edge", publisher: "Microsoft Corporation", count: 5, color: "#06b6d4" },
    { name: "Microsoft Visual C++", publisher: "Microsoft Corporation", count: 5, color: "#8b5cf6" },
    { name: "Python", publisher: "Python Software Foundation", count: 3, color: "#f59e0b" },
    { name: "Java", publisher: "Oracle Corporation", count: 2, color: "#93c5fd" },
  ];

  const topSoftwareItems =
    summary?.top_software && summary.top_software.length > 0
      ? summary.top_software.map((item, idx) => ({
          ...item,
          color:
            defaultTopSoftware[idx % defaultTopSoftware.length]?.color ||
            "#3b82f6",
        }))
      : defaultTopSoftware;

  const maxInstCount = Math.max(
    totalComputers || 5,
    ...topSoftwareItems.map((it) => it.count || 0)
  );

  // 2. OS distribution data
  const defaultOsData = [
    { os_name: "Windows 10", count: 142, percentage: 65.4, color: "#3b82f6" },
    { os_name: "Windows 11", count: 58, percentage: 26.7, color: "#10b981" },
    { os_name: "Other", count: 17, percentage: 7.8, color: "#8b5cf6" },
  ];

  const osDistribution =
    summary?.by_os && summary.by_os.length > 0
      ? summary.by_os.map((item, idx) => ({
          ...item,
          color: defaultOsData[idx % defaultOsData.length]?.color || "#3b82f6",
        }))
      : defaultOsData;

  const totalInstallations =
    summary?.total_software ||
    osDistribution.reduce((acc, curr) => acc + (curr.count || 0), 0) ||
    totalRecords;

  // Compute SVG Donut Chart Slices purely without outer variable mutation
  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const donutSlices = osDistribution.map((item, index) => {
    const priorPct = osDistribution
      .slice(0, index)
      .reduce((sum, curr) => sum + (curr.percentage || 0), 0);
    const strokeDasharray = `${(item.percentage / 100) * circumference} ${circumference}`;
    const strokeDashoffset = -((priorPct / 100) * circumference);
    return {
      ...item,
      strokeDasharray,
      strokeDashoffset,
    };
  });

  // 3. Top Publishers data
  const defaultPublishers = [
    { publisher: "Microsoft", count: 70, color: "#3b82f6" },
    { publisher: "Google", count: 52, color: "#10b981" },
    { publisher: "Oracle", count: 18, color: "#8b5cf6" },
    { publisher: "Python", count: 16, color: "#f59e0b" },
    { publisher: "Others", count: 61, color: "#60a5fa" },
  ];

  const topPublishers =
    summary?.top_publishers && summary.top_publishers.length > 0
      ? summary.top_publishers.map((item, idx) => ({
          ...item,
          publisher:
            item.publisher.length > 10
              ? item.publisher.split(" ")[0]
              : item.publisher,
          color:
            defaultPublishers[idx % defaultPublishers.length]?.color ||
            "#3b82f6",
        }))
      : defaultPublishers;

  const chartMaxY = 80;

  return (
    <div className="software-analytics-grid">
      {/* ========================================================
          Card 1: Top Software by Installations
      ======================================================== */}
      <div className="software-analytics-card">
        <div className="software-analytics-header">
          <div className="software-analytics-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
              <polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5 12 2" />
            </svg>
          </div>
          <h3 className="software-analytics-title">Top Software by Installations</h3>
        </div>

        <div className="software-top-list">
          {topSoftwareItems.slice(0, 5).map((item, idx) => {
            const barPct = Math.round(((item.count || 1) / maxInstCount) * 100);
            return (
              <div key={idx} className="software-top-row">
                <div className="software-top-info">
                  <div className="software-top-icon">
                    <SoftwareIcon name={item.name} publisher={item.publisher} size={20} />
                  </div>
                  <span className="software-top-name" title={item.name}>
                    {item.name}
                  </span>
                </div>

                <div className="software-top-bar-wrap">
                  <div className="software-top-bar-track">
                    <div
                      className="software-top-bar-fill"
                      style={{
                        width: `${barPct}%`,
                        backgroundColor: item.color,
                      }}
                    />
                  </div>
                </div>

                <span className="software-top-count">{item.count}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* ========================================================
          Card 2: Software by Operating System (Donut Chart)
      ======================================================== */}
      <div className="software-analytics-card">
        <div className="software-analytics-header">
          <div className="software-analytics-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
              <circle cx="18" cy="18" r="3" />
              <circle cx="6" cy="6" r="3" />
              <path d="M18 9v2a2 2 0 0 1-2 2H8" />
              <path d="M6 9v12" />
            </svg>
          </div>
          <h3 className="software-analytics-title">Software by Operating System</h3>
        </div>

        <div className="software-os-donut-container">
          <div className="software-donut-svg-wrap">
            <svg width="110" height="110" viewBox="0 0 100 100">
              <circle
                cx="50"
                cy="50"
                r={radius}
                fill="none"
                stroke="#f1f5f9"
                strokeWidth="12"
              />
              {donutSlices.map((slice, idx) => (
                <circle
                  key={idx}
                  cx="50"
                  cy="50"
                  r={radius}
                  fill="none"
                  stroke={slice.color}
                  strokeWidth="12"
                  strokeDasharray={slice.strokeDasharray}
                  strokeDashoffset={slice.strokeDashoffset}
                  transform="rotate(-90 50 50)"
                  strokeLinecap="butt"
                />
              ))}
            </svg>
            <div className="software-donut-center">
              <span className="software-donut-total">{totalInstallations}</span>
              <span className="software-donut-subtext">Installations</span>
            </div>
          </div>

          <div className="software-os-legend">
            {osDistribution.map((item, idx) => (
              <div key={idx} className="software-os-legend-item">
                <span
                  className="software-os-legend-dot"
                  style={{ backgroundColor: item.color }}
                />
                <span className="software-os-legend-name">{item.os_name}</span>
                <span className="software-os-legend-val">
                  {`${item.count} (${item.percentage}%)`}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ========================================================
          Card 3: Top Publishers (Vertical Bar Chart)
      ======================================================== */}
      <div className="software-analytics-card">
        <div className="software-analytics-header">
          <div className="software-analytics-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
              <line x1="18" y1="20" x2="18" y2="10" />
              <line x1="12" y1="20" x2="12" y2="4" />
              <line x1="6" y1="20" x2="6" y2="14" />
            </svg>
          </div>
          <h3 className="software-analytics-title">Top Publishers</h3>
        </div>

        <div className="software-publishers-chart-wrap">
          {/* Y-axis Ticks */}
          <div className="software-pub-y-axis">
            <span>80</span>
            <span>60</span>
            <span>40</span>
            <span>20</span>
            <span>0</span>
          </div>

          {/* Bar Columns Container */}
          <div className="software-pub-bars-area">
            {/* Horizontal Grid Lines */}
            <div className="software-pub-grid-line" style={{ bottom: "100%" }} />
            <div className="software-pub-grid-line" style={{ bottom: "75%" }} />
            <div className="software-pub-grid-line" style={{ bottom: "50%" }} />
            <div className="software-pub-grid-line" style={{ bottom: "25%" }} />
            <div className="software-pub-grid-line" style={{ bottom: "0%" }} />

            {/* Bars */}
            <div className="software-pub-bars-row">
              {topPublishers.slice(0, 5).map((pub, idx) => {
                const heightPct = Math.min(
                  100,
                  Math.round(((pub.count || 0) / chartMaxY) * 100)
                );
                return (
                  <div key={idx} className="software-pub-column">
                    <span className="software-pub-val">{pub.count}</span>
                    <div
                      className="software-pub-bar"
                      style={{
                        height: `${Math.max(8, heightPct)}%`,
                        backgroundColor: pub.color,
                      }}
                      title={`${pub.publisher}: ${pub.count}`}
                    />
                    <span className="software-pub-label">{pub.publisher}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
