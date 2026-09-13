import { useState } from "react";
import "./App.css";

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

  const [active, setActive] = useState("dashboard");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [search, setSearch] = useState("");
  const [bellOpen, setBellOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [filterOpen, setFilterOpen] = useState(false);

  const handleLogin = (userData) => {
    console.log("Logged in user:", userData);
    setIsLoggedIn(true);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
  };

  const navigate = (id) => {
    setActive(id);
    setBellOpen(false);
    setProfileOpen(false);
    setFilterOpen(false);
  };

  const renderPage = () => {
    switch (active) {
      case "dashboard":
        return <Dashboard />;

      case "computers":
        return <ComputerList />;

      case "details":
        return <ComputerDetails />;

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

  // Show Login Page first
  if (!isLoggedIn) {
    return <LoginPage onLogin={handleLogin} />;
  }

  // Show Dashboard after login
  return (
    <div className={`app ${sidebarOpen ? "" : "sidebar-collapsed"}`}>
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