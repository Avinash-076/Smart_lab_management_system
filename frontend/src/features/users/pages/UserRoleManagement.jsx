import { useState, useEffect, useCallback, useMemo } from "react";
import Icon from "../../../components/ui/Icon";
import {
  getUsers,
  createUser,
  updateUser,
  deleteUser,
  getRoles,
  getPermissions,
  updateRolePermissions,
  getCurrentUserProfile,
} from "../../../services/api";

function UserRoleManagement() {
  // Navigation tabs
  const [activeTab, setActiveTab] = useState("users");

  // Current logged in user info
  const [currentUser, setCurrentUser] = useState(null);

  // Users State
  const [users, setUsers] = useState([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [totalPages, setTotalPages] = useState(1);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [userError, setUserError] = useState(null);

  // Roles & Permissions State
  const [roles, setRoles] = useState([]);
  const [permissionsCatalog, setPermissionsCatalog] = useState([]);
  const [rolesError, setRolesError] = useState(null);

  // Filter States
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("All Roles");
  const [statusFilter, setStatusFilter] = useState("All Status");

  // Modals
  const [showAddUser, setShowAddUser] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [deletingUser, setDeletingUser] = useState(null);
  const [permissionRole, setPermissionRole] = useState(null);
  const [permissionMatrix, setPermissionMatrix] = useState({});

  // Form States
  const [newUser, setNewUser] = useState({
    username: "",
    full_name: "",
    email: "",
    password: "",
    role_id: "",
    is_active: true,
  });
  const [editFormData, setEditFormData] = useState({
    full_name: "",
    email: "",
    password: "",
    role_id: "",
    is_active: true,
  });

  // Action status / feedback
  const [formError, setFormError] = useState(null);
  const [formSubmitting, setFormSubmitting] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (msg, isError = false) => {
    setToastMessage({ text: msg, isError });
    setTimeout(() => {
      setToastMessage(null);
    }, 4000);
  };

  /* =====================================================
     DATA FETCH EFFECTS (ESLint Compliant)
  ===================================================== */

  useEffect(() => {
    let active = true;
    async function initProfileAndRoles() {
      try {
        const [profile, rolesData, permsData] = await Promise.all([
          getCurrentUserProfile().catch(() => null),
          getRoles().catch(() => []),
          getPermissions().catch(() => []),
        ]);
        if (active) {
          if (profile) setCurrentUser(profile);
          setRoles(Array.isArray(rolesData) ? rolesData : []);
          setPermissionsCatalog(Array.isArray(permsData) ? permsData : []);
        }
      } catch (err) {
        if (active) {
          setRolesError(err.message || "Failed to load roles and permissions");
        }
      }
    }

    initProfileAndRoles();
    return () => {
      active = false;
    };
  }, []);

  const fetchUsers = useCallback(async () => {
    setLoadingUsers(true);
    setUserError(null);
    try {
      const options = {
        page,
        limit,
      };
      if (search.trim()) options.search = search.trim();
      if (roleFilter !== "All Roles") {
        const found = roles.find((r) => r.name === roleFilter);
        if (found) options.role_id = found.id;
      }
      if (statusFilter === "Active") options.status = "active";
      else if (statusFilter === "Inactive") options.status = "inactive";

      const res = await getUsers(options);
      if (res && Array.isArray(res.items)) {
        setUsers(res.items);
        setTotalUsers(res.total || 0);
        setTotalPages(res.total_pages || 1);
      } else if (Array.isArray(res)) {
        setUsers(res);
        setTotalUsers(res.length);
        setTotalPages(1);
      } else {
        setUsers([]);
        setTotalUsers(0);
        setTotalPages(1);
      }
    } catch (err) {
      setUserError(err.message || "Failed to load user list");
    } finally {
      setLoadingUsers(false);
    }
  }, [page, limit, search, roleFilter, statusFilter, roles]);

  useEffect(() => {
    let active = true;
    async function loadUsersData() {
      try {
        const options = {
          page,
          limit,
        };
        if (search.trim()) options.search = search.trim();
        if (roleFilter !== "All Roles") {
          const found = roles.find((r) => r.name === roleFilter);
          if (found) options.role_id = found.id;
        }
        if (statusFilter === "Active") options.status = "active";
        else if (statusFilter === "Inactive") options.status = "inactive";

        const res = await getUsers(options);
        if (active) {
          if (res && Array.isArray(res.items)) {
            setUsers(res.items);
            setTotalUsers(res.total || 0);
            setTotalPages(res.total_pages || 1);
          } else if (Array.isArray(res)) {
            setUsers(res);
            setTotalUsers(res.length);
            setTotalPages(1);
          } else {
            setUsers([]);
            setTotalUsers(0);
            setTotalPages(1);
          }
          setLoadingUsers(false);
        }
      } catch (err) {
        if (active) {
          setUserError(err.message || "Failed to load user list");
          setLoadingUsers(false);
        }
      }
    }

    loadUsersData();
    return () => {
      active = false;
    };
  }, [page, limit, search, roleFilter, statusFilter, roles]);

  const reloadRoles = async () => {
    try {
      const [rolesData, permsData] = await Promise.all([
        getRoles(),
        getPermissions().catch(() => []),
      ]);
      setRoles(Array.isArray(rolesData) ? rolesData : []);
      setPermissionsCatalog(Array.isArray(permsData) ? permsData : []);
    } catch (err) {
      setRolesError(err.message || "Failed to reload roles");
    }
  };

  // Derived stats
  const activeCount = useMemo(() => {
    return users.filter((u) => u.is_active).length;
  }, [users]);

  /* =====================================================
     USER ACTIONS
  ===================================================== */

  const handleOpenAddUser = () => {
    const defaultRoleId = roles.length > 0 ? roles[0].id : "";
    setNewUser({
      username: "",
      full_name: "",
      email: "",
      password: "",
      role_id: defaultRoleId,
      is_active: true,
    });
    setFormError(null);
    setShowAddUser(true);
  };

  const handleCreateUserSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);

    if (!newUser.username.trim()) {
      setFormError("Username is required");
      return;
    }
    if (!newUser.password || newUser.password.length < 6) {
      setFormError("Password must be at least 6 characters");
      return;
    }
    if (!newUser.role_id) {
      setFormError("Please select a role");
      return;
    }

    setFormSubmitting(true);
    try {
      const payload = {
        username: newUser.username.trim(),
        password: newUser.password,
        role_id: parseInt(newUser.role_id, 10),
        is_active: newUser.is_active,
      };
      if (newUser.full_name.trim()) payload.full_name = newUser.full_name.trim();
      if (newUser.email.trim()) payload.email = newUser.email.trim();

      await createUser(payload);
      showToast(`User '${newUser.username}' created successfully`);
      setShowAddUser(false);
      fetchUsers();
      reloadRoles();
    } catch (err) {
      setFormError(err.message || "Failed to create user");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleOpenEditUser = (user) => {
    setEditingUser(user);
    setEditFormData({
      full_name: user.full_name || "",
      email: user.email || "",
      password: "",
      role_id: user.role_id || "",
      is_active: user.is_active ?? true,
    });
    setFormError(null);
  };

  const handleUpdateUserSubmit = async (e) => {
    e.preventDefault();
    if (!editingUser) return;
    setFormError(null);

    setFormSubmitting(true);
    try {
      const payload = {
        role_id: parseInt(editFormData.role_id, 10),
        is_active: editFormData.is_active,
        full_name: editFormData.full_name.trim() || null,
        email: editFormData.email.trim() || null,
      };
      if (editFormData.password && editFormData.password.length >= 6) {
        payload.password = editFormData.password;
      } else if (editFormData.password && editFormData.password.length < 6) {
        setFormError("Password must be at least 6 characters if updating");
        setFormSubmitting(false);
        return;
      }

      await updateUser(editingUser.id, payload);
      showToast(`User '${editingUser.username}' updated successfully`);
      setEditingUser(null);
      fetchUsers();
      reloadRoles();
    } catch (err) {
      setFormError(err.message || "Failed to update user");
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleDeleteUserConfirm = async () => {
    if (!deletingUser) return;
    setFormSubmitting(true);
    try {
      await deleteUser(deletingUser.id);
      showToast(`User '${deletingUser.username}' deleted successfully`);
      setDeletingUser(null);
      fetchUsers();
      reloadRoles();
    } catch (err) {
      showToast(err.message || "Failed to delete user", true);
    } finally {
      setFormSubmitting(false);
    }
  };

  /* =====================================================
     ROLE PERMISSION MATRIX ACTIONS
  ===================================================== */

  const handleOpenPermissions = (role) => {
    setPermissionRole(role);
    const matrix = {};
    if (Array.isArray(role.permissions)) {
      role.permissions.forEach((p) => {
        matrix[p.action_code] = p.allowed;
      });
    }
    setPermissionMatrix(matrix);
    setFormError(null);
  };

  const handleTogglePermission = (actionCode) => {
    setPermissionMatrix((prev) => ({
      ...prev,
      [actionCode]: !prev[actionCode],
    }));
  };

  const handleSavePermissions = async () => {
    if (!permissionRole) return;
    setFormSubmitting(true);
    setFormError(null);
    try {
      const payload = Object.keys(permissionMatrix).map((code) => ({
        action_code: code,
        allowed: !!permissionMatrix[code],
      }));
      await updateRolePermissions(permissionRole.id, payload);
      showToast(`Permissions updated for role '${permissionRole.name}'`);
      setPermissionRole(null);
      reloadRoles();
    } catch (err) {
      setFormError(err.message || "Failed to update role permissions");
    } finally {
      setFormSubmitting(false);
    }
  };

  const resetFilters = () => {
    setSearch("");
    setRoleFilter("All Roles");
    setStatusFilter("All Status");
    setPage(1);
  };

  // Group permission catalog by category
  const groupedPermissions = useMemo(() => {
    const groups = {};
    permissionsCatalog.forEach((p) => {
      const cat = p.category || "General";
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(p);
    });
    return groups;
  }, [permissionsCatalog]);

  return (
    <div className="content">
      {/* Toast Notification */}
      {toastMessage && (
        <div
          className={`settings-success ${toastMessage.isError ? "error" : ""}`}
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            zIndex: 10000,
            boxShadow: "0 10px 25px rgba(0,0,0,0.15)",
            background: toastMessage.isError ? "#fef2f2" : "#ecfdf5",
            color: toastMessage.isError ? "#991b1b" : "#065f46",
            border: `1px solid ${toastMessage.isError ? "#fecaca" : "#a7f3d0"}`,
          }}
        >
          <Icon type={toastMessage.isError ? "close" : "check"} size={17} />
          {toastMessage.text}
        </div>
      )}

      {/* =================================================
          PAGE HEADER
      ================================================= */}
      <div className="page-top">
        <div>
          <h2>User &amp; Role Management</h2>
          <p>
            Manage SLMS user accounts, system roles, and fine-grained access control matrices.
          </p>
        </div>

        {activeTab === "users" && (
          <button className="user-add-button" onClick={handleOpenAddUser}>
            <Icon type="plus" size={16} />
            Add User
          </button>
        )}
      </div>

      {/* =================================================
          TABS
      ================================================= */}
      <div className="user-role-tabs">
        <button
          className={activeTab === "users" ? "active" : ""}
          onClick={() => setActiveTab("users")}
        >
          <Icon type="users" size={16} />
          Users
          <span>{totalUsers}</span>
        </button>

        <button
          className={activeTab === "roles" ? "active" : ""}
          onClick={() => setActiveTab("roles")}
        >
          <Icon type="settings" size={16} />
          Roles &amp; Permissions
          <span>{roles.length}</span>
        </button>
      </div>

      {/* =================================================
          USERS TAB
      ================================================= */}
      {activeTab === "users" && (
        <>
          {/* USER STATISTICS */}
          <div className="user-role-stats">
            <div className="user-role-stat">
              <div className="user-role-stat-icon blue">
                <Icon type="users" size={19} />
              </div>
              <div>
                <span>Total Users</span>
                <strong>{totalUsers}</strong>
              </div>
            </div>

            <div className="user-role-stat">
              <div className="user-role-stat-icon green">
                <Icon type="check" size={19} />
              </div>
              <div>
                <span>Active Users (Page)</span>
                <strong>{activeCount}</strong>
              </div>
            </div>

            <div className="user-role-stat">
              <div className="user-role-stat-icon purple">
                <Icon type="settings" size={19} />
              </div>
              <div>
                <span>Defined Roles</span>
                <strong>{roles.length}</strong>
              </div>
            </div>
          </div>

          {/* USER TABLE PANEL */}
          <div className="user-role-panel">
            {/* FILTERS */}
            <div className="user-role-filters">
              <div className="user-role-search">
                <Icon type="search" size={16} />
                <input
                  type="text"
                  placeholder="Search by username, name, or email..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                />
              </div>

              <select
                value={roleFilter}
                onChange={(e) => {
                  setRoleFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="All Roles">All Roles</option>
                {roles.map((r) => (
                  <option key={r.id} value={r.name}>
                    {r.name}
                  </option>
                ))}
              </select>

              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="All Status">All Status</option>
                <option value="Active">Active</option>
                <option value="Inactive">Inactive</option>
              </select>

              <button className="user-reset-button" onClick={resetFilters}>
                Reset
              </button>

              <button
                className="user-reset-button"
                onClick={fetchUsers}
                title="Refresh user list"
                style={{ display: "flex", alignItems: "center", gap: "4px" }}
              >
                <Icon type="refresh" size={14} />
                Refresh
              </button>
            </div>

            {/* ERROR BANNER */}
            {userError && (
              <div
                style={{
                  padding: "12px 16px",
                  margin: "16px 20px",
                  background: "#fef2f2",
                  border: "1px solid #fecaca",
                  borderRadius: "8px",
                  color: "#991b1b",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  fontSize: "12px",
                }}
              >
                <span>{userError}</span>
                <button
                  onClick={fetchUsers}
                  style={{
                    border: "none",
                    background: "none",
                    color: "#2563eb",
                    cursor: "pointer",
                    fontWeight: 600,
                  }}
                >
                  Retry
                </button>
              </div>
            )}

            {/* TABLE */}
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Username</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Account Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>

                <tbody>
                  {loadingUsers ? (
                    <tr>
                      <td colSpan="6" className="user-empty-cell">
                        Loading users from database...
                      </td>
                    </tr>
                  ) : users.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="user-empty-cell">
                        No users found matching filter criteria.
                      </td>
                    </tr>
                  ) : (
                    users.map((user) => (
                      <tr key={user.id}>
                        <td>
                          <div className="user-name-cell">
                            <div
                              className="user-avatar"
                              style={{
                                background: user.is_active ? "#2563eb" : "#94a3b8",
                                color: "#ffffff",
                              }}
                            >
                              {(user.full_name || user.username).charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <strong>{user.full_name || user.username}</strong>
                              {currentUser && currentUser.id === user.id && (
                                <span
                                  style={{
                                    marginLeft: "6px",
                                    fontSize: "9px",
                                    background: "#e0e7ff",
                                    color: "#3730a3",
                                    padding: "2px 6px",
                                    borderRadius: "4px",
                                    fontWeight: 600,
                                  }}
                                >
                                  You
                                </span>
                              )}
                            </div>
                          </div>
                        </td>

                        <td>
                          <code style={{ fontSize: "11px", color: "#1e293b" }}>
                            {user.username}
                          </code>
                        </td>

                        <td>{user.email || <span style={{ color: "#94a3b8" }}>—</span>}</td>

                        <td>
                          <span
                            className="user-role-badge"
                            style={{
                              background:
                                user.role_name === "Administrator" ? "#fef3c7" : "#f1f5f9",
                              color:
                                user.role_name === "Administrator" ? "#92400e" : "#475569",
                              border:
                                user.role_name === "Administrator"
                                  ? "1px solid #fde68a"
                                  : "1px solid #e2e8f0",
                              fontWeight: 600,
                            }}
                          >
                            {user.role_name || `Role #${user.role_id}`}
                          </span>
                        </td>

                        <td>
                          <span
                            className={`user-status ${user.is_active ? "active" : "inactive"}`}
                          >
                            {user.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>

                        <td>
                          <div className="user-actions">
                            <button
                              className="user-action-edit"
                              title="Edit User"
                              onClick={() => handleOpenEditUser(user)}
                            >
                              <Icon type="edit" size={15} />
                            </button>

                            <button
                              className="user-action-delete"
                              title="Delete User"
                              onClick={() => setDeletingUser(user)}
                            >
                              <Icon type="trash" size={15} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* PAGINATION */}
            {totalPages > 1 && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "14px 20px",
                  borderTop: "1px solid #edf0f4",
                  fontSize: "12px",
                  color: "#64748b",
                }}
              >
                <span>
                  Showing page {page} of {totalPages} ({totalUsers} total users)
                </span>
                <div style={{ display: "flex", gap: "8px" }}>
                  <button
                    className="user-reset-button"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    style={{ opacity: page <= 1 ? 0.5 : 1, cursor: page <= 1 ? "not-allowed" : "pointer" }}
                  >
                    Previous
                  </button>
                  <button
                    className="user-reset-button"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    style={{ opacity: page >= totalPages ? 0.5 : 1, cursor: page >= totalPages ? "not-allowed" : "pointer" }}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* =================================================
          ROLES & PERMISSIONS TAB
      ================================================= */}
      {activeTab === "roles" && (
        <>
          {rolesError && (
            <div
              style={{
                padding: "12px 16px",
                marginBottom: "20px",
                background: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "8px",
                color: "#991b1b",
                fontSize: "12px",
              }}
            >
              {rolesError}
            </div>
          )}

          <div className="roles-grid">
            {roles.map((role) => {
              const allowedPermissions = Array.isArray(role.permissions)
                ? role.permissions.filter((p) => p.allowed)
                : [];

              return (
                <div className="role-card" key={role.id}>
                  <div className="role-card-header">
                    <div
                      className="role-icon"
                      style={{
                        background: role.name === "Administrator" ? "#fef3c7" : "#eaf2ff",
                        color: role.name === "Administrator" ? "#b45309" : "#2563eb",
                      }}
                    >
                      <Icon type="settings" size={19} />
                    </div>

                    <div style={{ flex: 1 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                        }}
                      >
                        <h3>{role.name}</h3>
                        <button
                          onClick={() => handleOpenPermissions(role)}
                          style={{
                            border: "1px solid #cbd5e1",
                            background: "#ffffff",
                            padding: "4px 10px",
                            borderRadius: "6px",
                            fontSize: "11px",
                            fontWeight: 600,
                            color: "#334155",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <Icon type="edit" size={12} />
                          Edit Matrix
                        </button>
                      </div>

                      <span>
                        {role.user_count ?? 0} user
                        {role.user_count !== 1 ? "s" : ""} assigned
                      </span>
                    </div>
                  </div>

                  <p className="role-description">
                    {role.description || "Configured system security role."}
                  </p>

                  <div className="role-permissions-title">
                    Granted Permissions ({allowedPermissions.length})
                  </div>

                  <div className="role-permissions">
                    {allowedPermissions.length === 0 ? (
                      <span style={{ color: "#94a3b8", background: "#f8fafc" }}>
                        No permissions granted
                      </span>
                    ) : (
                      allowedPermissions.map((permission) => (
                        <span key={permission.action_code}>
                          <Icon type="check" size={12} />
                          {permission.action_code}
                        </span>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* =================================================
          ADD USER MODAL
      ================================================= */}
      {showAddUser && (
        <div className="modal-overlay">
          <div className="user-modal">
            <div className="user-modal-header">
              <div>
                <h3>Add New User</h3>
                <p>Create a new verified SLMS user account.</p>
              </div>
              <button className="user-modal-close" onClick={() => setShowAddUser(false)}>
                <Icon type="close" size={18} />
              </button>
            </div>

            <form onSubmit={handleCreateUserSubmit}>
              <div className="user-modal-body">
                {formError && (
                  <div
                    style={{
                      gridColumn: "1 / -1",
                      padding: "10px 14px",
                      background: "#fef2f2",
                      border: "1px solid #fecaca",
                      borderRadius: "6px",
                      color: "#991b1b",
                      fontSize: "12px",
                    }}
                  >
                    {formError}
                  </div>
                )}

                <div className="settings-field">
                  <label>Full Name</label>
                  <input
                    type="text"
                    value={newUser.full_name}
                    onChange={(e) => setNewUser({ ...newUser, full_name: e.target.value })}
                    placeholder="e.g. Daya Sagar"
                  />
                </div>

                <div className="settings-field">
                  <label>Username *</label>
                  <input
                    type="text"
                    required
                    value={newUser.username}
                    onChange={(e) => setNewUser({ ...newUser, username: e.target.value })}
                    placeholder="e.g. dsagar"
                  />
                </div>

                <div className="settings-field">
                  <label>Email Address</label>
                  <input
                    type="email"
                    value={newUser.email}
                    onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                    placeholder="e.g. dsagar@slms.local"
                  />
                </div>

                <div className="settings-field">
                  <label>Password * (min 6 chars)</label>
                  <input
                    type="password"
                    required
                    value={newUser.password}
                    onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                    placeholder="••••••••"
                  />
                </div>

                <div className="settings-field">
                  <label>Assigned Role *</label>
                  <select
                    value={newUser.role_id}
                    onChange={(e) => setNewUser({ ...newUser, role_id: e.target.value })}
                  >
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="settings-field">
                  <label>Account Status</label>
                  <select
                    value={newUser.is_active ? "active" : "inactive"}
                    onChange={(e) =>
                      setNewUser({ ...newUser, is_active: e.target.value === "active" })
                    }
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="user-modal-footer">
                <button
                  type="button"
                  className="user-cancel-button"
                  onClick={() => setShowAddUser(false)}
                  disabled={formSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="user-create-button"
                  disabled={formSubmitting}
                >
                  {formSubmitting ? "Creating..." : "Create User"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================
          EDIT USER MODAL
      ================================================= */}
      {editingUser && (
        <div className="modal-overlay">
          <div className="user-modal">
            <div className="user-modal-header">
              <div>
                <h3>Edit User: {editingUser.username}</h3>
                <p>Modify user profile, role assignment, and access state.</p>
              </div>
              <button className="user-modal-close" onClick={() => setEditingUser(null)}>
                <Icon type="close" size={18} />
              </button>
            </div>

            <form onSubmit={handleUpdateUserSubmit}>
              <div className="user-modal-body">
                {formError && (
                  <div
                    style={{
                      gridColumn: "1 / -1",
                      padding: "10px 14px",
                      background: "#fef2f2",
                      border: "1px solid #fecaca",
                      borderRadius: "6px",
                      color: "#991b1b",
                      fontSize: "12px",
                    }}
                  >
                    {formError}
                  </div>
                )}

                <div className="settings-field">
                  <label>Full Name</label>
                  <input
                    type="text"
                    value={editFormData.full_name}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, full_name: e.target.value })
                    }
                    placeholder="Full Name"
                  />
                </div>

                <div className="settings-field">
                  <label>Email Address</label>
                  <input
                    type="email"
                    value={editFormData.email}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, email: e.target.value })
                    }
                    placeholder="user@slms.local"
                  />
                </div>

                <div className="settings-field">
                  <label>New Password (leave blank to keep current)</label>
                  <input
                    type="password"
                    value={editFormData.password}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, password: e.target.value })
                    }
                    placeholder="••••••••"
                  />
                </div>

                <div className="settings-field">
                  <label>Assigned Role</label>
                  <select
                    value={editFormData.role_id}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, role_id: e.target.value })
                    }
                  >
                    {roles.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="settings-field">
                  <label>Account Status</label>
                  <select
                    value={editFormData.is_active ? "active" : "inactive"}
                    onChange={(e) =>
                      setEditFormData({
                        ...editFormData,
                        is_active: e.target.value === "active",
                      })
                    }
                  >
                    <option value="active">Active</option>
                    <option value="inactive">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="user-modal-footer">
                <button
                  type="button"
                  className="user-cancel-button"
                  onClick={() => setEditingUser(null)}
                  disabled={formSubmitting}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="user-create-button"
                  disabled={formSubmitting}
                >
                  {formSubmitting ? "Saving..." : "Save Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =================================================
          DELETE CONFIRMATION MODAL
      ================================================= */}
      {deletingUser && (
        <div className="modal-overlay">
          <div className="user-modal" style={{ maxWidth: "440px" }}>
            <div className="user-modal-header">
              <div>
                <h3>Delete User Account</h3>
                <p>Confirm permanent deletion of this user.</p>
              </div>
              <button className="user-modal-close" onClick={() => setDeletingUser(null)}>
                <Icon type="close" size={18} />
              </button>
            </div>

            <div style={{ padding: "20px", fontSize: "13px", color: "#475569", lineHeight: "1.5" }}>
              Are you sure you want to permanently delete user{" "}
              <strong>{deletingUser.username}</strong> ({deletingUser.full_name || "No name"})?
              This action will be logged in the system audit trail.
            </div>

            <div className="user-modal-footer">
              <button
                type="button"
                className="user-cancel-button"
                onClick={() => setDeletingUser(null)}
                disabled={formSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="user-create-button"
                onClick={handleDeleteUserConfirm}
                disabled={formSubmitting}
                style={{ background: "#dc2626", borderColor: "#dc2626" }}
              >
                {formSubmitting ? "Deleting..." : "Delete User"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =================================================
          PERMISSION MATRIX MODAL
      ================================================= */}
      {permissionRole && (
        <div className="modal-overlay">
          <div className="user-modal" style={{ maxWidth: "680px", width: "100%" }}>
            <div className="user-modal-header">
              <div>
                <h3>Configure Permissions: {permissionRole.name}</h3>
                <p>Enable or revoke fine-grained functional permissions for this role.</p>
              </div>
              <button className="user-modal-close" onClick={() => setPermissionRole(null)}>
                <Icon type="close" size={18} />
              </button>
            </div>

            <div style={{ padding: "20px", maxHeight: "60vh", overflowY: "auto" }}>
              {formError && (
                <div
                  style={{
                    padding: "10px 14px",
                    marginBottom: "16px",
                    background: "#fef2f2",
                    border: "1px solid #fecaca",
                    borderRadius: "6px",
                    color: "#991b1b",
                    fontSize: "12px",
                  }}
                >
                  {formError}
                </div>
              )}

              {Object.keys(groupedPermissions).map((category) => (
                <div key={category} style={{ marginBottom: "20px" }}>
                  <h4
                    style={{
                      margin: "0 0 10px 0",
                      fontSize: "13px",
                      color: "#1e293b",
                      borderBottom: "1px solid #f1f5f9",
                      paddingBottom: "4px",
                    }}
                  >
                    {category}
                  </h4>

                  <div style={{ display: "grid", gap: "8px" }}>
                    {groupedPermissions[category].map((perm) => {
                      const isChecked = !!permissionMatrix[perm.action_code];
                      const isLockedAdmin =
                        permissionRole.name === "Administrator" &&
                        ["MANAGE_ROLES", "MANAGE_USERS", "VIEW_COMPUTERS"].includes(
                          perm.action_code
                        );

                      return (
                        <label
                          key={perm.action_code}
                          style={{
                            display: "flex",
                            alignItems: "flex-start",
                            gap: "10px",
                            padding: "8px 12px",
                            background: isChecked ? "#f8fafc" : "#ffffff",
                            border: `1px solid ${isChecked ? "#cbd5e1" : "#e2e8f0"}`,
                            borderRadius: "6px",
                            cursor: isLockedAdmin ? "not-allowed" : "pointer",
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            disabled={isLockedAdmin}
                            onChange={() => handleTogglePermission(perm.action_code)}
                            style={{ marginTop: "3px" }}
                          />
                          <div style={{ flex: 1 }}>
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "6px",
                                fontWeight: 600,
                                fontSize: "12px",
                                color: "#0f172a",
                              }}
                            >
                              <span>{perm.name}</span>
                              <code style={{ fontSize: "10px", color: "#64748b" }}>
                                ({perm.action_code})
                              </code>
                              {isLockedAdmin && (
                                <span
                                  style={{
                                    fontSize: "9px",
                                    color: "#b45309",
                                    background: "#fef3c7",
                                    padding: "1px 5px",
                                    borderRadius: "3px",
                                  }}
                                >
                                  Required Root
                                </span>
                              )}
                            </div>
                            <p
                              style={{
                                margin: "2px 0 0",
                                fontSize: "11px",
                                color: "#64748b",
                                lineHeight: "1.4",
                              }}
                            >
                              {perm.description}
                            </p>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>

            <div className="user-modal-footer">
              <button
                type="button"
                className="user-cancel-button"
                onClick={() => setPermissionRole(null)}
                disabled={formSubmitting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="user-create-button"
                onClick={handleSavePermissions}
                disabled={formSubmitting}
              >
                {formSubmitting ? "Saving..." : "Save Permission Matrix"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default UserRoleManagement;