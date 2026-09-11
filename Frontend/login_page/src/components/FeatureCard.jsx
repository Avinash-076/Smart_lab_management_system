import {
  MonitorIcon,
  BrainIcon,
  ShieldIcon
} from "./Icons";


function FeatureCard() {
  return (
    <div className="feature-card">

      <div className="feature-item">

        <div className="feature-icon">
          <MonitorIcon size={23} />
        </div>

        <div>
          <h3>
            Monitor Systems
          </h3>

          <p>
            Real-time status and performance
          </p>
        </div>

      </div>


      <div className="feature-item">

        <div className="feature-icon blue">
          <BrainIcon size={25} />
        </div>

        <div>
          <h3>
            AI Assistance
          </h3>

          <p>
            Smart insights and recommendations
          </p>
        </div>

      </div>


      <div className="feature-item">

        <div className="feature-icon shield">
          <ShieldIcon size={24} />
        </div>

        <div>
          <h3>
            Secure &amp; Role Based
          </h3>

          <p>
            Role-based access with JWT authentication
          </p>
        </div>

      </div>

    </div>
  );
}

export default FeatureCard;