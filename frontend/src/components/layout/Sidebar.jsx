import { useState, useEffect, useRef } from "react";
import Icon from "../ui/Icon";
import { MonitorCheckIcon } from "../ui/Icons";
import { parseJwt, getAccessToken } from "../../services/authService";
import "./Sidebar.css";

function getInitialUserInfo() {
  try {
    const token = getAccessToken();
    if (token) {
      const decoded = parseJwt(token);
      if (decoded) {
        const rawUsername =
          decoded.username ||
          (decoded.sub && isNaN(Number(decoded.sub)) ? decoded.sub : "Admin");
        const rawRole = decoded.role || "Administrator";
        return {
          name: rawUsername.charAt(0).toUpperCase() + rawUsername.slice(1),
          role: rawRole.charAt(0).toUpperCase() + rawRole.slice(1),
          initial: rawUsername.charAt(0).toUpperCase(),
        };
      }
    }
  } catch {
    // Fallback
  }
  return {
    name: "Admin",
    role: "Administrator",
    initial: "A",
  };
}

function Sidebar({ active, navigate, logout, sidebarOpen = true }) {
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const userMenuRef = useRef(null);
  const [userInfo] = useState(getInitialUserInfo);

  // Close user dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setUserDropdownOpen(false);
      }
    }
    if (userDropdownOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [userDropdownOpen]);

  const navItems = [
    ["grid", "Dashboard", "dashboard"],
    ["computer", "Computers", "computers"],
    ["remote", "Global Remote Control", "remote-control"],
    ["software", "Software Inventory", "software"],
    ["issue", "Issue Management", "issues"],
    ["maintenance", "Maintenance Records", "maintenance"],
    ["reports", "Reports", "reports"],
    ["audit", "Audit Logs", "audit"],
    ["settings", "Settings", "settings"],
  ];

  return (
    <aside className={`sidebar ${sidebarOpen ? "" : "collapsed"}`}>
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="sidebar-brand__logo" title="SLMS">
          <MonitorCheckIcon size={24} />
        </div>

        <div className="sidebar-brand__text">
          <span className="sidebar-brand__title">SLMS</span>
          <span className="sidebar-brand__subtitle">Smart Lab Management System</span>
        </div>
      </div>

      {/* Navigation List */}
      <nav className="sidebar-nav" aria-label="Main navigation">
        {navItems.map(([ic, label, id]) => {
          const isActive = active === id || (id === "computers" && active === "details");
          return (
            <button
              key={id}
              type="button"
              className={`sidebar-nav__item ${isActive ? "active" : ""}`}
              onClick={() => {
                navigate(id);
                setUserDropdownOpen(false);
              }}
              title={label}
            >
              <span className="sidebar-nav__icon">
                <Icon type={ic} size={20} />
              </span>
              <span className="sidebar-nav__label">{label}</span>
            </button>
          );
        })}
      </nav>

      {/* User Profile Section at Bottom */}
      <div className="sidebar-user" ref={userMenuRef}>
        <button
          type="button"
          className={`sidebar-user__card ${userDropdownOpen ? "open" : ""}`}
          onClick={() => setUserDropdownOpen((prev) => !prev)}
          aria-expanded={userDropdownOpen}
          aria-haspopup="true"
          title={`${userInfo.name} (${userInfo.role})`}
        >
          <div className="sidebar-user__avatar" aria-hidden="true">
            {userInfo.initial}
          </div>

          <div className="sidebar-user__info">
            <span className="sidebar-user__name">{userInfo.name}</span>
            <span className="sidebar-user__role">{userInfo.role}</span>
          </div>

          <span className="sidebar-user__chevron" aria-hidden="true">
            <Icon type="chevron-down" size={16} />
          </span>
        </button>

        {userDropdownOpen && (
          <div className="sidebar-user__menu" role="menu">
            <div className="sidebar-user__menu-header">
              <div className="sidebar-user__menu-name">{userInfo.name}</div>
              <div className="sidebar-user__menu-role">{userInfo.role}</div>
            </div>

            <button
              type="button"
              className="sidebar-user__menu-item"
              role="menuitem"
              onClick={() => {
                navigate("settings");
                setUserDropdownOpen(false);
              }}
            >
              <Icon type="settings" size={16} />
              <span>Settings</span>
            </button>

            <button
              type="button"
              className="sidebar-user__menu-item logout"
              role="menuitem"
              onClick={() => {
                setUserDropdownOpen(false);
                logout();
              }}
            >
              <Icon type="logout" size={16} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </aside>
  );
}

export default Sidebar;