import Icon from "./Icon";

function Sidebar({ active, navigate, logout}) {
  const navItems = [
    ["home", "Dashboard", "dashboard"],
    ["computer", "Computer List", "computers"],
    ["details", "Computer Details", "details"],
    ["software", "Software Inventory", "software"],
    ["issue", "Issue Management", "issues"],
    ["maintenance", "Maintenance Records", "maintenance"],
    ["reports", "Reports", "reports"],
    ["settings", "Settings", "settings"],
    ["users", "User & Role Management", "users"],
  ];

  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-monitor">
          <span>〰</span>
        </div>

        <div>
          <div className="brand-name">SLMS</div>

          <div className="brand-sub">
            Smart Lab Management
            <br />
            System
          </div>
        </div>
      </div>

      <div className="navigation">
        {navItems.map(([ic, label, id]) => (
          <button
            key={id}
            className={`nav-item ${
              active === id ? "active" : ""
            }`}
            onClick={() => navigate(id)}
          >
            <Icon type={ic} size={22} />
            <span>{label}</span>
          </button>
        ))}

        <button
          className="nav-item"
          onClick={logout}
        >
          <Icon type="logout" size={22} />
          <span>Logout</span>
        </button>
      </div>

      <div className="system-box">
        <div className="system-title">
          <span className="green-dot" />
          System Status
        </div>

        <div className="system-ok">
          All systems operational
        </div>

        <div className="shield">✓</div>
      </div>
    </aside>
  );
}

export default Sidebar;