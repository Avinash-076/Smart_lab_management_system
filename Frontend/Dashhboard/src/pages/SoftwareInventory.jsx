import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function SoftwareInventory() {
  return (
    <div className="content">
      <div className="page-top">
        <div>
          <h2>Software Inventory</h2>

          <p>
            View software installed on laboratory computers.
          </p>
        </div>
      </div>

      <div className="cards">
        <StatCard
          icon="software"
          title="Total Software"
          number="0"
          footer="Installed applications"
          type="blue"
        />

        <StatCard
          icon="computer"
          title="Computers"
          number="24"
          footer="Registered computers"
          type="green"
        />

        <StatCard
          icon="issue"
          title="Outdated"
          number="0"
          footer="Software requiring updates"
          type="orange"
        />

        <StatCard
          icon="details"
          title="Categories"
          number="0"
          footer="Software categories"
          type="purple"
        />
      </div>

      <div className="table-card">
        <div className="page-section-header">
          <div>
            <h3>Installed Software</h3>

            <p>
              Software inventory collected from client agents.
            </p>
          </div>
        </div>

        <div className="empty-state">
          <Icon
            type="software"
            size={40}
          />

          <h3>No software data</h3>

          <p>
            Software information will appear here after
            client agents report their inventory.
          </p>
        </div>
      </div>
    </div>
  );
}

export default SoftwareInventory;