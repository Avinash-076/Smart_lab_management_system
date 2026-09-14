import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function UserRoleManagement() {
  return (
    <div className="content">

      <div className="page-top">
        <div>
          <h2>User & Role Management</h2>

          <p>
            Manage system users, roles, and permissions.
          </p>
        </div>

        <div className="top-actions">

          <button className="export">
            Add User
          </button>

        </div>
      </div>

      <div className="cards">

        <StatCard
          icon="users"
          title="Total Users"
          number="0"
          footer="Registered users"
          type="blue"
        />

        <StatCard
          icon="users"
          title="Administrators"
          number="0"
          footer="Administrator accounts"
          type="purple"
        />

        <StatCard
          icon="users"
          title="Lab Staff"
          number="0"
          footer="Lab staff accounts"
          type="green"
        />

        <StatCard
          icon="users"
          title="Active"
          number="0"
          footer="Active user accounts"
          type="orange"
        />

      </div>

      <div className="table-card">

        <div className="page-section-header">
          <div>
            <h3>Users</h3>

            <p>
              Manage users and their assigned roles.
            </p>
          </div>
        </div>

        <div className="empty-state">

          <Icon
            type="users"
            size={40}
          />

          <h3>
            No users available
          </h3>

          <p>
            User accounts will appear here after they
            are created.
          </p>

        </div>

      </div>

    </div>
  );
}

export default UserRoleManagement;