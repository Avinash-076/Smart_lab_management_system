import Icon from "./Icon";

function Header({
  active,
  navItems,
  sidebarOpen,
  setSidebarOpen,
  search,
  setSearch,
  bellOpen,
  setBellOpen,
  profileOpen,
  setProfileOpen,
  setFilterOpen,
  navigate,
}) {
  return (
    <header className="header">
      <div className="header-title">

        {/* MENU */}
        <button
          className="menu"
          onClick={() =>
            setSidebarOpen((prev) => !prev)
          }
          title={
            sidebarOpen
              ? "Collapse Sidebar"
              : "Expand Sidebar"
          }
        >
          <Icon type="menu" size={25} />
        </button>

        {/* PAGE TITLE */}
        <h1>
          {active === "computers"
            ? "Computer List"
            : navItems.find(
                (x) => x[2] === active
              )?.[1] || "SLMS"}
        </h1>
      </div>

      <div className="header-right">

        {/* SEARCH */}
        <div className="header-search">
          <input
            placeholder="Search computers..."
            value={search}
            onChange={(e) =>
              setSearch(e.target.value)
            }
          />

          <Icon type="search" size={19} />
        </div>

        {/* NOTIFICATION */}
        <div className="header-popup-wrapper">
          <button
            className="bell"
            onClick={() => {
              setBellOpen((p) => !p);
              setFilterOpen(false);
              setProfileOpen(false);
            }}
          >
            <Icon type="bell" size={24} />
            <span>3</span>
          </button>

          {bellOpen && (
            <div className="slms-dropdown notification-dropdown">
              <div className="dropdown-heading">
                <div>
                  <b>Notifications</b>
                  <small>
                    Recent system activity
                  </small>
                </div>

                <span className="notification-count">
                  3
                </span>
              </div>

              <div className="notification-item">
                <span className="notification-dot green" />

                <div>
                  <b>System Status</b>

                  <p>
                    All systems operational.
                  </p>

                  <small>
                    Just now
                  </small>
                </div>
              </div>

              <div className="notification-item">
                <span className="notification-dot orange" />

                <div>
                  <b>PC-05 Offline</b>

                  <p>
                    PC-05 is currently offline.
                  </p>

                  <small>
                    5 minutes ago
                  </small>
                </div>
              </div>

              <div className="notification-item">
                <span className="notification-dot blue" />

                <div>
                  <b>Lab Monitoring</b>

                  <p>
                    Lab monitoring is active.
                  </p>

                  <small>
                    10 minutes ago
                  </small>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ADMIN */}
        <div className="header-popup-wrapper">
          <button
            className="admin"
            onClick={() => {
              setProfileOpen((p) => !p);
              setBellOpen(false);
              setFilterOpen(false);
            }}
          >
            <div className="avatar">
              <Icon type="users" size={22} />
            </div>

            <div>
              <b>Admin</b>
              <small>Administrator</small>
            </div>
          </button>

          {profileOpen && (
            <div className="slms-dropdown admin-dropdown">
              <div className="admin-dropdown-header">
                <div className="admin-big-avatar">
                  <Icon type="users" size={24} />
                </div>

                <div>
                  <b>Admin</b>
                  <small>Administrator</small>
                </div>
              </div>

              <div className="dropdown-divider" />

              <button
                className="dropdown-action"
                onClick={() => {
                  navigate("settings");
                }}
              >
                <span className="dropdown-action-icon">
                  <Icon
                    type="settings"
                    size={18}
                  />
                </span>

                <span>
                  <b>Settings</b>

                  <small>
                    Manage system settings
                  </small>
                </span>
              </button>

              <button
                className="dropdown-action logout-action"
                onClick={() => {
                  navigate("logout");
                }}
              >
                <span className="dropdown-action-icon">
                  <Icon
                    type="logout"
                    size={18}
                  />
                </span>

                <span>
                  <b>Logout</b>

                  <small>
                    Sign out of SLMS
                  </small>
                </span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;