import Icon from "./Icon";

function ViewComputerModal({ computer, onClose }) {
  if (!computer) {
    return null;
  }

  const used = Math.round(
    ((computer.total - computer.free) /
      computer.total) *
      100
  );

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
    >
      <div
        className="modal view-modal"
        onClick={(e) => e.stopPropagation()}
      >
        {/* HEADER */}
        <div className="modal-header">
          <div className="modal-title">
            <div className="modal-icon">
              <Icon
                type="windows"
                size={24}
              />
            </div>

            <div>
              <h2>{computer.name}</h2>
              <p>Computer Details</p>
            </div>
          </div>

          <button
            className="modal-close"
            onClick={onClose}
          >
            ×
          </button>
        </div>

        {/* BODY */}
        <div className="modal-body">
          <h3>Computer Information</h3>

          <div className="details-grid">
            <div className="detail-item">
              <span>Computer Name</span>
              <b>{computer.name}</b>
            </div>

            <div className="detail-item">
              <span>IP Address</span>
              <b>{computer.ip}</b>
            </div>

            <div className="detail-item">
              <span>Operating System</span>
              <b>{computer.os}</b>
            </div>

            <div className="detail-item">
              <span>CPU</span>
              <b>{computer.cpu}</b>
            </div>

            <div className="detail-item">
              <span>RAM</span>
              <b>{computer.ram}</b>
            </div>

            <div className="detail-item">
              <span>Last Seen</span>
              <b>
                {computer.last} {computer.time}
              </b>
            </div>

            <div className="detail-item">
              <span>Status</span>

              <span
                className={`status ${computer.status.toLowerCase()}`}
              >
                <i />
                {computer.status}
              </span>
            </div>

            <div className="detail-item">
              <span>Lab</span>
              <b>{computer.lab}</b>
            </div>
          </div>

          {/* DISK */}
          <div className="disk-details">
            <div className="disk-details-header">
              <span>Disk Usage</span>
              <b>{used}% used</b>
            </div>

            <div className="disk-track">
              <div
                className="disk-fill"
                style={{
                  width: `${used}%`,
                }}
              />
            </div>

            <div className="disk-details-footer">
              <span>
                {computer.total - computer.free} GB used
              </span>

              <span>
                {computer.free} GB free of{" "}
                {computer.total} GB
              </span>
            </div>
          </div>
        </div>

        {/* FOOTER */}
        <div className="modal-footer">
          <button
            className="modal-button"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default ViewComputerModal;