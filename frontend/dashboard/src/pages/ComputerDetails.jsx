import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function ComputerDetails() {
  return (
    <div className="content">

      <div className="page-top">
        <div>
          <h2>Computer Details</h2>

          <p>
            View detailed information about laboratory computers.
          </p>
        </div>
      </div>

      <div className="cards">

        <StatCard
          icon="computer"
          title="Total Computers"
          number="24"
          footer="Registered computers"
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
          icon="windows"
          title="Windows"
          number="24"
          footer="Windows systems"
          type="purple"
        />

      </div>

      <div className="table-card">

        <div className="page-section-header">
          <div>
            <h3>Computer Details</h3>

            <p>
              Select a computer from the Computer List
              to view complete information.
            </p>
          </div>
        </div>

        <div className="empty-state">

          <Icon
            type="details"
            size={40}
          />

          <h3>
            No computer selected
          </h3>

          <p>
            Detailed computer information will appear
            when a computer is selected.
          </p>

        </div>

      </div>

    </div>
  );
}

export default ComputerDetails;