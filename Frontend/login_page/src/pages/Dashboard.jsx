function Dashboard({ onLogout }) {

  return (
    <div className="dashboard-page">

      <div className="dashboard-card">

        <div className="dashboard-logo">
          SLMS
        </div>

        <h1>
          Welcome to SLMS Dashboard
        </h1>

        <p>
          Login successful.
        </p>

        <button
          className="logout-button"
          onClick={onLogout}
        >
          Logout
        </button>

      </div>

    </div>
  );
}

export default Dashboard;