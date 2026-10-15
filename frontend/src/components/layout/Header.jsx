import { useState, useEffect, useCallback, useRef } from "react";
import Icon from "../ui/Icon";
import { parseJwt, getAccessToken } from "../../services/authService";
import {
  getNotifications,
  getNotificationStats,
  markNotificationRead,
  markAllNotificationsRead,
  clearReadNotifications,
} from "../../services/notificationService";
import "./Header.css";

function formatRelativeTime(dateStr) {
  if (!dateStr) return "Just now";
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffSec = Math.floor((now - date) / 1000);
    if (diffSec < 60) return "Just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return dateStr;
  }
}

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

const PAGE_CONFIG = {
  dashboard: {
    title: "Dashboard",
    subtitle: "Monitor and manage all laboratory computers and active alerts.",
  },
  computers: {
    title: "Computers",
    subtitle: "View and manage all lab computers.",
  },
  "remote-control": {
    title: "Global Remote Control",
    subtitle: "Manage and execute commands across multiple computers",
  },
  details: {
    title: "Computer Details",
    subtitle: "Complete computer telemetry, hardware specifications, and system status.",
  },
  software: {
    title: "Software Inventory",
    subtitle: "View applications installed on laboratory computers.",
  },
  issues: {
    title: "Issue Management",
    subtitle: "Monitor and manage problems reported by laboratory computers.",
  },
  maintenance: {
    title: "Maintenance Records",
    subtitle: "Schedule, track, and manage computer maintenance and servicing activities.",
  },
  reports: {
    title: "Reports & Analytics",
    subtitle: "Generate, inspect, and export system metrics, telemetry, and administrative logs.",
  },
  audit: {
    title: "Audit Logs",
    subtitle: "Complete traceability and security audit trail for all operations across the laboratory.",
  },
  settings: {
    title: "Settings",
    subtitle: "Configure laboratory metadata, telemetry thresholds, notification alerts, and client agent parameters.",
  },
  users: {
    title: "User & Role Management",
    subtitle: "Manage SLMS user accounts, system roles, and fine-grained access control matrices.",
  },
};

function Header({
  active,
  navItems,
  sidebarOpen,
  setSidebarOpen,
  bellOpen,
  setBellOpen,
  profileOpen,
  setProfileOpen,
  setFilterOpen,
  navigate,
  logout,
}) {
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState({
    total: 0,
    unread: 0,
    critical: 0,
    warning: 0,
    info: 0,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeFilter, setActiveFilter] = useState("all"); // 'all' or 'unread'

  const bellWrapperRef = useRef(null);
  const profileWrapperRef = useRef(null);

  const [userInfo] = useState(getInitialUserInfo);

  const fetchNotificationData = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const [notifsData, statsData] = await Promise.all([
        getNotifications({ limit: 30 }),
        getNotificationStats(),
      ]);

      setNotifications(Array.isArray(notifsData) ? notifsData : []);
      if (statsData && typeof statsData === "object") {
        setStats({
          total: statsData.total || 0,
          unread: statsData.unread || 0,
          critical: statsData.critical || 0,
          warning: statsData.warning || 0,
          info: statsData.info || 0,
        });
      }
    } catch (err) {
      console.error("Failed to load notifications:", err);
      setError(err.message || "Failed to load notifications.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let ignore = false;
    async function init() {
      try {
        setLoading(true);
        setError("");
        const [notifsData, statsData] = await Promise.all([
          getNotifications({ limit: 30 }),
          getNotificationStats(),
        ]);

        if (ignore) return;
        setNotifications(Array.isArray(notifsData) ? notifsData : []);
        if (statsData && typeof statsData === "object") {
          setStats({
            total: statsData.total || 0,
            unread: statsData.unread || 0,
            critical: statsData.critical || 0,
            warning: statsData.warning || 0,
            info: statsData.info || 0,
          });
        }
      } catch (err) {
        if (!ignore) {
          console.error("Failed to load notifications:", err);
          setError(err.message || "Failed to load notifications.");
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    init();
    return () => {
      ignore = true;
    };
  }, []);

  // Close dropdowns on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (bellWrapperRef.current && !bellWrapperRef.current.contains(event.target)) {
        setBellOpen(false);
      }
      if (profileWrapperRef.current && !profileWrapperRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [setBellOpen, setProfileOpen]);

  const handleMarkRead = async (id, e) => {
    if (e) e.stopPropagation();
    try {
      await markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
      setStats((prev) => ({
        ...prev,
        unread: Math.max(0, prev.unread - 1),
      }));
    } catch (err) {
      console.error("Failed to mark notification read:", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setStats((prev) => ({ ...prev, unread: 0 }));
    } catch (err) {
      console.error("Failed to mark all read:", err);
    }
  };

  const handleClearRead = async () => {
    try {
      await clearReadNotifications();
      setNotifications((prev) => prev.filter((n) => !n.is_read));
      setStats((prev) => ({
        ...prev,
        total: prev.unread,
      }));
    } catch (err) {
      console.error("Failed to clear read notifications:", err);
    }
  };

  const filteredNotifications = notifications.filter((n) => {
    if (activeFilter === "unread") return !n.is_read;
    return true;
  });

  const getDotClass = (severity) => {
    const s = (severity || "").toLowerCase();
    if (s === "critical" || s === "warning") return "notification-dot orange";
    return "notification-dot blue";
  };

  const currentPage = PAGE_CONFIG[active] || {
    title: navItems?.find((x) => x[2] === active)?.[1] || "SLMS",
    subtitle: "",
  };

  return (
    <header className="header">
      {/* Left Area: Collapse Toggle & Page Heading */}
      <div className="header-left">
        <button
          type="button"
          className="header-menu-btn"
          onClick={() => setSidebarOpen((prev) => !prev)}
          title={sidebarOpen ? "Collapse Sidebar" : "Expand Sidebar"}
          aria-label={sidebarOpen ? "Collapse Sidebar" : "Expand Sidebar"}
        >
          <Icon type="menu" size={20} />
        </button>

        <div className="header-title-block">
          <h1 className="header-page-title">{currentPage.title}</h1>
          {currentPage.subtitle && (
            <p className="header-page-subtitle">{currentPage.subtitle}</p>
          )}
        </div>
      </div>

      {/* Right Area: Notification Bell & User Profile */}
      <div className="header-right">
        {/* Notification Bell */}
        <div className="header-popup-wrapper" ref={bellWrapperRef}>
          <button
            type="button"
            className="header-bell-btn"
            onClick={() => {
              const nextState = !bellOpen;
              setBellOpen(nextState);
              if (setFilterOpen) setFilterOpen(false);
              setProfileOpen(false);
              if (nextState) {
                fetchNotificationData();
              }
            }}
            title="Notifications & Alerts"
            aria-label="Notifications & Alerts"
            aria-expanded={bellOpen}
          >
            <Icon type="bell" size={20} />
            {stats.unread > 0 && (
              <span className="header-bell-badge">
                {stats.unread > 99 ? "99+" : stats.unread}
              </span>
            )}
          </button>

          {bellOpen && (
            <div className="header-dropdown header-notifications-menu" role="dialog" aria-label="Notifications">
              {/* Dropdown Header */}
              <div className="header-notifications-header">
                <div>
                  <b>Notifications &amp; Alerts</b>
                  <small>
                    {stats.unread > 0
                      ? `${stats.unread} unread alert${stats.unread === 1 ? "" : "s"}`
                      : "All alerts caught up"}
                  </small>
                </div>

                <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                  {stats.unread > 0 && (
                    <button
                      type="button"
                      onClick={handleMarkAllRead}
                      style={{
                        background: "rgba(37, 99, 235, 0.1)",
                        border: "1px solid rgba(37, 99, 235, 0.25)",
                        color: "#2563eb",
                        borderRadius: "6px",
                        padding: "3px 8px",
                        fontSize: "11px",
                        fontWeight: "600",
                        cursor: "pointer",
                      }}
                    >
                      Read All
                    </button>
                  )}
                  {notifications.some((n) => n.is_read) && (
                    <button
                      type="button"
                      onClick={handleClearRead}
                      style={{
                        background: "#f1f5f9",
                        border: "1px solid #e2e8f0",
                        color: "#64748b",
                        borderRadius: "6px",
                        padding: "3px 8px",
                        fontSize: "11px",
                        cursor: "pointer",
                      }}
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              {/* Filter Tabs */}
              <div className="header-notifications-tabs">
                <button
                  type="button"
                  className="header-notifications-tab-btn"
                  onClick={() => setActiveFilter("all")}
                  style={{
                    color: activeFilter === "all" ? "#2563eb" : "#64748b",
                    fontWeight: activeFilter === "all" ? "600" : "400",
                    borderBottom: activeFilter === "all" ? "2px solid #2563eb" : "2px solid transparent",
                  }}
                >
                  All ({notifications.length})
                </button>
                <button
                  type="button"
                  className="header-notifications-tab-btn"
                  onClick={() => setActiveFilter("unread")}
                  style={{
                    color: activeFilter === "unread" ? "#2563eb" : "#64748b",
                    fontWeight: activeFilter === "unread" ? "600" : "400",
                    borderBottom: activeFilter === "unread" ? "2px solid #2563eb" : "2px solid transparent",
                  }}
                >
                  Unread ({stats.unread})
                </button>
              </div>

              {/* Notification List */}
              <div className="header-notifications-list">
                {loading && notifications.length === 0 ? (
                  <div style={{ padding: "24px 16px", textAlign: "center", color: "#64748b", fontSize: "13px" }}>
                    Loading alerts...
                  </div>
                ) : error && notifications.length === 0 ? (
                  <div style={{ padding: "20px 16px", textAlign: "center", color: "#dc2626", fontSize: "13px" }}>
                    <span>⚠ {error}</span>
                    <button
                      type="button"
                      onClick={fetchNotificationData}
                      style={{
                        display: "block",
                        margin: "8px auto 0",
                        background: "transparent",
                        border: "1px solid rgba(220, 38, 38, 0.3)",
                        color: "#dc2626",
                        borderRadius: "4px",
                        padding: "2px 8px",
                        fontSize: "11px",
                        cursor: "pointer",
                      }}
                    >
                      Retry
                    </button>
                  </div>
                ) : filteredNotifications.length > 0 ? (
                  filteredNotifications.map((notif) => {
                    const compName = notif.computer_hostname || `PC-${notif.computer_id}`;
                    return (
                      <div
                        key={notif.id}
                        className="header-notification-item"
                        style={{
                          opacity: notif.is_read ? 0.7 : 1,
                          backgroundColor: notif.is_read ? "transparent" : "rgba(37, 99, 235, 0.03)",
                        }}
                      >
                        <span className={getDotClass(notif.severity)} />

                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <b style={{ fontSize: "12.5px", color: notif.is_read ? "#475569" : "#172033" }}>
                              {compName} • {notif.category?.toUpperCase()}
                            </b>
                            <small style={{ color: "#94a3b8", fontSize: "11px" }}>
                              {formatRelativeTime(notif.created_at)}
                            </small>
                          </div>

                          <p
                            style={{
                              margin: "3px 0 0",
                              fontSize: "12px",
                              color: "#64748b",
                              lineHeight: "1.4",
                              wordBreak: "break-word",
                            }}
                          >
                            {notif.message}
                          </p>
                        </div>

                        {!notif.is_read && (
                          <button
                            type="button"
                            onClick={(e) => handleMarkRead(notif.id, e)}
                            title="Mark as read"
                            style={{
                              background: "transparent",
                              border: "none",
                              color: "#2563eb",
                              padding: "2px 4px",
                              cursor: "pointer",
                              fontSize: "13px",
                              fontWeight: "bold",
                            }}
                          >
                            ✓
                          </button>
                        )}
                      </div>
                    );
                  })
                ) : (
                  <div style={{ padding: "30px 16px", textAlign: "center", color: "#64748b", fontSize: "13px" }}>
                    {activeFilter === "unread" ? "No unread notifications" : "No notifications found"}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Profile in Header */}
        <div className="header-popup-wrapper" ref={profileWrapperRef}>
          <button
            type="button"
            className="header-user-btn"
            onClick={() => {
              setProfileOpen((p) => !p);
              setBellOpen(false);
              if (setFilterOpen) setFilterOpen(false);
            }}
            aria-expanded={profileOpen}
            aria-haspopup="true"
          >
            <div className="header-user-avatar" aria-hidden="true">
              {userInfo.initial}
            </div>

            <div className="header-user-text">
              <span className="header-user-name">{userInfo.name}</span>
              <span className="header-user-role">{userInfo.role}</span>
            </div>
          </button>

          {profileOpen && (
            <div className="header-dropdown header-profile-menu" role="menu">
              <div className="header-profile-menu__header">
                <div className="header-profile-menu__avatar">
                  {userInfo.initial}
                </div>
                <div>
                  <div className="header-user-name">{userInfo.name}</div>
                  <div className="header-user-role">{userInfo.role}</div>
                </div>
              </div>

              <button
                type="button"
                className="header-profile-menu__item"
                role="menuitem"
                onClick={() => {
                  navigate("settings");
                  setProfileOpen(false);
                }}
              >
                <Icon type="settings" size={16} />
                <span>Settings</span>
              </button>

              <button
                type="button"
                className="header-profile-menu__item logout"
                role="menuitem"
                onClick={() => {
                  setProfileOpen(false);
                  logout();
                }}
              >
                <Icon type="logout" size={16} />
                <span>Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;