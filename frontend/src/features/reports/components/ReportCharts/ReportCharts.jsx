import Icon from "../../../../components/ui/Icon";
import "./ReportCharts.css";

function ReportCharts({ category, reportData, loading }) {
  if (loading || !reportData) return null;

  switch (category) {
    case "inventory": {
      const osDist = reportData.os_distribution || [];
      const hw = reportData.hardware_summary || {};

      return (
        <div className="report-charts-grid">
          {/* OS Distribution */}
          <div className="report-chart-card">
            <div className="report-chart-header">
              <h3 className="report-chart-title">Operating System Distribution</h3>
              <span className="report-chart-tag">Hardware Fleet</span>
            </div>
            {osDist.length === 0 ? (
              <div className="report-chart-empty">No OS distribution data recorded</div>
            ) : (
              <div className="report-dist-list">
                {osDist.map((item, idx) => (
                  <div key={idx} className="report-dist-row">
                    <div className="report-dist-meta">
                      <span className="report-dist-name">
                        <Icon type={item.os_name?.toLowerCase().includes("win") ? "windows" : "computer"} size={16} />
                        {item.os_name}
                      </span>
                      <span className="report-dist-stat">
                        {item.count} hosts ({item.percentage}%)
                      </span>
                    </div>
                    <div className="report-progress-track">
                      <div
                        className="report-progress-fill report-fill-blue"
                        style={{ width: `${Math.min(100, Math.max(2, item.percentage))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Hardware Specifications Summary */}
          <div className="report-chart-card">
            <div className="report-chart-header">
              <h3 className="report-chart-title">Hardware Aggregate Capacity</h3>
              <span className="report-chart-tag">Specifications</span>
            </div>
            <div className="report-hw-metrics-list">
              <div className="report-hw-metric-item">
                <div className="report-hw-metric-label">
                  <Icon type="cpu" size={16} />
                  <span>Average Processor Cores</span>
                </div>
                <div className="report-hw-metric-value">{hw.avg_cores || 0} cores</div>
              </div>
              <div className="report-hw-metric-item">
                <div className="report-hw-metric-label">
                  <Icon type="ram" size={16} />
                  <span>Total System Memory (RAM)</span>
                </div>
                <div className="report-hw-metric-value">{hw.total_ram_gb || 0} GB</div>
              </div>
              <div className="report-hw-metric-item">
                <div className="report-hw-metric-label">
                  <Icon type="storage" size={16} />
                  <span>Total Storage Capacity</span>
                </div>
                <div className="report-hw-metric-value">{hw.total_storage_gb || 0} GB</div>
              </div>
            </div>
          </div>
        </div>
      );
    }

    case "utilization": {
      const ms = reportData.metrics_summary || {};
      const timeline = reportData.timeline || [];

      // Generate SVG path for timeline if points exist
      const maxPts = timeline.slice(-20);
      const hasTimeline = maxPts.length > 1;

      const width = 500;
      const height = 140;
      const padding = 20;

      const getPoints = (key) => {
        if (!hasTimeline) return "";
        return maxPts
          .map((pt, i) => {
            const x = padding + (i / (maxPts.length - 1)) * (width - 2 * padding);
            const val = pt[key] || 0;
            const y = height - padding - (val / 100) * (height - 2 * padding);
            return `${x},${y}`;
          })
          .join(" ");
      };

      return (
        <div className="report-charts-grid">
          {/* Resource Usage Gauges */}
          <div className="report-chart-card">
            <div className="report-chart-header">
              <h3 className="report-chart-title">Average Resource Utilization</h3>
              <span className="report-chart-tag">{reportData.period} window</span>
            </div>
            <div className="report-dist-list">
              <div className="report-dist-row">
                <div className="report-dist-meta">
                  <span className="report-dist-name">
                    <Icon type="cpu" size={16} /> CPU Utilization
                  </span>
                  <span className="report-dist-stat">{ms.avg_cpu_percent}%</span>
                </div>
                <div className="report-progress-track">
                  <div
                    className="report-progress-fill report-fill-blue"
                    style={{ width: `${Math.min(100, Math.max(0, ms.avg_cpu_percent))}%` }}
                  />
                </div>
              </div>

              <div className="report-dist-row">
                <div className="report-dist-meta">
                  <span className="report-dist-name">
                    <Icon type="ram" size={16} /> Memory (RAM) Utilization
                  </span>
                  <span className="report-dist-stat">{ms.avg_ram_percent}%</span>
                </div>
                <div className="report-progress-track">
                  <div
                    className="report-progress-fill report-fill-purple"
                    style={{ width: `${Math.min(100, Math.max(0, ms.avg_ram_percent))}%` }}
                  />
                </div>
              </div>

              <div className="report-dist-row">
                <div className="report-dist-meta">
                  <span className="report-dist-name">
                    <Icon type="storage" size={16} /> Storage (Disk) Utilization
                  </span>
                  <span className="report-dist-stat">{ms.avg_disk_percent}%</span>
                </div>
                <div className="report-progress-track">
                  <div
                    className="report-progress-fill report-fill-indigo"
                    style={{ width: `${Math.min(100, Math.max(0, ms.avg_disk_percent))}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Telemetry Timeline Trend */}
          <div className="report-chart-card">
            <div className="report-chart-header">
              <h3 className="report-chart-title">Telemetry Activity Trend</h3>
              <span className="report-chart-tag">
                {timeline.length} {timeline.length === 1 ? "Sample" : "Samples"}
              </span>
            </div>
            {hasTimeline ? (
              <div className="report-timeline-container">
                <svg viewBox={`0 0 ${width} ${height}`} className="report-timeline-svg">
                  <polyline
                    fill="none"
                    stroke="#3157D5"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    points={getPoints("avg_cpu")}
                  />
                  <polyline
                    fill="none"
                    stroke="#7C3AED"
                    strokeWidth="2"
                    strokeDasharray="4 4"
                    points={getPoints("avg_ram")}
                  />
                </svg>
                <div className="report-timeline-legend">
                  <span className="legend-item">
                    <span className="legend-dot dot-blue" /> Avg CPU
                  </span>
                  <span className="legend-item">
                    <span className="legend-dot dot-purple" /> Avg RAM
                  </span>
                </div>
              </div>
            ) : (
              <div className="report-chart-empty">
                {timeline.length === 1
                  ? "Single telemetry point captured. Additional intervals will generate a trend line."
                  : "No historical telemetry samples in selected period."}
              </div>
            )}
          </div>
        </div>
      );
    }

    case "software": {
      const topInstalled = reportData.top_installed || [];
      const totalRecs = reportData.total_records || 1;

      return (
        <div className="report-charts-grid">
          <div className="report-chart-card full-width-card">
            <div className="report-chart-header">
              <h3 className="report-chart-title">Top Installed Applications</h3>
              <span className="report-chart-tag">Software Inventory</span>
            </div>
            {topInstalled.length === 0 ? (
              <div className="report-chart-empty">No installed applications found</div>
            ) : (
              <div className="report-dist-list">
                {topInstalled.slice(0, 5).map((app, idx) => {
                  const pct = Math.round((app.count / totalRecs) * 100);
                  return (
                    <div key={idx} className="report-dist-row">
                      <div className="report-dist-meta">
                        <span className="report-dist-name">
                          <strong>{app.name}</strong>
                          {app.publisher && <small className="report-dist-sub">({app.publisher})</small>}
                        </span>
                        <span className="report-dist-stat">{app.count} computers</span>
                      </div>
                      <div className="report-progress-track">
                        <div
                          className="report-progress-fill report-fill-blue"
                          style={{ width: `${Math.min(100, Math.max(5, pct))}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      );
    }

    case "issues": {
      const bySev = reportData.by_severity || {};
      const byStat = reportData.by_status || {};
      const total = reportData.total_issues || 1;

      const severities = [
        { label: "Critical", count: bySev.critical || 0, tone: "red" },
        { label: "High", count: bySev.high || 0, tone: "orange" },
        { label: "Medium", count: bySev.medium || 0, tone: "blue" },
        { label: "Low", count: bySev.low || 0, tone: "green" },
      ];

      return (
        <div className="report-charts-grid">
          <div className="report-chart-card">
            <div className="report-chart-header">
              <h3 className="report-chart-title">Issues by Severity</h3>
              <span className="report-chart-tag">Priority</span>
            </div>
            <div className="report-dist-list">
              {severities.map((item, idx) => {
                const pct = Math.round((item.count / total) * 100);
                return (
                  <div key={idx} className="report-dist-row">
                    <div className="report-dist-meta">
                      <span className="report-dist-name">{item.label}</span>
                      <span className="report-dist-stat">{item.count} ({pct}%)</span>
                    </div>
                    <div className="report-progress-track">
                      <div
                        className={`report-progress-fill report-fill-${item.tone}`}
                        style={{ width: `${Math.min(100, Math.max(item.count ? 5 : 0, pct))}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="report-chart-card">
            <div className="report-chart-header">
              <h3 className="report-chart-title">Issues Resolution Status</h3>
              <span className="report-chart-tag">Workflow</span>
            </div>
            <div className="report-hw-metrics-list">
              <div className="report-hw-metric-item">
                <span className="report-hw-metric-label">Open Issues</span>
                <span className="report-hw-metric-value report-val-orange">{byStat.open || 0}</span>
              </div>
              <div className="report-hw-metric-item">
                <span className="report-hw-metric-label">In Progress</span>
                <span className="report-hw-metric-value report-val-blue">{byStat.in_progress || 0}</span>
              </div>
              <div className="report-hw-metric-item">
                <span className="report-hw-metric-label">Resolved</span>
                <span className="report-hw-metric-value report-val-green">{byStat.resolved || 0}</span>
              </div>
            </div>
          </div>
        </div>
      );
    }

    case "usage": {
      const topApps = reportData.top_applications || [];
      const topProcs = reportData.top_processes || [];

      return (
        <div className="report-charts-grid">
          <div className="report-chart-card">
            <div className="report-chart-header">
              <h3 className="report-chart-title">Most Used Applications</h3>
              <span className="report-chart-tag">Duration</span>
            </div>
            {topApps.length === 0 ? (
              <div className="report-chart-empty">No application usage sessions recorded</div>
            ) : (
              <div className="report-dist-list">
                {topApps.slice(0, 5).map((app, idx) => (
                  <div key={idx} className="report-dist-row">
                    <div className="report-dist-meta">
                      <span className="report-dist-name">
                        <Icon type="cpu" size={15} />
                        {app.application_name}
                      </span>
                      <span className="report-dist-stat">
                        {app.total_duration_hours} hrs ({app.session_count} runs)
                      </span>
                    </div>
                    <div className="report-progress-track">
                      <div
                        className="report-progress-fill report-fill-blue"
                        style={{
                          width: `${Math.min(
                            100,
                            Math.max(5, (app.total_duration_hours / (topApps[0]?.total_duration_hours || 1)) * 100)
                          )}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="report-chart-card">
            <div className="report-chart-header">
              <h3 className="report-chart-title">Live Top Processes Snapshot</h3>
              <span className="report-chart-tag">Resource Intensive</span>
            </div>
            {topProcs.length === 0 ? (
              <div className="report-chart-empty">No active processes snapshot available</div>
            ) : (
              <div className="report-dist-list">
                {topProcs.slice(0, 5).map((proc, idx) => (
                  <div key={idx} className="report-dist-row">
                    <div className="report-dist-meta">
                      <span className="report-dist-name">
                        <strong>{proc.name}</strong>
                        <small className="report-dist-sub">PID: {proc.pid}</small>
                      </span>
                      <span className="report-dist-stat">
                        CPU: {proc.cpu_percent}% | RAM: {proc.memory_mb} MB
                      </span>
                    </div>
                    <div className="report-progress-track">
                      <div
                        className="report-progress-fill report-fill-purple"
                        style={{ width: `${Math.min(100, Math.max(5, proc.cpu_percent))}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      );
    }

    default:
      return null;
  }
}

export default ReportCharts;
