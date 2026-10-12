import { ShieldIcon } from "../../../components/ui/Icons";
import "./LoginSecurityNotice.css";

function LoginSecurityNotice() {
  return (
    <div className="login-security">
      {/* Subtle Separator */}
      <div className="login-security__separator">
        <span className="login-security__separator-line" />
        <span className="login-security__separator-text">Secure Authentication</span>
        <span className="login-security__separator-line" />
      </div>

      {/* Notice Card */}
      <div className="login-security__notice">
        <div className="login-security__icon-badge">
          <ShieldIcon size={18} />
        </div>
        <div className="login-security__content">
          <span className="login-security__title">Your account is protected</span>
          <span className="login-security__desc">
            You will be redirected after successful login based on your role.
          </span>
        </div>
      </div>
    </div>
  );
}

export default LoginSecurityNotice;
