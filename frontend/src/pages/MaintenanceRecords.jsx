import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function MaintenanceRecords() {
  return (
    <div className="content">

      <div className="page-top">
        <div>
          <h2>Maintenance Records</h2>

          <p>
            Track maintenance activities performed on lab computers.
          </p>
        </div>
      </div>

      <div className="cards">

        <StatCard
          icon="maintenance"
          title="Total Records"
          number="0"
          footer="All maintenance records"
          type="blue"
        />

        <StatCard
          icon="issue"
          title="Pending"
          number="0"
          footer="Maintenance pending"
          type="orange"
        />

        <StatCard
          icon="maintenance"
          title="In Progress"
          number="0"
          footer="Maintenance in progress"
          type="purple"
        />

        <StatCard
          icon="details"
          title="Completed"
          number="0"
          footer="Completed maintenance"
          type="green"
        />

      </div>

      <div className="table-card">

        <div className="page-section-header">
          <div>
            <h3>Maintenance Records</h3>

            <p>
              History of computer maintenance activities.
            </p>
          </div>
        </div>

        <div className="empty-state">

          <Icon
            type="maintenance"
            size={40}
          />

          <h3>
            No maintenance records
          </h3>

          <p>
            Maintenance activities will appear here.
          </p>

        </div>

      </div>

    </div>
  );
}

export default MaintenanceRecords;
