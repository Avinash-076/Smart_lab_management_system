import { describe, it, expect, vi } from "vitest";
import { renderToString } from "react-dom/server";
import LoginPage from "../features/auth/pages/LoginPage";
import LoginForm from "../features/auth/components/LoginForm";
import LoginBrandPanel from "../features/auth/components/LoginBrandPanel";
import LoginSecurityNotice from "../features/auth/components/LoginSecurityNotice";

describe("LoginPage & Components Rendering", () => {
  it("renders LoginPage with brand panel, login card, and footer", () => {
    const html = renderToString(<LoginPage onLogin={vi.fn()} />);

    // Brand Panel checks
    expect(html).toContain("SLMS");
    expect(html).toContain("Smart Lab Management System");
    expect(html).toContain("Smart Lab");
    expect(html).toContain("Management");
    expect(html).toContain("Made Simple");
    expect(html).toContain("Real-time Monitoring");
    expect(html).toContain("Smart Insights");
    expect(html).toContain("Secure &amp; Role Based");

    // Login Card checks
    expect(html).toContain("Login to");
    expect(html).toContain("Enter your credentials to access the system");
    expect(html).toContain("Username");
    expect(html).toContain("Password");
    expect(html).toContain("Login");

    // Security Notice checks
    expect(html).toContain("Secure Authentication");
    expect(html).toContain("Your account is protected");

    // Footer
    expect(html).toContain("2025 SLMS - Smart Lab Management System");
  });

  it("renders LoginBrandPanel with all 3 feature rows and description", () => {
    const html = renderToString(<LoginBrandPanel />);

    expect(html).toContain("Monitor, manage and secure all your lab computers in one intelligent platform.");
    expect(html).toContain("Track system status and performance across all lab computers.");
    expect(html).toContain("Get analytics and recommendations to optimize lab usage.");
    expect(html).toContain("Protect your lab with JWT authentication and role-based access control.");
  });

  it("renders LoginForm with accessible input fields and submit button", () => {
    const html = renderToString(<LoginForm onLogin={vi.fn()} />);

    expect(html).toContain('id="username"');
    expect(html).toContain('id="password"');
    expect(html).toContain('placeholder="Enter username"');
    expect(html).toContain('placeholder="Enter password"');
    expect(html).toContain('type="submit"');
    expect(html).toContain('aria-label="Show password"');
  });

  it("renders LoginSecurityNotice with title and description", () => {
    const html = renderToString(<LoginSecurityNotice />);

    expect(html).toContain("Secure Authentication");
    expect(html).toContain("Your account is protected");
    expect(html).toContain("You will be redirected after successful login based on your role.");
  });
});
