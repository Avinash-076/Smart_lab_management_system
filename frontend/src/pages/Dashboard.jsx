
import { useState, useEffect } from "react";
import { getComputers } from "../services/api";
import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function Dashboard() {
  const [computers, setComputers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getComputers();
      setComputers(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
      setError(err.message || "Failed to load dashboard statistics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
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
            Monitor and manage all laboratory computers.
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

          {/* RECENT ACTIVITY */}
          <div className="table-card">
            <div className="page-section-header">
              <div>
                <h3>Recent Activity</h3>
                <p>
                  Latest events from laboratory computers.
                </p>
              </div>
            </div>

            <div className="empty-state">
              <Icon type="details" size={32} />
              <h3>No recent activity</h3>
              <p>
                Recent computer activity will appear here.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

export default Dashboard;
