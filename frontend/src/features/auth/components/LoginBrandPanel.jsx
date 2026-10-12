import {
  MonitorCheckIcon,
  MonitorIcon,
  BarChartIcon,
  ShieldIcon,
} from "../../../components/ui/Icons";
import "./LoginBrandPanel.css";

function LoginBrandPanel() {
  return (
    <aside className="login-brand">
      {/* Decorative ambient gradients */}
      <div className="login-brand__glow-top" aria-hidden="true" />
      <div className="login-brand__glow-bottom" aria-hidden="true" />

      {/* Unified Left-Aligned Content Container */}
      <div className="login-brand__container">
        {/* Brand Header */}
        <div className="login-brand__header">
          <div className="login-brand__logo-badge">
            <MonitorCheckIcon size={25} />
          </div>
          <div className="login-brand__logo-text">
            <span className="login-brand__title">SLMS</span>
            <span className="login-brand__subtitle">Smart Lab Management System</span>
          </div>
        </div>

        {/* Hero Headline */}
        <div className="login-brand__hero">
          <h1 className="login-brand__headline">
            Smart Lab<br />
            Management<br />
            <span className="login-brand__accent">Made Simple</span>
          </h1>
          <p className="login-brand__description">
            Monitor, manage and secure all your lab computers in one intelligent platform.
          </p>
        </div>

        {/* Feature Rows */}
        <div className="login-brand__features">
          <div className="login-brand__feature-item">
            <div className="login-brand__feature-icon">
              <MonitorIcon size={22} />
            </div>
            <div className="login-brand__feature-content">
              <h2 className="login-brand__feature-title">Real-time Monitoring</h2>
              <p className="login-brand__feature-desc">
                Track system status and performance across all lab computers.
              </p>
            </div>
          </div>

          <div className="login-brand__feature-item">
            <div className="login-brand__feature-icon">
              <BarChartIcon size={22} />
            </div>
            <div className="login-brand__feature-content">
              <h2 className="login-brand__feature-title">Smart Insights</h2>
              <p className="login-brand__feature-desc">
                Get analytics and recommendations to optimize lab usage.
              </p>
            </div>
          </div>

          <div className="login-brand__feature-item">
            <div className="login-brand__feature-icon">
              <ShieldIcon size={22} />
            </div>
            <div className="login-brand__feature-content">
              <h2 className="login-brand__feature-title">Secure &amp; Role Based</h2>
              <p className="login-brand__feature-desc">
                Protect your lab with JWT authentication and role-based access control.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Subtle Lab Workstation Decorative Vector */}
      <div className="login-brand__graphic" aria-hidden="true">
        <svg
          className="login-brand__graphic-svg"
          viewBox="0 0 320 180"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Subtle workstation desk line */}
          <path
            d="M0 160L320 160"
            stroke="url(#desk-grad)"
            strokeWidth="2"
          />
          {/* Primary Monitor Outline */}
          <rect
            x="145"
            y="55"
            width="135"
            height="85"
            rx="5"
            stroke="#0EA5E9"
            strokeWidth="1.5"
            fill="rgba(10, 37, 88, 0.75)"
          />
          <path d="M195 140H230" stroke="#0EA5E9" strokeWidth="2" strokeLinecap="round" />
          <path d="M212 140V156" stroke="#0EA5E9" strokeWidth="2" strokeLinecap="round" />
          {/* Chart waveform on primary monitor */}
          <path
            d="M158 112L180 92L200 102L230 74L262 90"
            stroke="#0EA5E9"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Secondary Monitor Outline */}
          <rect
            x="52"
            y="75"
            width="82"
            height="65"
            rx="4"
            stroke="rgba(14, 165, 233, 0.65)"
            strokeWidth="1.2"
            fill="rgba(10, 37, 88, 0.5)"
          />
          <path d="M82 140H104" stroke="rgba(14, 165, 233, 0.65)" strokeWidth="1.5" strokeLinecap="round" />
          <path d="M93 140V156" stroke="rgba(14, 165, 233, 0.65)" strokeWidth="1.5" strokeLinecap="round" />
          <circle cx="93" cy="107" r="14" stroke="#0EA5E9" strokeWidth="1.4" strokeDasharray="56 28" />

          <defs>
            <linearGradient id="desk-grad" x1="0" y1="160" x2="320" y2="160" gradientUnits="userSpaceOnUse">
              <stop stopColor="rgba(14, 165, 233, 0)" />
              <stop offset="0.5" stopColor="rgba(14, 165, 233, 0.45)" />
              <stop offset="1" stopColor="rgba(14, 165, 233, 0.75)" />
            </linearGradient>
          </defs>
        </svg>
      </div>
    </aside>
  );
}

export default LoginBrandPanel;
