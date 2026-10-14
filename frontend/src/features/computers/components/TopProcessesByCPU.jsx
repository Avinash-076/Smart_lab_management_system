import "./TopProcessesByCPU.css";

function ProcessIcon({ name = "" }) {
  const lower = (name || "").toLowerCase();

  if (lower.includes("chrome")) {
    return (
      <span className="proc-icon proc-icon-chrome" title="Google Chrome">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none">
          <circle cx="12" cy="12" r="9" stroke="#ea4335" strokeWidth="2.5" />
          <circle cx="12" cy="12" r="4" fill="#4285f4" />
          <path d="M12 3a9 9 0 0 1 7.8 4.5L12 12" stroke="#fbbc05" strokeWidth="2" />
          <path d="M4.2 16.5A9 9 0 0 1 4.2 7.5L12 12" stroke="#34a853" strokeWidth="2" />
        </svg>
      </span>
    );
  }

  if (lower.includes("code")) {
    return (
      <span className="proc-icon proc-icon-code" title="Visual Studio Code">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" color="#007acc">
          <path d="M18.5 2.5l-7.7 7.2L6 6.5 3.5 8l4.3 4-4.3 4 2.5 1.5 4.8-3.2 7.7 7.2L22 20V4l-3.5-1.5z" />
        </svg>
      </span>
    );
  }

  if (lower.includes("msmpeng") || lower.includes("defender") || lower.includes("antivirus")) {
    return (
      <span className="proc-icon proc-icon-defender" title="Windows Defender">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#0078d4" strokeWidth="2">
          <path d="M12 2l7 4v6c0 5-3.5 9.5-7 11-3.5-1.5-7-6-7-11V6l7-4z" fill="#0078d4" fillOpacity="0.15" />
        </svg>
      </span>
    );
  }

  if (lower.includes("explorer")) {
    return (
      <span className="proc-icon proc-icon-explorer" title="Windows Explorer">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#f59e0b" strokeWidth="2">
          <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" fill="#fef3c7" />
        </svg>
      </span>
    );
  }

  if (lower.includes("dwm")) {
    return (
      <span className="proc-icon proc-icon-dwm" title="Desktop Window Manager">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#64748b" strokeWidth="2">
          <rect x="3" y="4" width="18" height="16" rx="2" fill="#f1f5f9" />
          <line x1="3" y1="9" x2="21" y2="9" />
        </svg>
      </span>
    );
  }

  if (lower.includes("python")) {
    return (
      <span className="proc-icon proc-icon-python" title="Python">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" color="#306998">
          <path d="M11.9 2c-3.4 0-3.2 1.5-3.2 1.5l.04 1.5h3.2v.5H5.4S2 5.1 2 8.5s3 3.3 3 3.3h1.8v-1.6c0-1.8 1.6-1.8 1.6-1.8h5.5s1.5.02 1.5-1.5V3.5S15.3 2 11.9 2zm-1.8 1.1a.6.6 0 110 1.2.6.6 0 010-1.2zm1.9 18.9c3.4 0 3.2-1.5 3.2-1.5l-.04-1.5h-3.2v-.5h6.5s3.4.4 3.4-3-3-3.3-3-3.3h-1.8v1.6c0 1.8-1.6 1.8-1.6 1.8h-5.5s-1.5-.02-1.5 1.5v3.4s.1 1.5 3.5 1.5zm1.8-1.1a.6.6 0 110-1.2.6.6 0 010 1.2z" />
        </svg>
      </span>
    );
  }

  if (lower.includes("others")) {
    return (
      <span className="proc-icon proc-icon-others" title="Other Processes">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#3b82f6" strokeWidth="2">
          <rect x="3" y="3" width="7" height="7" rx="1.5" fill="#3b82f6" fillOpacity="0.2" />
          <rect x="14" y="3" width="7" height="7" rx="1.5" fill="#3b82f6" fillOpacity="0.2" />
          <rect x="14" y="14" width="7" height="7" rx="1.5" fill="#3b82f6" fillOpacity="0.2" />
          <rect x="3" y="14" width="7" height="7" rx="1.5" fill="#3b82f6" fillOpacity="0.2" />
        </svg>
      </span>
    );
  }

  // Generic process/application icon
  return (
    <span className="proc-icon proc-icon-generic" title={name}>
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#64748b" strokeWidth="2">
        <polygon points="12 2 2 7 12 12 22 7 12 2" />
        <polyline points="2 17 12 22 22 17" />
        <polyline points="2 12 12 17 22 12" />
      </svg>
    </span>
  );
}

export default function TopProcessesByCPU({
  processes = [],
  totalCpuPercent = 0,
  loading = false,
}) {
  const topList = Array.isArray(processes) ? processes : [];

  // Calculate items to display (up to 5 + Others remainder if applicable)
  const items = topList.slice(0, 5);
  const topSum = items.reduce((acc, p) => acc + (p.cpu_percent || 0), 0);
  const othersCpu = Math.max(0, Math.round((totalCpuPercent - topSum) * 10) / 10);

  const displayList = [...items];
  if (topList.length > 5 && othersCpu > 0) {
    displayList.push({
      pid: 0,
      name: "Others",
      cpu_percent: othersCpu,
    });
  }

  // Determine maximum percentage for scaling the bars relative to 100% or highest item
  const maxPct = Math.max(25, ...displayList.map((p) => p.cpu_percent || 0));

  return (
    <div className="process-analytics-card top-cpu-card">
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
          <h3 className="process-analytics-title">Top Processes by CPU Usage</h3>
        </div>
      </div>

      <div className="top-cpu-content">
        {loading && displayList.length === 0 ? (
          <div className="top-cpu-empty">Loading top processes...</div>
        ) : displayList.length === 0 ? (
          <div className="top-cpu-empty">No active process CPU utilization recorded.</div>
        ) : (
          <div className="top-cpu-list">
            {displayList.map((proc) => {
              const cpuVal = proc.cpu_percent !== undefined ? proc.cpu_percent : 0;
              // Bar width proportional to maxPct
              const barWidthPct = Math.min(100, Math.max(3, (cpuVal / maxPct) * 100));

              return (
                <div key={`${proc.pid}-${proc.name}`} className="top-cpu-row">
                  <div className="top-cpu-name-group">
                    <ProcessIcon name={proc.name} />
                    <span className="top-cpu-name" title={proc.name}>
                      {proc.name}
                    </span>
                  </div>

                  <div className="top-cpu-bar-container">
                    <div
                      className="top-cpu-progress-bar"
                      style={{ width: `${barWidthPct}%` }}
                    />
                  </div>

                  <div className="top-cpu-pct-label">
                    {cpuVal.toFixed(1)}%
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
