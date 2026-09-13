import { useState } from "react";

import {
  UserIcon,
  LockIcon,
  EyeIcon,
  EyeOffIcon,
  ShieldIcon,
  LoginIcon,
  InfoIcon,
  ChevronDownIcon
} from "./Icons";


function LoginForm({ onLogin }) {

  const [username, setUsername] = useState("");

  const [password, setPassword] = useState("");

  const [role, setRole] = useState("");

  const [showPassword, setShowPassword] = useState(false);

  const [error, setError] = useState("");


  
  const handleSubmit = (event) => {

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


    onLogin({
      username: username.trim(),
      password
    });
  };

  return (
    <div className="login-container">

      {/* Login icon */}

      <div className="login-icon-wrapper">

        <div className="login-lock">
          <LockIcon size={37} />
        </div>

        <div className="login-user">
          <UserIcon size={24} />
        </div>

      </div>


      {/* Heading */}

      <h2>
        Login to <span>SLMS</span>
      </h2>

      <p className="login-subtitle">
        Enter your credentials to continue
      </p>


      <form onSubmit={handleSubmit}>

        {/* USERNAME */}

        <div className="form-group">

          <label htmlFor="username">
            Username
          </label>

          <div className="input-wrapper">

            <UserIcon size={21} />

            <input
              id="username"
              type="text"
              placeholder="Enter username"
              value={username}
              onChange={(event) =>
                setUsername(event.target.value)
              }
            />

          </div>

        </div>


        {/* PASSWORD */}

        <div className="form-group">

          <label htmlFor="password">
            Password
          </label>

          <div className="input-wrapper">

            <LockIcon size={21} />

            <input
              id="password"
              type={showPassword ? "text" : "password"}
              placeholder="Enter password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
            />

            <button
              type="button"
              className="password-toggle"
              onClick={() =>
                setShowPassword((previous) => !previous)
              }
              aria-label="Toggle password visibility"
            >

              {showPassword ? (
                <EyeIcon size={21} />
              ) : (
                <EyeOffIcon size={21} />
              )}

            </button>

          </div>

        </div>


        {/* ERROR */}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}


        {/* LOGIN BUTTON */}

        <button
          type="submit"
          className="login-button"
        >

          <LoginIcon size={23} />

          <span>
            Login
          </span>

        </button>

      </form>


      {/* SECURITY */}

      <div className="security-section">

        <div className="security-icon">
          <ShieldIcon size={25} />
        </div>

        <div>

          <h3>
            Secure Authentication
          </h3>

          <p>
            You will be redirected after token verification
          </p>

        </div>

      </div>


      {/* INFORMATION */}

      <div className="info-box">

        <div className="info-icon">
          <InfoIcon size={22} />
        </div>

        <p>
          After successful login, you will be redirected to your
          dashboard based on your role.
        </p>

      </div>

    </div>
  );
}

export default LoginForm;