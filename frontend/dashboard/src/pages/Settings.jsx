import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function Reports() {
  return (
    <div className="content">

      <div className="page-top">
        <div>
          <h2>Reports</h2>

          <p>
            Generate and view laboratory monitoring reports.
          </p>
        </div>

        <div className="top-actions">

          <button className="export">
            <Icon
              type="upload"
              size={18}
            />

            Export Report
          </button>

        </div>
      </div>

      <div className="cards">

        <StatCard
          icon="computer"
          title="Computer Report"
          number="24"
          footer="Registered computers"
          type="blue"
        />

        <StatCard
          icon="issue"
          title="Issue Report"
          number="0"
          footer="Reported issues"
          type="orange"
        />

        <StatCard
          icon="maintenance"
          title="Maintenance"
          number="0"
          footer="Maintenance records"
          type="purple"
        />

        <StatCard
          icon="software"
          title="Software"
          number="0"
          footer="Software records"
          type="green"
        />

      </div>

      <div className="table-card">

        <div className="page-section-header">
          <div>
            <h3>Available Reports</h3>

            <p>
              Select a report type to generate a report.
            </p>
          </div>
        </div>

        <div className="dashboard-grid">

          <div className="dashboard-panel">
            <Icon
              type="computer"
              size={28}
            />

            <div>
              <h3>Computer Report</h3>
              <p>
                Computer status and hardware information.
              </p>
            </div>
          </div>

          <div className="dashboard-panel">
            <Icon
              type="issue"
              size={28}
            />

            <div>
              <h3>Issue Report</h3>
              <p>
                Report of computer problems and issues.
              </p>
            </div>
          </div>

          <div className="dashboard-panel">
            <Icon
              type="maintenance"
              size={28}
            />

            <div>
              <h3>Maintenance Report</h3>
              <p>
                History of maintenance activities.
              </p>
            </div>
          </div>

          <div className="dashboard-panel">
            <Icon
              type="software"
              size={28}
            />

            <div>
              <h3>Software Report</h3>
              <p>
                Software installed across laboratory computers.
              </p>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}

export default Reports;
