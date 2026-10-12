import { useState } from "react";
import {
  UserIcon,
  LockIcon,
  EyeIcon,
  EyeOffIcon,
  LoginIcon,
  UserLockIcon,
} from "../../../components/ui/Icons";
import LoginSecurityNotice from "./LoginSecurityNotice";
import "./LoginForm.css";

function LoginForm({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");

    if (!username.trim()) {
      setError("Please enter your username.");
      return;
    }

    if (!password.trim()) {
      setError("Please enter your password.");
      return;
    }

    try {
      setLoading(true);
      await onLogin({
        username: username.trim(),
        password,
      });
    } catch (err) {
      setError(err.message || "Invalid username or password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-card">
      {/* Top Security Icon Badge */}
      <div className="login-card__icon-badge">
        <UserLockIcon size={26} />
      </div>

      {/* Heading */}
      <h2 className="login-card__title">
        Login to <span className="login-card__title-brand">SLMS</span>
      </h2>
      <p className="login-card__subtitle">
        Enter your credentials to access the system
      </p>

      {/* Form */}
      <form className="login-card__form" onSubmit={handleSubmit} noValidate>
        {/* Username Field */}
        <div className="login-card__field">
          <label className="login-card__label" htmlFor="username">
            Username
          </label>
          <div className="login-card__input-wrapper">
            <span className="login-card__input-icon" aria-hidden="true">
              <UserIcon size={18} />
            </span>
            <input
              id="username"
              name="username"
              type="text"
              className="login-card__input"
              placeholder="Enter username"
              value={username}
              disabled={loading}
              autoComplete="username"
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
        </div>

        {/* Password Field */}
        <div className="login-card__field">
          <label className="login-card__label" htmlFor="password">
            Password
          </label>
          <div className="login-card__input-wrapper">
            <span className="login-card__input-icon" aria-hidden="true">
              <LockIcon size={18} />
            </span>
            <input
              id="password"
              name="password"
              type={showPassword ? "text" : "password"}
              className="login-card__input"
              placeholder="Enter password"
              value={password}
              disabled={loading}
              autoComplete="current-password"
              onChange={(e) => setPassword(e.target.value)}
              required
            />
            <button
              type="button"
              className="login-card__password-toggle"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              tabIndex={0}
            >
              {showPassword ? <EyeIcon size={18} /> : <EyeOffIcon size={18} />}
            </button>
          </div>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="login-card__error-banner" role="alert">
            <span className="login-card__error-dot" />
            <span className="login-card__error-text">{error}</span>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          className="login-card__submit-btn"
          disabled={loading}
        >
          {loading ? (
            <span className="login-card__spinner" aria-hidden="true" />
          ) : (
            <LoginIcon size={20} />
          )}
          <span>{loading ? "Signing in..." : "Login"}</span>
        </button>
      </form>

      {/* Security Notice Section */}
      <LoginSecurityNotice />
    </div>
  );
}

export default LoginForm;