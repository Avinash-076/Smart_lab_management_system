import Icon from "../../../../components/ui/Icon";
import "./FleetOverview.css";

export default function FleetOverview({ metrics, loading }) {
  const total = metrics?.total_computers ?? 0;
  const online = metrics?.online_computers ?? 0;
  const offline = metrics?.offline_computers ?? 0;
  const commands24h = metrics?.commands_last_24h ?? 0;
  const successful24h = metrics?.successful_commands_24h ?? 0;
  const failed24h = metrics?.failed_commands_24h ?? 0;

  const onlinePct = total > 0 ? Math.round((online / total) * 100) : 0;
  const offlinePct = total > 0 ? Math.round((offline / total) * 100) : 0;

  return (
    <div className="fleet-overview-grid" data-testid="fleet-overview">
      {/* Total Computers */}
      <div className="fleet-card">
        <div className="fleet-card-body">
          <div className="fleet-icon-wrapper blue">
            <Icon name="computer" size={24} />
          </div>
          <div className="fleet-card-info">
            <span className="fleet-card-title">Total Computers</span>
            <div className="fleet-card-value-row">
              <span className="fleet-card-value">
                {loading ? "..." : total}
              </span>
            </div>
            <span className="fleet-card-sub">All registered computers</span>
          </div>
        </div>
        <div className="fleet-card-chart blue">
          <span style={{ height: "40%" }} />
          <span style={{ height: "65%" }} />
          <span style={{ height: "50%" }} />
          <span style={{ height: "85%" }} />
          <span style={{ height: "100%" }} />
        </div>
      </div>

      {/* Online Computers */}
      <div className="fleet-card">
        <div className="fleet-card-body">
          <div className="fleet-icon-wrapper green">
            <Icon name="wifi" size={24} />
          </div>
          <div className="fleet-card-info">
            <span className="fleet-card-title">Online</span>
            <div className="fleet-card-value-row">
              <span className="fleet-card-value">
                {loading ? "..." : online}
              </span>
              <span className="fleet-badge-pct green">({onlinePct}%)</span>
            </div>
            <span className="fleet-card-trend green">
              ↑ {onlinePct}% available fleet
            </span>
          </div>
        </div>
        <div className="fleet-card-chart green">
          <span style={{ height: "35%" }} />
          <span style={{ height: "55%" }} />
          <span style={{ height: "70%" }} />
          <span style={{ height: "60%" }} />
          <span style={{ height: "90%" }} />
        </div>
      </div>

      {/* Offline Computers */}
      <div className="fleet-card">
        <div className="fleet-card-body">
          <div className="fleet-icon-wrapper red">
            <Icon name="wifi-off" size={24} />
          </div>
          <div className="fleet-card-info">
            <span className="fleet-card-title">Offline</span>
            <div className="fleet-card-value-row">
              <span className="fleet-card-value">
                {loading ? "..." : offline}
              </span>
              <span className="fleet-badge-pct red">({offlinePct}%)</span>
            </div>
            <span className="fleet-card-trend red">
              {offline > 0 ? `↓ ${offline} requiring attention` : "All systems connected"}
            </span>
          </div>
        </div>
        <div className="fleet-card-chart red">
          <span style={{ height: "60%" }} />
          <span style={{ height: "40%" }} />
          <span style={{ height: "75%" }} />
          <span style={{ height: "30%" }} />
          <span style={{ height: "50%" }} />
        </div>
      </div>

      {/* Commands 24h */}
      <div className="fleet-card">
        <div className="fleet-card-body">
          <div className="fleet-icon-wrapper indigo">
            <Icon name="file-text" size={24} />
          </div>
          <div className="fleet-card-info">
            <span className="fleet-card-title">Commands (24h)</span>
            <div className="fleet-card-value-row">
              <span className="fleet-card-value">
                {loading ? "..." : commands24h}
              </span>
            </div>
            <div className="fleet-card-status-dots">
              <span className="fleet-dot-item success">
                <span className="dot green" /> {successful24h} Success
              </span>
              <span className="fleet-dot-item failed">
                <span className="dot red" /> {failed24h} Failed
              </span>
            </div>
          </div>
        </div>
        <div className="fleet-card-chart indigo">
          <span style={{ height: "45%" }} />
          <span style={{ height: "70%" }} />
          <span style={{ height: "50%" }} />
          <span style={{ height: "80%" }} />
          <span style={{ height: "95%" }} />
        </div>
      </div>
    </div>
  );
}
