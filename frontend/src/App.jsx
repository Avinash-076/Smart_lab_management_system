import { useState, useEffect } from "react";
import "./App.css";
import {
  login,
  logout,
  isAuthenticated,
  subscribeAuthChange,
  refreshToken,
  getAccessToken,
  getRefreshToken,
  isTokenExpired,
} from "./services/api";
import LoginPage from "./pages/LoginPage";

import Sidebar from "./components/Sidebar";
import Header from "./components/Header";

import Dashboard from "./pages/Dashboard";
import ComputerList from "./pages/ComputerList";
import ComputerDetails from "./pages/ComputerDetails";
import SoftwareInventory from "./pages/SoftwareInventory";
import IssueManagement from "./pages/IssueManagement";
import MaintenanceRecords from "./pages/MaintenanceRecords";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";
import UserRoleManagement from "./pages/UserRoleManagement";
import AuditLogs from "./pages/AuditLogs";

const navItems = [
  ["home", "Dashboard", "dashboard"],
  ["computer", "Computer List", "computers"],
  ["details", "Computer Details", "details"],
  ["software", "Software Inventory", "software"],
  ["issue", "Issue Management", "issues"],
  ["maintenance", "Maintenance Records", "maintenance"],
  ["reports", "Reports", "reports"],
  ["audit", "Audit Logs", "audit"],
  ["settings", "Settings", "settings"],
  ["users", "User & Role Management", "users"],
];

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(() => isAuthenticated());

  // Current active page
  const [active, setActive] = useState("dashboard");

  // Selected computer for Computer Details page
  const [selectedComputer, setSelectedComputer] =
    useState(null);

  const [sidebarOpen, setSidebarOpen] = useState(true);

  const [search, setSearch] = useState("");

  const [bellOpen, setBellOpen] = useState(false);

  const [profileOpen, setProfileOpen] = useState(false);

  const [filterOpen, setFilterOpen] = useState(false);

  /* =====================================================
     AUTH LIFECYCLE & SESSION PRESERVATION
  ===================================================== */

  useEffect(() => {
    // If access token is expired on mount but refresh token exists, refresh eagerly
    const aToken = getAccessToken();
    const rToken = getRefreshToken();
    if (aToken && isTokenExpired(aToken) && rToken && !isTokenExpired(rToken)) {
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
  };

  /* =====================================================
     NAVIGATION
  ===================================================== */

  const navigate = (id) => {
    setActive(id);

    setBellOpen(false);

    setProfileOpen(false);

    setFilterOpen(false);
  };

  /* =====================================================
     OPEN COMPUTER DETAILS
  ===================================================== */

  const openComputerDetails = (computer) => {
    // Store the computer that was clicked
    setSelectedComputer(computer);

    // Navigate to Computer Details page
    navigate("details");
  };

  /* =====================================================
     RENDER ACTIVE PAGE
  ===================================================== */

  const renderPage = () => {
    switch (active) {
      case "dashboard":
        return <Dashboard />;

      case "computers":
        return (
          <ComputerList
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

      case "software":
        return <SoftwareInventory />;

      case "issues":
        return <IssueManagement />;

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
      <Sidebar
        active={active}
        navigate={navigate}
        logout={handleLogout}
      />

      <main className="main">

        <Header
          active={active}
          navItems={navItems}
          sidebarOpen={sidebarOpen}
          setSidebarOpen={setSidebarOpen}
          search={search}
          setSearch={setSearch}
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