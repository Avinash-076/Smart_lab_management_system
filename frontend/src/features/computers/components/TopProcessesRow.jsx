import Icon from "../../../components/ui/Icon";
import "./TopProcessesRow.css";

function ProcessIcon({ name }) {
  const n = (name || "").toLowerCase();
  if (n.includes("chrome") || n.includes("browser")) {
    return <span className="proc-app-icon chrome-icon">🌐</span>;
  }
  if (n.includes("code") || n.includes("vscode")) {
    return <span className="proc-app-icon code-icon">💻</span>;
  }
  if (n.includes("edge")) {
    return <span className="proc-app-icon edge-icon">🌊</span>;
  }
  if (n.includes("onedrive") || n.includes("cloud")) {
    return <span className="proc-app-icon cloud-icon">☁️</span>;
  }
  if (n.includes("java")) {
    return <span className="proc-app-icon java-icon">☕</span>;
  }
  return <span className="proc-app-icon default-icon">⚙️</span>;
}

function TopProcessesRow({
  rankings = null,
  loading = false,
  onViewAll,
}) {
  const topCpu = rankings?.top_cpu || [];
  const topMem = rankings?.top_memory || [];
  const networkAttribution = rankings?.network || {
    supported: false,
    reason: "Platform attribution unavailable: user-space process socket I/O is not reliably attributable without kernel-mode drivers on Windows.",
    items: [],
  };

  return (
    <div className="top-processes-row">
      {/* 1. Top CPU Usage Processes */}
      <div className="process-ranking-card">
        <div className="proc-card-header">
          <div className="proc-card-title-box">
            <div className="proc-header-icon cpu" style={{ color: "#2563eb" }}>
              <Icon type="cpu" size={17} />
            </div>
            <h3 className="proc-card-title">Top CPU Usage Processes</h3>
          </div>
          {onViewAll && (
            <button
              type="button"
              className="view-all-link-btn"
              onClick={onViewAll}
            >
              View All
            </button>
          )}
        </div>

        <div className="proc-card-body">
          {loading ? (
            <div className="proc-skeleton-table" />
          ) : topCpu.length === 0 ? (
            <div className="proc-empty-state">No process data available</div>
          ) : (
            <table className="proc-mini-table">
              <thead>
                <tr>
                  <th className="th-rank">#</th>
                  <th className="th-name">Process Name</th>
                  <th className="th-cpu">CPU %</th>
                  <th className="th-mem">Memory</th>
                  <th className="th-user">User</th>
                </tr>
              </thead>
              <tbody>
                {topCpu.map((p, idx) => (
                  <tr key={p.pid || idx}>
                    <td className="td-rank">{p.rank || idx + 1}</td>
                    <td className="td-name">
                      <div className="proc-name-cell">
                        <ProcessIcon name={p.name} />
                        <span className="proc-name-text" title={p.name}>
                          {p.name}
                        </span>
                      </div>
                    </td>
                    <td className="td-cpu">{p.cpu_percent !== undefined ? `${p.cpu_percent}%` : "—"}</td>
                    <td className="td-mem">
                      {p.memory_mb ? `${Math.round(p.memory_mb)} MB` : p.memory_percent ? `${p.memory_percent}%` : "—"}
                    </td>
                    <td className="td-user">{p.user || "System"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* 2. Memory Usage by Process */}
      <div className="process-ranking-card">
        <div className="proc-card-header">
          <div className="proc-card-title-box">
            <div className="proc-header-icon mem" style={{ color: "#10b981" }}>
              <Icon type="memory" size={17} />
            </div>
            <h3 className="proc-card-title">Memory Usage by Process</h3>
          </div>
          {onViewAll && (
            <button
              type="button"
              className="view-all-link-btn"
              onClick={onViewAll}
            >
              View All
            </button>
          )}
        </div>

        <div className="proc-card-body">
          {loading ? (
            <div className="proc-skeleton-table" />
          ) : topMem.length === 0 ? (
            <div className="proc-empty-state">No process data available</div>
          ) : (
            <table className="proc-mini-table">
              <thead>
                <tr>
                  <th className="th-rank">#</th>
                  <th className="th-name">Process Name</th>
                  <th className="th-mem">Memory</th>
                  <th className="th-cpu">CPU %</th>
                  <th className="th-user">User</th>
                </tr>
              </thead>
              <tbody>
                {topMem.map((p, idx) => (
                  <tr key={p.pid || idx}>
                    <td className="td-rank">{p.rank || idx + 1}</td>
                    <td className="td-name">
                      <div className="proc-name-cell">
                        <ProcessIcon name={p.name} />
                        <span className="proc-name-text" title={p.name}>
                          {p.name}
                        </span>
                      </div>
                    </td>
                    <td className="td-mem">
                      {p.memory_mb ? `${Math.round(p.memory_mb)} MB` : p.memory_percent ? `${p.memory_percent}%` : "—"}
                    </td>
                    <td className="td-cpu">{p.cpu_percent !== undefined ? `${p.cpu_percent}%` : "—"}</td>
                    <td className="td-user">{p.user || "System"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* 3. Network Usage by Process */}
      <div className="process-ranking-card">
        <div className="proc-card-header">
          <div className="proc-card-title-box">
            <div className="proc-header-icon net" style={{ color: "#8b5cf6" }}>
              <Icon type="network" size={17} />
            </div>
            <h3 className="proc-card-title">Network Usage by Process</h3>
          </div>
          {onViewAll && (
            <button
              type="button"
              className="view-all-link-btn"
              onClick={onViewAll}
            >
              View All
            </button>
          )}
        </div>

        <div className="proc-card-body">
          {loading ? (
            <div className="proc-skeleton-table" />
          ) : !networkAttribution.supported && (!networkAttribution.items || networkAttribution.items.length === 0) ? (
            <div className="proc-platform-notice">
              <div className="notice-icon-box">
                <Icon type="info" size={20} />
              </div>
              <div className="notice-content">
                <span className="notice-title">Per-Process Network Attribution</span>
                <p className="notice-desc">
                  Windows user-mode agents cannot reliably attribute individual socket I/O to processes without kernel-mode drivers (ETW/WinPcap). Host aggregated network telemetry is monitored above.
                </p>
              </div>
            </div>
          ) : (
            <table className="proc-mini-table">
              <thead>
                <tr>
                  <th className="th-rank">#</th>
                  <th className="th-name">Process Name</th>
                  <th className="th-down">Download</th>
                  <th className="th-up">Upload</th>
                  <th className="th-total">Total</th>
                </tr>
              </thead>
              <tbody>
                {networkAttribution.items.map((p, idx) => (
                  <tr key={p.pid || idx}>
                    <td className="td-rank">{p.rank || idx + 1}</td>
                    <td className="td-name">
                      <div className="proc-name-cell">
                        <ProcessIcon name={p.name} />
                        <span className="proc-name-text" title={p.name}>
                          {p.name}
                        </span>
                      </div>
                    </td>
                    <td className="td-down">{p.download_mb ? `${p.download_mb} MB` : "—"}</td>
                    <td className="td-up">{p.upload_mb ? `${p.upload_mb} MB` : "—"}</td>
                    <td className="td-total">{p.total_mb ? `${p.total_mb} MB` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default TopProcessesRow;
