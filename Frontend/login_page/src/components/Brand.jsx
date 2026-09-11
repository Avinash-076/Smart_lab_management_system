import { MonitorIcon } from "./Icons";

function Brand() {
  return (
    <div className="brand">

      <div className="brand-icon">
        <MonitorIcon size={43} />
      </div>

      <div className="brand-text">
        <h1>SLMS</h1>

        <p>
          Smart Lab Management System
        </p>
      </div>

    </div>
  );
}

export default Brand;