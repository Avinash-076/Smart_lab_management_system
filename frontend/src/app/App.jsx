import { useState, useEffect } from "react";
import "../styles/globals.css";
import "../components/layout/AppLayout.css";
import {
  login,
  logout,
  isAuthenticated,
  subscribeAuthChange,
  refreshToken,
  getAccessToken,
  getRefreshToken,
  isTokenExpired,
} from "../services/authService";

import LoginPage from "../features/auth/pages/LoginPage";
import Sidebar from "../components/layout/Sidebar";
import Header from "../components/layout/Header";

import Dashboard from "../features/dashboard/Dashboard";
import ComputersPage from "../features/computers/pages/ComputersPage";
import ComputerDetails from "../features/computers/pages/ComputerDetails";
import GlobalRemoteControlPage from "../features/global-remote-control/pages/GlobalRemoteControlPage";
import SoftwareInventory from "../features/software/pages/SoftwareInventory";
import IssueManagement from "../features/issues/pages/IssueManagement";
import MaintenanceRecords from "../features/maintenance/pages/MaintenanceRecords";
import Reports from "../features/reports/pages/Reports";
import Settings from "../features/settings/pages/Settings";
import UserRoleManagement from "../features/users/pages/UserRoleManagement";
import AuditLogs from "../features/audit/pages/AuditLogs";

const navItems = [
  ["home", "Dashboard", "dashboard"],
  ["computer", "Computers", "computers"],
  ["remote", "Global Remote Control", "remote-control"],
  ["software", "Software Inventory", "software"],
  ["issue", "Issue Management", "issues"],
  ["maintenance", "Maintenance Records", "maintenance"],
  ["reports", "Reports", "reports"],
  ["audit", "Audit Logs", "audit"],
  ["settings", "Settings", "settings"],
  ["users", "User & Role Management", "users"],
];

function parsePath(pathname) {
  const clean =
    pathname && pathname !== "/" && pathname.endsWith("/")
      ? pathname.slice(0, -1)
      : pathname || "/";

  // Match /computers/:id (e.g. /computers/1, /computers/2)
  const matchDetails = clean.match(/^\/computers\/([^/]+)$/);
  if (matchDetails) {
    const rawId = matchDetails[1];
    const compId = !isNaN(Number(rawId)) ? Number(rawId) : rawId;
    return {
      active: "details",
      computer: { id: compId },
    };
  }

  if (clean === "/computers") {
    return { active: "computers", computer: null };
  }

  const validPages = [
    "dashboard",
    "remote-control",
    "software",
    "issues",
    "maintenance",
    "reports",
    "audit",
    "settings",
    "users",
  ];

  const section = clean.replace(/^\//, "");
  if (validPages.includes(section)) {
    return { active: section, computer: null };
  }

  return { active: "dashboard", computer: null };
}

function getPathFor(pageId, comp) {
  if (pageId === "details") {
    const cid =
      comp?.id !== undefined
        ? comp.id
        : typeof comp === "number" || typeof comp === "string"
        ? comp
        : null;
    return cid ? `/computers/${cid}` : "/computers";
  }
  if (pageId === "dashboard") {
    return "/";
  }
  return `/${pageId}`;
}

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => isAuthenticated());

  // Parse initial route from URL
  const initialRoute =
    typeof window !== "undefined"
      ? parsePath(window.location.pathname)
      : { active: "dashboard", computer: null };

  // Current active page
  const [active, setActive] = useState(initialRoute.active);

  // Selected computer for Computer Details page
  const [selectedComputer, setSelectedComputer] = useState(
    initialRoute.computer
  );

  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [bellOpen, setBellOpen] = useState(false);

  const [profileOpen, setProfileOpen] = useState(false);

  const [filterOpen, setFilterOpen] = useState(false);
  const [dashboardSearch, setDashboardSearch] = useState("");

  /* =====================================================
     URL SYNCHRONIZATION & BROWSER HISTORY
  ===================================================== */

  useEffect(() => {
    function handlePopState() {
      const route = parsePath(window.location.pathname);
      setActive(route.active);
      setSelectedComputer(route.computer);
    }

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, []);

  /* =====================================================
     AUTH LIFECYCLE & SESSION PRESERVATION
  ===================================================== */

  useEffect(() => {
    // If access token is expired on mount but refresh token exists, refresh eagerly
    const aToken = getAccessToken();
    const rToken = getRefreshToken();
    if ((!aToken || isTokenExpired(aToken)) && rToken && !isTokenExpired(rToken)) {
      refreshToken().catch(() => {
        setIsLoggedIn(false);
      });
    }

    // Subscribe to auth state changes (e.g. 401 token invalidation)
    const unsubscribe = subscribeAuthChange((authenticated) => {
      setIsLoggedIn(authenticated);
      if (!authenticated) {
        setSelectedComputer(null);
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  /* =====================================================
     LOGIN
  ===================================================== */

  const handleLogin = async (userData) => {
    const data = await login(userData.username, userData.password);
    setIsLoggedIn(true);
    return data;
  };

  /* =====================================================
     LOGOUT
  ===================================================== */

  const handleLogout = () => {
    logout();
    setIsLoggedIn(false);
    setSelectedComputer(null);
    setProfileOpen(false);
    setBellOpen(false);
    setFilterOpen(false);
    setActive("dashboard");
    if (typeof window !== "undefined" && window.location.pathname !== "/") {
      window.history.pushState(null, "", "/");
    }
  };

  /* =====================================================
     NAVIGATION
  ===================================================== */

  const navigate = (id, comp = null) => {
    setActive(id);
    setSelectedComputer(comp);
    setBellOpen(false);
    setProfileOpen(false);
    setFilterOpen(false);

    if (typeof window !== "undefined") {
      const newPath = getPathFor(id, comp);
      if (window.location.pathname !== newPath) {
        window.history.pushState(null, "", newPath);
      }
    }
  };

  /* =====================================================
     OPEN COMPUTER DETAILS
  ===================================================== */

  const openComputerDetails = (computer) => {
    navigate("details", computer);
  };

  /* =====================================================
     RENDER ACTIVE PAGE
  ===================================================== */

  const renderPage = () => {
    switch (active) {
      case "dashboard":
        return (
          <Dashboard
            searchQuery={dashboardSearch}
            onSearchChange={setDashboardSearch}
            onViewComputer={openComputerDetails}
            onNavigate={navigate}
          />
        );

      case "computers":
        return (
          <ComputersPage
            onViewComputer={openComputerDetails}
          />
        );

      case "details":
        return (
          <ComputerDetails
            computer={selectedComputer}
            onBack={() => navigate("computers")}
          />
        );

      case "remote-control":
        return (
          <GlobalRemoteControlPage
            onViewComputer={openComputerDetails}
          />
        );

      case "software":
        return <SoftwareInventory onViewComputer={openComputerDetails} />;

      case "issues":
        return <IssueManagement onViewComputer={openComputerDetails} />;

      case "maintenance":
        return <MaintenanceRecords />;

      case "reports":
        return <Reports />;

      case "audit":
        return <AuditLogs />;

      case "settings":
        return <Settings />;

      case "users":
        return <UserRoleManagement />;

      default:
        return <Dashboard />;
    }
  };

  /* =====================================================
     LOGIN PAGE
  ===================================================== */

  if (!isLoggedIn) {
    return (
      <LoginPage
        onLogin={handleLogin}
      />
    );
  }

  /* =====================================================
     MAIN APPLICATION
  ===================================================== */

  return (
    <div
      className={`app ${
        sidebarOpen
          ? ""
          : "sidebar-collapsed"
      }`}
    >
      {/* Mobile drawer backdrop */}
      <div
        className="sidebar-backdrop"
        onClick={() => setSidebarOpen(false)}
        aria-hidden="true"
      />

      <Sidebar
        active={active}
        navigate={navigate}
        logout={handleLogout}
        sidebarOpen={sidebarOpen}
      />

      <main className="main">

        <Header
          active={active}
          navItems={navItems}
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          bellOpen={bellOpen}
          setBellOpen={setBellOpen}
          profileOpen={profileOpen}
          setProfileOpen={setProfileOpen}
          filterOpen={filterOpen}
          setFilterOpen={setFilterOpen}
          navigate={navigate}
          logout={handleLogout}
        />

        {renderPage()}

      </main>
    </div>
  );
}

export default App;
