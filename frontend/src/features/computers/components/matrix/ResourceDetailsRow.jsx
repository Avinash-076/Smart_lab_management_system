import Icon from "../../../../components/ui/Icon";
import "./ResourceDetailsRow.css";

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined || isNaN(bytes)) return "—";
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}

function ResourceDetailsRow({
  diskPartitions = [],
  memoryDetails = {},
  networkDetails = {},
  loading = false,
}) {
  // Safe defaults for Memory Details
  const memTotal = memoryDetails?.total_gb || 16.0;
  const memInUseGb = memoryDetails?.in_use_gb !== null && memoryDetails?.in_use_gb !== undefined
    ? memoryDetails.in_use_gb
    : null;
  const memAvailGb = memoryDetails?.available_gb !== null && memoryDetails?.available_gb !== undefined
    ? memoryDetails.available_gb
    : null;
  const memInUsePct = memoryDetails?.in_use_percent !== null && memoryDetails?.in_use_percent !== undefined
    ? Math.round(memoryDetails.in_use_percent)
    : memInUseGb !== null ? Math.round((memInUseGb / memTotal) * 100) : 0;
  const memAvailPct = Math.max(0, 100 - memInUsePct);

  // Network speeds & volumes
  const downSpeed = networkDetails?.download_mbps !== null && networkDetails?.download_mbps !== undefined
    ? `${networkDetails.download_mbps} Mbps`
    : "—";
  const upSpeed = networkDetails?.upload_mbps !== null && networkDetails?.upload_mbps !== undefined
    ? `${networkDetails.upload_mbps} Mbps`
    : "—";

  const sentText = networkDetails?.total_sent_gb !== null && networkDetails?.total_sent_gb !== undefined
    ? `${networkDetails.total_sent_gb} GB`
    : networkDetails?.total_sent_bytes
    ? formatBytes(networkDetails.total_sent_bytes)
    : "—";

  const recvText = networkDetails?.total_received_gb !== null && networkDetails?.total_received_gb !== undefined
    ? `${networkDetails.total_received_gb} GB`
    : networkDetails?.total_received_bytes
    ? formatBytes(networkDetails.total_received_bytes)
    : "—";

  // Partitions fallback if empty
  const partitions = diskPartitions && diskPartitions.length > 0 ? diskPartitions : [
    {
      name: "C: (System)",
      percent: 0,
      used_gb: 0,
      total_gb: 512,
    },
  ];

  return (
    <div className="resource-details-row">
      {/* 1. Disk Space Usage Card */}
      <div className="detail-card disk-detail-card">
        <div className="detail-card-header">
          <div className="detail-card-title-box">
            <div className="detail-icon-wrap" style={{ color: "#f59e0b" }}>
              <Icon type="storage" size={18} />
            </div>
            <h3 className="detail-card-title">Disk Space Usage</h3>
          </div>
        </div>

        <div className="detail-card-body disk-partitions-body">
          {loading ? (
            <div className="detail-loading-skeleton" />
          ) : (
            <div className="partitions-list">
              {partitions.map((part, idx) => {
                const pct = Math.min(100, Math.max(0, Math.round(part.percent || 0)));
                const barColor = idx === 0 ? "orange" : "blue";
                const total = part.total_gb || 512;
                const used = part.used_gb !== undefined ? part.used_gb : Math.round((total * pct) / 100);

                return (
                  <div key={idx} className="partition-item">
                    <div className="partition-label-row">
                      <span className="partition-name">{part.name || part.mountpoint || `Drive ${idx + 1}`}</span>
                    </div>
                    <div className="partition-pct-row">
                      <span className="partition-pct-val">{pct}%</span>
                    </div>
                    <div className="partition-bar-track">
                      <div
                        className={`partition-bar-fill ${barColor}`}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <div className="partition-subtext">
                      {used} GB used of {total} GB
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* 2. Memory Details Card */}
      <div className="detail-card memory-detail-card">
        <div className="detail-card-header">
          <div className="detail-card-title-box">
            <div className="detail-icon-wrap" style={{ color: "#10b981" }}>
              <Icon type="memory" size={18} />
            </div>
            <h3 className="detail-card-title">Memory Details</h3>
          </div>
        </div>

        <div className="detail-card-body memory-card-body">
          {loading ? (
            <div className="detail-loading-skeleton" />
          ) : (
            <>
              {/* Stacked Progress Bar */}
              <div className="memory-stacked-track">
                <div
                  className="memory-segment-fill in-use"
                  style={{ width: `${memInUsePct}%` }}
                  title={`In Use: ${memInUsePct}%`}
                />
                <div
                  className="memory-segment-fill available"
                  style={{ width: `${memAvailPct}%` }}
                  title={`Available: ${memAvailPct}%`}
                />
              </div>

              {/* Memory Legend */}
              <div className="memory-legend-row">
                <div className="memory-legend-col">
                  <div className="legend-dot-label">
                    <span className="legend-dot green" />
                    <span className="legend-lbl">In Use</span>
                  </div>
                  <span className="legend-val">
                    {memInUseGb !== null ? `${memInUseGb} GB (${memInUsePct}%)` : "—"}
                  </span>
                </div>

                <div className="memory-legend-col">
                  <div className="legend-dot-label">
                    <span className="legend-dot grey" />
                    <span className="legend-lbl">Available</span>
                  </div>
                  <span className="legend-val">
                    {memAvailGb !== null ? `${memAvailGb} GB (${memAvailPct}%)` : "—"}
                  </span>
                </div>

                <div className="memory-legend-col">
                  <div className="legend-dot-label">
                    <span className="legend-dot blue" />
                    <span className="legend-lbl">Total</span>
                  </div>
                  <span className="legend-val">
                    {memTotal ? `${memTotal} GB` : "—"}
                  </span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* 3. Network Details Card */}
      <div className="detail-card network-detail-card">
        <div className="detail-card-header">
          <div className="detail-card-title-box">
            <div className="detail-icon-wrap" style={{ color: "#8b5cf6" }}>
              <Icon type="network" size={18} />
            </div>
            <h3 className="detail-card-title">Network Details</h3>
          </div>
        </div>

        <div className="detail-card-body network-card-body">
          {loading ? (
            <div className="detail-loading-skeleton" />
          ) : (
            <>
              {/* Download and Upload Speed dials */}
              <div className="network-speeds-grid">
                <div className="speed-dial-box">
                  <div className="speed-circle-icon down">
                    <Icon type="arrow-down" size={16} />
                  </div>
                  <div className="speed-info-stack">
                    <span className="speed-value">{downSpeed}</span>
                    <span className="speed-label">Download Speed</span>
                  </div>
                </div>

                <div className="speed-dial-box">
                  <div className="speed-circle-icon up">
                    <Icon type="arrow-up" size={16} />
                  </div>
                  <div className="speed-info-stack">
                    <span className="speed-value">{upSpeed}</span>
                    <span className="speed-label">Upload Speed</span>
                  </div>
                </div>
              </div>

              {/* Cumulative Sent and Received */}
              <div className="network-cumulative-row">
                <div className="cumulative-col">
                  <span className="cumul-label">Sent</span>
                  <span className="cumul-val">{sentText}</span>
                </div>
                <div className="cumulative-col">
                  <span className="cumul-label">Received</span>
                  <span className="cumul-val">{recvText}</span>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ResourceDetailsRow;
