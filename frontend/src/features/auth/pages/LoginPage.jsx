import LoginBrandPanel from "../components/LoginBrandPanel";
import LoginForm from "../components/LoginForm";
import "./Login.css";

function LoginPage({ onLogin }) {
  return (
    <main className="login-page">
      {/* Left Branding Panel */}
      <LoginBrandPanel />

      {/* Right Authentication Area */}
      <section className="login-auth">
        {/* Ambient background decoration */}
        <div className="login-auth__bg-shape" aria-hidden="true" />

        {/* Centered Login Card Container */}
        <div className="login-auth__center">
          <LoginForm onLogin={onLogin} />
        </div>

        {/* Footer */}
        <footer className="login-auth__footer">
          &copy; 2025 SLMS - Smart Lab Management System. All rights reserved.
        </footer>
      </section>
    </main>
  );
}

export default LoginPage;
