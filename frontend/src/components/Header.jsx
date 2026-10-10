import { useState, useEffect, useCallback } from "react";
import Icon from "./Icon";
import {
  getNotifications,
  getNotificationStats,
  markNotificationRead,
  markAllNotificationsRead,
  clearReadNotifications,
} from "../services/api";

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
    if (s === "critical") return "notification-dot orange";
    if (s === "warning") return "notification-dot orange";
    return "notification-dot blue";
  };

  return (
    <header className="header">
      <div className="header-title">
        {/* MENU */}
        <button
          className="menu"
          onClick={() => setSidebarOpen((prev) => !prev)}
          title={sidebarOpen ? "Collapse Sidebar" : "Expand Sidebar"}
        >
          <Icon type="menu" size={25} />
        </button>

        {/* PAGE TITLE */}
        <h1>
          {active === "computers"
            ? "Computer List"
            : navItems.find((x) => x[2] === active)?.[1] || "SLMS"}
        </h1>
      </div>

      <div className="header-right">
        {/* SEARCH */}
        <div className="header-search">
          <input
            placeholder="Search computers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Icon type="search" size={19} />
        </div>

        {/* NOTIFICATION */}
        <div className="header-popup-wrapper">
          <button
            className="bell"
            onClick={() => {
              const nextState = !bellOpen;
              setBellOpen(nextState);
              setFilterOpen(false);
              setProfileOpen(false);
              if (nextState) {
                fetchNotificationData();
              }
            }}
            title="Notifications & Alerts"
          >
            <Icon type="bell" size={24} />
            {stats.unread > 0 && <span>{stats.unread > 99 ? "99+" : stats.unread}</span>}
          </button>

          {bellOpen && (
            <div
              className="slms-dropdown notification-dropdown"
              style={{
                minWidth: "360px",
                maxWidth: "420px",
                maxHeight: "480px",
                overflowY: "auto",
              }}
            >
              {/* DROPDOWN HEADING */}
              <div className="dropdown-heading" style={{ padding: "14px 16px" }}>
                <div>
                  <b>Notifications & Alerts</b>
                  <small style={{ display: "block", color: "#8b949e", fontSize: "11px" }}>
                    {stats.unread > 0 ? `${stats.unread} unread alert${stats.unread === 1 ? "" : "s"}` : "All alerts caught up"}
                  </small>
                </div>

                <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                  {stats.unread > 0 && (
                    <button
                      onClick={handleMarkAllRead}
                      style={{
                        background: "rgba(59, 130, 246, 0.15)",
                        border: "1px solid rgba(59, 130, 246, 0.3)",
                        color: "#60a5fa",
                        borderRadius: "4px",
                        padding: "3px 7px",
                        fontSize: "11px",
                        fontWeight: "600",
                        cursor: "pointer",
                      }}
                      title="Mark all as read"
                    >
                      Read All
                    </button>
                  )}
                  {notifications.some((n) => n.is_read) && (
                    <button
                      onClick={handleClearRead}
                      style={{
                        background: "rgba(255, 255, 255, 0.05)",
                        border: "1px solid rgba(255, 255, 255, 0.12)",
                        color: "#8b949e",
                        borderRadius: "4px",
                        padding: "3px 7px",
                        fontSize: "11px",
                        cursor: "pointer",
                      }}
                      title="Clear read notifications"
                    >
                      Clear
                    </button>
                  )}
                </div>
              </div>

              {/* FILTER TABS */}
              <div
                style={{
                  display: "flex",
                  borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
                  padding: "0 16px 8px",
                  gap: "12px",
                  fontSize: "12px",
                }}
              >
                <button
                  onClick={() => setActiveFilter("all")}
                  style={{
                    background: "none",
                    border: "none",
                    padding: "4px 0",
                    color: activeFilter === "all" ? "#3b82f6" : "#8b949e",
                    fontWeight: activeFilter === "all" ? "600" : "400",
                    borderBottom: activeFilter === "all" ? "2px solid #3b82f6" : "2px solid transparent",
                    cursor: "pointer",
                  }}
                >
                  All ({notifications.length})
                </button>
                <button
                  onClick={() => setActiveFilter("unread")}
                  style={{
                    background: "none",
                    border: "none",
                    padding: "4px 0",
                    color: activeFilter === "unread" ? "#3b82f6" : "#8b949e",
                    fontWeight: activeFilter === "unread" ? "600" : "400",
                    borderBottom: activeFilter === "unread" ? "2px solid #3b82f6" : "2px solid transparent",
                    cursor: "pointer",
                  }}
                >
                  Unread ({stats.unread})
                </button>
              </div>

              {/* BODY LIST */}
              {loading && notifications.length === 0 ? (
                <div style={{ padding: "24px 16px", textAlign: "center", color: "#8b949e", fontSize: "13px" }}>
                  Loading alerts...
                </div>
              ) : error && notifications.length === 0 ? (
                <div style={{ padding: "20px 16px", textAlign: "center", color: "#ef4444", fontSize: "13px" }}>
                  <span>⚠ {error}</span>
                  <button
                    onClick={fetchNotificationData}
                    style={{
                      display: "block",
                      margin: "8px auto 0",
                      background: "transparent",
                      border: "1px solid rgba(239, 68, 68, 0.3)",
                      color: "#ef4444",
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
                      className="notification-item"
                      style={{
                        padding: "10px 16px",
                        borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                        opacity: notif.is_read ? 0.75 : 1,
                        background: notif.is_read ? "transparent" : "rgba(59, 130, 246, 0.04)",
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "10px",
                        cursor: "default",
                      }}
                    >
                      <span className={getDotClass(notif.severity)} style={{ marginTop: "4px" }} />

                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                          <b style={{ fontSize: "13px", color: notif.is_read ? "#c9d1d9" : "#f0f6fc" }}>
                            {compName} • {notif.category?.toUpperCase()}
                          </b>
                          <small style={{ color: "#718096", fontSize: "11px" }}>
                            {formatRelativeTime(notif.created_at)}
                          </small>
                        </div>

                        <p
                          style={{
                            margin: "4px 0 0",
                            fontSize: "12px",
                            color: "#8b949e",
                            lineHeight: "1.4",
                            wordBreak: "break-word",
                          }}
                        >
                          {notif.message}
                        </p>
                      </div>

                      {!notif.is_read && (
                        <button
                          onClick={(e) => handleMarkRead(notif.id, e)}
                          title="Mark as read"
                          style={{
                            background: "transparent",
                            border: "none",
                            color: "#3b82f6",
                            padding: "2px 4px",
                            cursor: "pointer",
                            fontSize: "12px",
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
                <div style={{ padding: "30px 16px", textAlign: "center", color: "#8b949e", fontSize: "13px" }}>
                  {activeFilter === "unread" ? "No unread notifications" : "No notifications found"}
                </div>
              )}
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
                  setProfileOpen(false);
                }}
              >
                <Icon type="settings" size={18} />
                Settings
              </button>

              <button
                className="dropdown-action"
                onClick={() => {
                  logout();
                  setProfileOpen(false);
                }}
              >
                <Icon type="logout" size={18} />
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

export default Header;