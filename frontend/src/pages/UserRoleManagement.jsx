import { useMemo, useState } from "react";

import Icon from "../components/Icon";

/* =====================================================
   USER & ROLE MANAGEMENT
===================================================== */

const initialUsers = [
  {
    id: 1,
    name: "Admin User",
    username: "admin",
    email: "admin@slms.local",
    role: "Administrator",
    status: "Active",
    lastLogin: "22 Sep 2026, 09:15 AM",
  },
  {
    id: 2,
    name: "Lab Administrator",
    username: "labadmin",
    email: "labadmin@slms.local",
    role: "Lab Administrator",
    status: "Active",
    lastLogin: "22 Sep 2026, 09:42 AM",
  },
  {
    id: 3,
    name: "Lab Technician",
    username: "technician",
    email: "technician@slms.local",
    role: "Technician",
    status: "Active",
    lastLogin: "21 Sep 2026, 04:30 PM",
  },
  {
    id: 4,
    name: "System Operator",
    username: "operator",
    email: "operator@slms.local",
    role: "Operator",
    status: "Active",
    lastLogin: "20 Sep 2026, 11:20 AM",
  },
  {
    id: 5,
    name: "Demo User",
    username: "demo",
    email: "demo@slms.local",
    role: "Operator",
    status: "Inactive",
    lastLogin: "15 Sep 2026, 02:10 PM",
  },
];

/* =====================================================
   ROLE DATA
===================================================== */

const roles = [
  {
    name: "Administrator",
    description:
      "Full access to all SLMS features and settings.",
    users: 1,
    permissions: [
      "Dashboard",
      "Computer Management",
      "Software Inventory",
      "Issue Management",
      "Maintenance",
      "Reports",
      "Settings",
      "User Management",
    ],
  },
  {
    name: "Lab Administrator",
    description:
      "Manage laboratory computers and monitoring.",
    users: 1,
    permissions: [
      "Dashboard",
      "Computer Management",
      "Software Inventory",
      "Issue Management",
      "Maintenance",
      "Reports",
    ],
  },
  {
    name: "Technician",
    description:
      "Monitor computers and manage maintenance tasks.",
    users: 1,
    permissions: [
      "Dashboard",
      "Computer Management",
      "Issue Management",
      "Maintenance",
    ],
  },
  {
    name: "Operator",
    description:
      "View laboratory status and computer information.",
    users: 2,
    permissions: [
      "Dashboard",
      "Computer Management",
      "Reports",
    ],
  },
];

/* =====================================================
   USER & ROLE MANAGEMENT PAGE
===================================================== */

function UserRoleManagement() {
  const [users, setUsers] =
    useState(initialUsers);

  const [search, setSearch] =
    useState("");

  const [roleFilter, setRoleFilter] =
    useState("All Roles");

  const [statusFilter, setStatusFilter] =
    useState("All Status");

  const [showAddUser, setShowAddUser] =
    useState(false);

  const [activeTab, setActiveTab] =
    useState("users");

  const [newUser, setNewUser] =
    useState({
      name: "",
      username: "",
      email: "",
      role: "Operator",
      status: "Active",
    });

  /* =====================================================
     FILTER USERS
  ===================================================== */

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      const searchValue =
        search.toLowerCase();

      const matchesSearch =
        user.name
          .toLowerCase()
          .includes(searchValue) ||
        user.username
          .toLowerCase()
          .includes(searchValue) ||
        user.email
          .toLowerCase()
          .includes(searchValue);

      const matchesRole =
        roleFilter === "All Roles" ||
        user.role === roleFilter;

      const matchesStatus =
        statusFilter === "All Status" ||
        user.status === statusFilter;

      return (
        matchesSearch &&
        matchesRole &&
        matchesStatus
      );
    });
  }, [
    users,
    search,
    roleFilter,
    statusFilter,
  ]);

  /* =====================================================
     ADD USER
  ===================================================== */

  const handleAddUser = (event) => {
    event.preventDefault();

    if (
      !newUser.name.trim() ||
      !newUser.username.trim() ||
      !newUser.email.trim()
    ) {
      return;
    }

    const user = {
      id: Date.now(),
      name: newUser.name,
      username: newUser.username,
      email: newUser.email,
      role: newUser.role,
      status: newUser.status,
      lastLogin: "Never",
    };

    setUsers((current) => [
      ...current,
      user,
    ]);

    setNewUser({
      name: "",
      username: "",
      email: "",
      role: "Operator",
      status: "Active",
    });

    setShowAddUser(false);
  };

  /* =====================================================
     DELETE USER
  ===================================================== */

  const handleDeleteUser = (id) => {
    const confirmed =
      window.confirm(
        "Are you sure you want to delete this user?"
      );

    if (!confirmed) {
      return;
    }

    setUsers((current) =>
      current.filter(
        (user) => user.id !== id
      )
    );
  };

  /* =====================================================
     RESET FILTERS
  ===================================================== */

  const resetFilters = () => {
    setSearch("");
    setRoleFilter("All Roles");
    setStatusFilter("All Status");
  };

  /* =====================================================
     RETURN
  ===================================================== */

  return (
    <div className="content">

      {/* =================================================
          PAGE HEADER
      ================================================= */}

      <div className="page-top">

        <div>
          <h2>
            User & Role Management
          </h2>

          <p>
            Manage SLMS users, roles,
            and access permissions.
          </p>
        </div>

        {activeTab === "users" && (
          <button
            className="user-add-button"
            onClick={() =>
              setShowAddUser(true)
            }
          >
            <Icon
              type="plus"
              size={16}
            />

            Add User
          </button>
        )}

      </div>

      {/* =================================================
          TABS
      ================================================= */}

      <div className="user-role-tabs">

        <button
          className={
            activeTab === "users"
              ? "active"
              : ""
          }
          onClick={() =>
            setActiveTab("users")
          }
        >
          <Icon
            type="users"
            size={16}
          />

          Users

          <span>
            {users.length}
          </span>
        </button>

        <button
          className={
            activeTab === "roles"
              ? "active"
              : ""
          }
          onClick={() =>
            setActiveTab("roles")
          }
        >
          <Icon
            type="settings"
            size={16}
          />

          Roles

          <span>
            {roles.length}
          </span>
        </button>

      </div>

      {/* =================================================
          USERS TAB
      ================================================= */}

      {activeTab === "users" && (
        <>

          {/* =================================================
              USER STATISTICS
          ================================================= */}

          <div className="user-role-stats">

            <div className="user-role-stat">

              <div className="user-role-stat-icon blue">
                <Icon
                  type="users"
                  size={19}
                />
              </div>

              <div>
                <span>
                  Total Users
                </span>

                <strong>
                  {users.length}
                </strong>
              </div>

            </div>

            <div className="user-role-stat">

              <div className="user-role-stat-icon green">
                <Icon
                  type="check"
                  size={19}
                />
              </div>

              <div>
                <span>
                  Active Users
                </span>

                <strong>
                  {
                    users.filter(
                      (user) =>
                        user.status ===
                        "Active"
                    ).length
                  }
                </strong>
              </div>

            </div>

            <div className="user-role-stat">

              <div className="user-role-stat-icon purple">
                <Icon
                  type="settings"
                  size={19}
                />
              </div>

              <div>
                <span>
                  Roles
                </span>

                <strong>
                  {roles.length}
                </strong>
              </div>

            </div>

          </div>

          {/* =================================================
              USER TABLE PANEL
          ================================================= */}

          <div className="user-role-panel">

            {/* FILTERS */}

            <div className="user-role-filters">

              <div className="user-role-search">

                <Icon
                  type="search"
                  size={16}
                />

                <input
                  type="text"
                  placeholder="Search users..."
                  value={search}
                  onChange={(event) =>
                    setSearch(
                      event.target.value
                    )
                  }
                />

              </div>

              <select
                value={roleFilter}
                onChange={(event) =>
                  setRoleFilter(
                    event.target.value
                  )
                }
              >
                <option>
                  All Roles
                </option>

                <option>
                  Administrator
                </option>

                <option>
                  Lab Administrator
                </option>

                <option>
                  Technician
                </option>

                <option>
                  Operator
                </option>

              </select>

              <select
                value={statusFilter}
                onChange={(event) =>
                  setStatusFilter(
                    event.target.value
                  )
                }
              >
                <option>
                  All Status
                </option>

                <option>
                  Active
                </option>

                <option>
                  Inactive
                </option>

              </select>

              <button
                className="user-reset-button"
                onClick={resetFilters}
              >
                Reset
              </button>

            </div>

            {/* TABLE */}

            <div className="table-scroll">

              <table>

                <thead>

                  <tr>
                    <th>User</th>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Last Login</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>

                </thead>

                <tbody>

                  {filteredUsers.length === 0 ? (

                    <tr>
                      <td
                        colSpan="7"
                        className="user-empty-cell"
                      >
                        No users found.
                      </td>
                    </tr>

                  ) : (

                    filteredUsers.map(
                      (user) => (
                        <tr key={user.id}>

                          <td>

                            <div className="user-name-cell">

                              <div className="user-avatar">
                                {user.name
                                  .charAt(0)
                                  .toUpperCase()}
                              </div>

                              <strong>
                                {user.name}
                              </strong>

                            </div>

                          </td>

                          <td>
                            {user.username}
                          </td>

                          <td>
                            {user.email}
                          </td>

                          <td>
                            <span className="user-role-badge">
                              {user.role}
                            </span>
                          </td>

                          <td>
                            {user.lastLogin}
                          </td>

                          <td>

                            <span
                              className={
                                `user-status ${
                                  user.status ===
                                  "Active"
                                    ? "active"
                                    : "inactive"
                                }`
                              }
                            >
                              {user.status}
                            </span>

                          </td>

                          <td>

                            <div className="user-actions">

                              <button
                                className="user-action-edit"
                                title="Edit User"
                              >
                                <Icon
                                  type="edit"
                                  size={15}
                                />
                              </button>

                              <button
                                className="user-action-delete"
                                title="Delete User"
                                onClick={() =>
                                  handleDeleteUser(
                                    user.id
                                  )
                                }
                              >
                                <Icon
                                  type="trash"
                                  size={15}
                                />
                              </button>

                            </div>

                          </td>

                        </tr>
                      )
                    )

                  )}

                </tbody>

              </table>

            </div>

          </div>

        </>
      )}

      {/* =================================================
          ROLES TAB
      ================================================= */}

      {activeTab === "roles" && (
        <div className="roles-grid">

          {roles.map((role) => (

            <div
              className="role-card"
              key={role.name}
            >

              <div className="role-card-header">

                <div className="role-icon">
                  <Icon
                    type="settings"
                    size={19}
                  />
                </div>

                <div>

                  <h3>
                    {role.name}
                  </h3>

                  <span>
                    {role.users} user
                    {role.users !== 1
                      ? "s"
                      : ""}
                  </span>

                </div>

              </div>

              <p className="role-description">
                {role.description}
              </p>

              <div className="role-permissions-title">
                Permissions
              </div>

              <div className="role-permissions">

                {role.permissions.map(
                  (permission) => (

                    <span
                      key={permission}
                    >
                      <Icon
                        type="check"
                        size={12}
                      />

                      {permission}
                    </span>

                  )
                )}

              </div>

            </div>

          ))}

        </div>
      )}

      {/* =================================================
          ADD USER MODAL
      ================================================= */}

      {showAddUser && (

        <div className="modal-overlay">

          <div className="user-modal">

            <div className="user-modal-header">

              <div>

                <h3>
                  Add New User
                </h3>

                <p>
                  Create a new SLMS user
                  account.
                </p>

              </div>

              <button
                className="user-modal-close"
                onClick={() =>
                  setShowAddUser(false)
                }
              >
                <Icon
                  type="close"
                  size={18}
                />
              </button>

            </div>

            <form
              onSubmit={handleAddUser}
            >

              <div className="user-modal-body">

                <div className="settings-field">

                  <label>
                    Full Name
                  </label>

                  <input
                    type="text"
                    value={newUser.name}
                    onChange={(event) =>
                      setNewUser({
                        ...newUser,
                        name:
                          event.target.value,
                      })
                    }
                    placeholder="Enter full name"
                  />

                </div>

                <div className="settings-field">

                  <label>
                    Username
                  </label>

                  <input
                    type="text"
                    value={
                      newUser.username
                    }
                    onChange={(event) =>
                      setNewUser({
                        ...newUser,
                        username:
                          event.target.value,
                      })
                    }
                    placeholder="Enter username"
                  />

                </div>

                <div className="settings-field">

                  <label>
                    Email
                  </label>

                  <input
                    type="email"
                    value={
                      newUser.email
                    }
                    onChange={(event) =>
                      setNewUser({
                        ...newUser,
                        email:
                          event.target.value,
                      })
                    }
                    placeholder="Enter email"
                  />

                </div>

                <div className="settings-field">

                  <label>
                    Role
                  </label>

                  <select
                    value={
                      newUser.role
                    }
                    onChange={(event) =>
                      setNewUser({
                        ...newUser,
                        role:
                          event.target.value,
                      })
                    }
                  >
                    <option>
                      Administrator
                    </option>

                    <option>
                      Lab Administrator
                    </option>

                    <option>
                      Technician
                    </option>

                    <option>
                      Operator
                    </option>

                  </select>

                </div>

                <div className="settings-field">

                  <label>
                    Status
                  </label>

                  <select
                    value={
                      newUser.status
                    }
                    onChange={(event) =>
                      setNewUser({
                        ...newUser,
                        status:
                          event.target.value,
                      })
                    }
                  >
                    <option>
                      Active
                    </option>

                    <option>
                      Inactive
                    </option>

                  </select>

                </div>

              </div>

              <div className="user-modal-footer">

                <button
                  type="button"
                  className="user-cancel-button"
                  onClick={() =>
                    setShowAddUser(false)
                  }
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="user-create-button"
                >
                  Create User
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  );
}

export default UserRoleManagement;