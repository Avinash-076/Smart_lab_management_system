import { describe, it, expect, vi } from "vitest";
import { renderToString } from "react-dom/server";
import Sidebar from "../components/layout/Sidebar";
import Header from "../components/layout/Header";

describe("Shared Authenticated Layout Components", () => {
  it("renders Sidebar with SLMS brand, all nav items, and user profile at the bottom", () => {
    const html = renderToString(
      <Sidebar
        active="dashboard"
        navigate={vi.fn()}
        logout={vi.fn()}
        sidebarOpen={true}
      />
    );

    // Branding
    expect(html).toContain("SLMS");
    expect(html).toContain("Smart Lab Management System");
    // Duplicate circular sidebar-edge toggle button removed
    expect(html).not.toContain("sidebar-toggle-btn");

    // Navigation items
    expect(html).toContain("Dashboard");
    expect(html).toContain("Computers");
    expect(html).toContain("Global Remote Control");
    expect(html).not.toContain("Computer Details");
    expect(html).toContain("Software Inventory");
    expect(html).toContain("Issue Management");
    expect(html).toContain("Maintenance Records");
    expect(html).toContain("Reports");
    expect(html).toContain("Audit Logs");
    expect(html).toContain("Settings");
    expect(html).not.toContain("User &amp; Role Management");

    // Active state
    expect(html).toContain("active");

    // Promotional card removed confirmation
    expect(html).not.toContain("system-box");
    expect(html).not.toContain("All systems operational");

    // Bottom user profile section
    expect(html).toContain("sidebar-user");
    expect(html).toContain("sidebar-user__avatar");
    expect(html).toContain("sidebar-user__name");
    expect(html).toContain("sidebar-user__role");
  });

  it("renders Sidebar in collapsed mode when sidebarOpen is false", () => {
    const html = renderToString(
      <Sidebar
        active="computers"
        navigate={vi.fn()}
        logout={vi.fn()}
        sidebarOpen={false}
      />
    );

    expect(html).toContain("sidebar collapsed");
  });

  it("renders Header with menu button, dynamic title and subtitle, notification bell, and user profile (no search bar)", () => {
    const navItems = [
      ["grid", "Dashboard", "dashboard"],
      ["computer", "Computers", "computers"],
    ];

    const html = renderToString(
      <Header
        active="dashboard"
        navItems={navItems}
        sidebarOpen={true}
        setSidebarOpen={vi.fn()}
        bellOpen={false}
        setBellOpen={vi.fn()}
        profileOpen={false}
        setProfileOpen={vi.fn()}
        setFilterOpen={vi.fn()}
        navigate={vi.fn()}
        logout={vi.fn()}
      />
    );

    // Menu button (the single toggle control)
    expect(html).toContain("header-menu-btn");

    // Dynamic Title and Subtitle in Header
    expect(html).toContain("header-title-block");
    expect(html).toContain("header-page-title");
    expect(html).toContain("Dashboard");
    expect(html).toContain("header-page-subtitle");
    expect(html).toContain("Monitor and manage all laboratory computers and active alerts.");

    // Search bar completely removed
    expect(html).not.toContain("header-search");
    expect(html).not.toContain("Search computer, software, or user...");

    // Notification bell
    expect(html).toContain("header-bell-btn");

    // Header user profile
    expect(html).toContain("header-user-btn");
    expect(html).toContain("header-user-avatar");
    expect(html).toContain("header-user-name");
    expect(html).toContain("header-user-role");
  });

  it("renders Header with dynamic title and subtitle for another route", () => {
    const html = renderToString(
      <Header
        active="computers"
        sidebarOpen={true}
        setSidebarOpen={vi.fn()}
        bellOpen={false}
        setBellOpen={vi.fn()}
        profileOpen={false}
        setProfileOpen={vi.fn()}
        navigate={vi.fn()}
        logout={vi.fn()}
      />
    );

    expect(html).toContain("Computers");
    expect(html).toContain("View and manage all lab computers.");
  });

  it("renders Header with notifications popup when bellOpen is true", () => {
    const html = renderToString(
      <Header
        active="dashboard"
        sidebarOpen={true}
        setSidebarOpen={vi.fn()}
        bellOpen={true}
        setBellOpen={vi.fn()}
        profileOpen={false}
        setProfileOpen={vi.fn()}
        navigate={vi.fn()}
        logout={vi.fn()}
      />
    );

    expect(html).toContain("header-dropdown header-notifications-menu");
    expect(html).toContain("Notifications &amp; Alerts");
    expect(html).toContain("All alerts caught up");
  });
});
