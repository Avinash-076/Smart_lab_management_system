import { useState, useEffect, useCallback } from "react";
import { getComputers, getNotifications } from "../services/api";
import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function formatRelativeTime(dateStr) {
  if (!dateStr) return "Just now";
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffSec = Math.floor((now - date) / 1000);
    if (diffSec < 60) return "Just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return dateStr;
  }
}

function Dashboard() {
  const [computers, setComputers] = useState([]);
  const [recentNotifications, setRecentNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const [compData, notifData] = await Promise.all([
        getComputers(),
        getNotifications({ limit: 6 }).catch(() => []),
      ]);
      setComputers(Array.isArray(compData) ? compData : []);
      setRecentNotifications(Array.isArray(notifData) ? notifData : []);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
      setError(err.message || "Failed to load dashboard statistics.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        setLoading(true);
        setError("");
        const [compData, notifData] = await Promise.all([
          getComputers(),
          getNotifications({ limit: 6 }).catch(() => []),
        ]);
        if (ignore) return;
        setComputers(Array.isArray(compData) ? compData : []);
        setRecentNotifications(Array.isArray(notifData) ? notifData : []);
      } catch (err) {
        if (!ignore) {
          console.error("Failed to load dashboard data:", err);
          setError(err.message || "Failed to load dashboard statistics.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, []);

  const totalComputers = computers.length;
  const onlineComputers = computers.filter(
    (c) => c.status && c.status.toLowerCase() === "online"
  ).length;
  const offlineComputers = computers.filter(
    (c) => !c.status || c.status.toLowerCase() === "offline"
  ).length;
  const windowsComputers = computers.filter(
    (c) => c.os_name && c.os_name.toLowerCase().includes("windows")
  ).length;

  return (
    <div className="content">
      {/* PAGE HEADER */}
      <div className="page-top">
        <div>
          <h2>Dashboard</h2>
          <p>
            Monitor and manage all laboratory computers and active alerts.
          </p>
        </div>

        <div className="top-actions">
          <button
            className="refresh"
            onClick={loadDashboardData}
            disabled={loading}
            title="Refresh dashboard statistics"
          >
            <Icon type="refresh" size={18} />
            Refresh
          </button>
        </div>
      </div>

      {/* LOADING STATE */}
      {loading && computers.length === 0 ? (
        <div className="table-card" style={{ padding: "40px 20px", textAlign: "center" }}>
          <div className="empty-state">
            <Icon type="refresh" size={32} />
            <h3>Loading dashboard data...</h3>
            <p>Fetching real computer statistics from backend.</p>
          </div>
        </div>
      ) : error && computers.length === 0 ? (
        /* ERROR STATE */
        <div className="table-card" style={{ padding: "40px 20px", textAlign: "center" }}>
          <div className="empty-state">
            <Icon type="details" size={32} />
            <h3 style={{ color: "#dc2626" }}>Failed to load dashboard</h3>
            <p>{error}</p>
            <button
              className="refresh"
              onClick={loadDashboardData}
              style={{ marginTop: "15px", display: "inline-flex" }}
            >
              <Icon type="refresh" size={18} />
              Try Again
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* STAT CARDS */}
          <div className="cards">
            <StatCard
              icon="computer"
              title="Total Computers"
              number={totalComputers}
              footer="All registered computers"
              type="blue"
            />

            <StatCard
              icon="computer"
              title="Online"
              number={onlineComputers}
              footer="Currently online"
              type="green"
            />

            <StatCard
              icon="computer"
              title="Offline"
              number={offlineComputers}
              footer="Currently offline"
              type="orange"
            />

            <StatCard
              icon="windows"
              title="Windows Systems"
              number={windowsComputers}
              footer="Windows computers"
              type="purple"
            />
          </div>

          {/* DASHBOARD SECTIONS */}
          <div className="table-card">
            <div className="page-section-header">
              <div>
                <h3>System Overview</h3>
                <p>
                  Current status of the laboratory computers.
                </p>
              </div>
            </div>

            <div className="dashboard-grid">
              <div className="dashboard-panel">
                <div className="dashboard-panel-icon">
                  <Icon type="computer" size={24} />
                </div>

                <div>
                  <h3>{onlineComputers}</h3>
                  <p>Online Computers</p>
                </div>
              </div>

              <div className="dashboard-panel">
                <div className="dashboard-panel-icon">
                  <Icon type="computer" size={24} />
                </div>

                <div>
                  <h3>{offlineComputers}</h3>
                  <p>Offline Computers</p>
                </div>
              </div>

              <div className="dashboard-panel">
                <div className="dashboard-panel-icon">
                  <Icon type="windows" size={24} />
                </div>

                <div>
                  <h3>{windowsComputers}</h3>
                  <p>Windows Systems</p>
                </div>
              </div>

              <div className="dashboard-panel">
                <div className="dashboard-panel-icon">
                  <Icon type="home" size={24} />
                </div>

                <div>
                  <h3>{totalComputers}</h3>
                  <p>Total Managed</p>
                </div>
              </div>
            </div>
          </div>

          {/* RECENT ACTIVITY & SYSTEM ALERTS */}
          <div className="table-card">
            <div className="page-section-header">
              <div>
                <h3>Recent Activity & Alerts</h3>
                <p>
                  Latest real-time events and system alerts from laboratory computers.
                </p>
              </div>
            </div>

            {recentNotifications.length > 0 ? (
              <div style={{ padding: "0 20px 20px" }}>
                {recentNotifications.map((notif) => {
                  const compName = notif.computer_hostname || `PC-${notif.computer_id}`;
                  const isCritical = notif.severity === "critical";
                  const isWarning = notif.severity === "warning";
                  const dotColor = isCritical ? "#ef4444" : isWarning ? "#f59e0b" : "#3b82f6";
                  const badgeBg = isCritical
                    ? "rgba(239, 68, 68, 0.12)"
                    : isWarning
                    ? "rgba(245, 158, 11, 0.12)"
                    : "rgba(59, 130, 246, 0.12)";
                  const badgeColor = isCritical ? "#ef4444" : isWarning ? "#f59e0b" : "#3b82f6";

                  return (
                    <div
                      key={notif.id}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "12px 14px",
                        marginBottom: "8px",
                        borderRadius: "8px",
                        background: notif.is_read ? "rgba(255, 255, 255, 0.02)" : "rgba(59, 130, 246, 0.04)",
                        border: "1px solid rgba(255, 255, 255, 0.06)",
                        gap: "12px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", flex: 1, minWidth: 0 }}>
                        <span
                          style={{
                            width: "8px",
                            height: "8px",
                            borderRadius: "50%",
                            background: dotColor,
                            flexShrink: 0,
                          }}
                        />
                        <div>
                          <strong style={{ fontSize: "13px", color: "#f0f6fc", marginRight: "8px" }}>
                            {compName}
                          </strong>
                          <span
                            style={{
                              display: "inline-block",
                              padding: "2px 6px",
                              borderRadius: "10px",
                              fontSize: "11px",
                              fontWeight: "600",
                              background: badgeBg,
                              color: badgeColor,
                              marginRight: "8px",
                            }}
                          >
                            {notif.category?.toUpperCase()}
                          </span>
                          <span style={{ fontSize: "13px", color: "#8b949e" }}>
                            {notif.message}
                          </span>
                        </div>
                      </div>

                      <div style={{ fontSize: "12px", color: "#718096", whiteSpace: "nowrap" }}>
                        {formatRelativeTime(notif.created_at)}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="empty-state">
                <Icon type="details" size={32} />
                <h3>No recent activity</h3>
                <p>
                  Recent computer activity and system alerts will appear here.
                </p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;
