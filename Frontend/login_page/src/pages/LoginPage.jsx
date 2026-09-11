import Brand from "../components/Brand";
import FeatureCard from "../components/FeatureCard";
import LoginForm from "../components/LoginForm";
import SystemIllustration from "../components/SystemIllustration";


function LoginPage({ onLogin }) {

  return (
    <main className="login-page">

      {/* LEFT SIDE */}

      <section className="left-panel">

        <Brand />


        <div className="welcome-section">

          <h2>
            Welcome <span>Back!</span>
          </h2>

          <p>
            Sign in to access your lab dashboard and
            <br />
            manage systems efficiently.
          </p>

        </div>


        <SystemIllustration />


        <FeatureCard />

      </section>


      {/* RIGHT SIDE */}

      <section className="right-panel">

        <div className="login-card">

          <LoginForm onLogin={onLogin} />

        </div>

      </section>


      {/* FOOTER */}

      <footer>
        © 2025 SLMS - Smart Lab Management System.
        All rights reserved.
      </footer>

    </main>
  );
}

export default LoginPage;