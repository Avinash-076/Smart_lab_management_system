import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

function ComputerDetails({
  computer,
  onBack,
}) {
  /* =====================================================
     NO COMPUTER SELECTED
  ===================================================== */

  if (!computer) {
    return (
      <div className="content">

        <div className="page-top">

          <div>
            <h2>
              Computer Details
            </h2>

            <p>
              Select a computer from
              the Computer List to view
              its complete information.
            </p>
          </div>

        </div>

        <div className="table-card">

          <div className="empty-state">

            <Icon
              type="details"
              size={40}
            />

            <h3>
              No computer selected
            </h3>

            <p>
              Open the Computer List
              and click the eye button
              beside a computer.
            </p>

            <button
              className="modal-button"
              onClick={onBack}
            >
              Go to Computer List
            </button>

          </div>

        </div>

      </div>
    );
  }

  /* =====================================================
     DISK CALCULATION
  ===================================================== */

  const usedDisk =
    Math.round(
      ((computer.total -
        computer.free) /
        computer.total) *
        100
    );

  /* =====================================================
     DEMO CPU / RAM VALUES
  ===================================================== */

  const ramUsage =
    computer.ram === "16 GB"
      ? 62
      : 71;

  const cpuUsage =
    computer.status ===
    "Online"
      ? 38
      : 0;

  /* =====================================================
     PAGE
  ===================================================== */

  return (
    <div className="content">

      {/* =================================================
          PAGE HEADER
      ================================================= */}

      <div className="page-top">

        <div>
          <h2>
            Computer Details
          </h2>

          <p>
            Detailed information for
            the selected laboratory
            computer.
          </p>
        </div>

        <button
          className="refresh"
          onClick={onBack}
        >
          ← Back to Computer List
        </button>

      </div>

      {/* =================================================
          SELECTED COMPUTER HEADER
      ================================================= */}

      <div className="details-computer-header">

        <div className="details-computer-title">

          <div className="details-computer-icon">

            <Icon
              type="windows"
              size={30}
            />

          </div>

          <div>

            <h2>
              {computer.name}
            </h2>

            <p>
              {computer.lab}
              {" • "}
              {computer.ip}
            </p>

          </div>

        </div>

        <span
          className={`status ${computer.status.toLowerCase()}`}
        >
          <i />

          {computer.status}
        </span>

      </div>

      {/* =================================================
          STAT CARDS
      ================================================= */}

      <div className="cards">

        <StatCard
          icon="computer"
          title="CPU Usage"
          number={`${cpuUsage}%`}
          footer="Current processor usage"
          type="blue"
        />

        <StatCard
          icon="computer"
          title="RAM Usage"
          number={`${ramUsage}%`}
          footer={`${computer.ram} installed`}
          type="green"
        />

        <StatCard
          icon="computer"
          title="Disk Usage"
          number={`${usedDisk}%`}
          footer={`${computer.free} GB free`}
          type="orange"
        />

        <StatCard
          icon="windows"
          title="Operating System"
          number={
            computer.os.includes(
              "Windows 11"
            )
              ? "Windows 11"
              : computer.os.includes(
                    "Windows 7"
                  )
                ? "Windows 7"
                : "Windows 10"
          }
          footer={computer.os}
          type="purple"
        />

      </div>

      {/* =================================================
          INFORMATION GRID
      ================================================= */}

      <div className="details-sections">

        {/* COMPUTER INFORMATION */}

        <div className="details-panel">

          <div className="details-panel-header">

            <h3>
              Computer Information
            </h3>

          </div>

          <div className="details-info-grid">

            <div>
              <span>
                Computer Name
              </span>

              <strong>
                {computer.name}
              </strong>
            </div>

            <div>
              <span>
                Computer ID
              </span>

              <strong>
                SLMS-
                {String(
                  computer.id
                ).padStart(
                  3,
                  "0"
                )}
              </strong>
            </div>

            <div>
              <span>
                Lab
              </span>

              <strong>
                {computer.lab}
              </strong>
            </div>

            <div>
              <span>
                IP Address
              </span>

              <strong>
                {computer.ip}
              </strong>
            </div>

            <div>
              <span>
                Operating System
              </span>

              <strong>
                {computer.os}
              </strong>
            </div>

            <div>
              <span>
                Last Seen
              </span>

              <strong>
                {computer.last}{" "}
                {computer.time}
              </strong>
            </div>

          </div>

        </div>

        {/* HARDWARE INFORMATION */}

        <div className="details-panel">

          <div className="details-panel-header">

            <h3>
              Hardware Information
            </h3>

          </div>

          <div className="details-info-grid">

            <div>
              <span>
                Processor
              </span>

              <strong>
                {computer.cpu}
              </strong>
            </div>

            <div>
              <span>
                RAM
              </span>

              <strong>
                {computer.ram}
              </strong>
            </div>

            <div>
              <span>
                Total Disk
              </span>

              <strong>
                {computer.total} GB
              </strong>
            </div>

            <div>
              <span>
                Free Disk
              </span>

              <strong>
                {computer.free} GB
              </strong>
            </div>

          </div>

        </div>

      </div>

      {/* =================================================
          STORAGE USAGE
      ================================================= */}

      <div className="details-panel disk-panel">

        <div className="details-panel-header">

          <h3>
            Storage Usage
          </h3>

        </div>

        <div className="large-disk">

          <div className="large-disk-label">

            <span>
              Disk Space
            </span>

            <strong>
              {computer.total -
                computer.free}{" "}
              GB used /{" "}
              {computer.total} GB
            </strong>

          </div>

          <div className="large-disk-track">

            <div
              className="large-disk-fill"
              style={{
                width: `${usedDisk}%`,
              }}
            />

          </div>

          <div className="large-disk-footer">

            <span>
              {usedDisk}% used
            </span>

            <span>
              {computer.free} GB
              available
            </span>

          </div>

        </div>

      </div>

      {/* =================================================
          NETWORK INFORMATION
      ================================================= */}

      <div className="details-panel">

        <div className="details-panel-header">

          <h3>
            Network Information
          </h3>

        </div>

        <div className="details-info-grid">

          <div>
            <span>
              IP Address
            </span>

            <strong>
              {computer.ip}
            </strong>
          </div>

          <div>
            <span>
              Connection
            </span>

            <strong>
              LAN / Ethernet
            </strong>
          </div>

          <div>
            <span>
              Network Status
            </span>

            <strong>
              {computer.status}
            </strong>
          </div>

          <div>
            <span>
              Last Heartbeat
            </span>

            <strong>
              {computer.last}{" "}
              {computer.time}
            </strong>
          </div>

        </div>

      </div>

    </div>
  );
}

export default ComputerDetails;