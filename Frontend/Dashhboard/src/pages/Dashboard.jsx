
import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function Dashboard() {
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
      </div>

      {/* STAT CARDS */}

      <div className="cards">
        <StatCard
          icon="computer"
          title="Total Computers"
          number="24"
          footer="All registered computers"
          type="blue"
        />

        <StatCard
          icon="computer"
          title="Online"
          number="18"
          footer="Currently online"
          type="green"
        />

        <StatCard
          icon="computer"
          title="Offline"
          number="6"
          footer="Currently offline"
          type="orange"
        />

        <StatCard
          icon="issue"
          title="Issues"
          number="5"
          footer="Issues requiring attention"
          type="purple"
        />
      </div>

      {/* DASHBOARD SECTIONS */}

      <div className="table-card">
        <div className="page-section-header">
          <div>
            <h3>System Overview</h3>

            <p>
              Current status of the laboratory.
            </p>
          </div>
        </div>

        <div className="dashboard-grid">
          <div className="dashboard-panel">
            <div className="dashboard-panel-icon">
              <Icon type="computer" size={24} />
            </div>

            <div>
              <h3>18</h3>
              <p>Online Computers</p>
            </div>
          </div>

          <div className="dashboard-panel">
            <div className="dashboard-panel-icon">
              <Icon type="computer" size={24} />
            </div>

            <div>
              <h3>6</h3>
              <p>Offline Computers</p>
            </div>
          </div>

          <div className="dashboard-panel">
            <div className="dashboard-panel-icon">
              <Icon type="issue" size={24} />
            </div>

            <div>
              <h3>5</h3>
              <p>Open Issues</p>
            </div>
          </div>

          <div className="dashboard-panel">
            <div className="dashboard-panel-icon">
              <Icon type="maintenance" size={24} />
            </div>

            <div>
              <h3>3</h3>
              <p>Maintenance Required</p>
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
    </div>
  );
}

export default Dashboard;
