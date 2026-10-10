function SystemIllustration() {
  return (
    <div className="system-illustration">

      <div className="floating-circle chip">
        <span>▦</span>
      </div>

      <div className="floating-circle wifi">
        <span>⌁</span>
      </div>

      <div className="floating-circle shield-float">
        <span>♢</span>
      </div>

      <div className="monitor">

        <div className="monitor-screen">

          <div className="screen-panel chart-panel">
            <div className="chart-line"></div>
            <div className="chart-line second"></div>
          </div>

          <div className="screen-panel pie-panel">
            <div className="pie-chart"></div>
          </div>

          <div className="screen-row">
            <span></span>
            <span></span>
          </div>

          <div className="screen-row">
            <span></span>
            <span></span>
          </div>

        </div>

      </div>

      <div className="monitor-stand"></div>

      <div className="monitor-base"></div>

      <div className="cpu-case">

        <div className="cpu-slot"></div>

        <div className="cpu-slot"></div>

        <div className="cpu-light"></div>

      </div>

      <div className="node node-one"></div>
      <div className="node node-two"></div>
      <div className="node node-three"></div>

    </div>
  );
}

export default SystemIllustration;