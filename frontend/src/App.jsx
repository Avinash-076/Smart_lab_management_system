import { useState } from "react";
import "./App.css";
import { login } from "./services/api";
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

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

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
     LOGIN
  ===================================================== */

  const handleLogin = async (userData) => {
    try {
      const data = await login(userData.username, userData.password);

      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);

      console.log("Login successful");

      setIsLoggedIn(true);
    } catch (error) {
      console.error("Login failed:", error);
      alert(error.message);
    }
  };
  /* =====================================================
     LOGOUT
  ===================================================== */

  const handleLogout = () => {
    setIsLoggedIn(false);

    // Clear selected computer when logging out
    setSelectedComputer(null);
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
          setFilterOpen={setFilterOpen}
          navigate={navigate}
        />

        {renderPage()}

      </main>
    </div>
  );
}

export default App;