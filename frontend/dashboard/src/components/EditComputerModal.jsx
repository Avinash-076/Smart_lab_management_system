import { useState } from "react";

function EditComputerModal({
  computer,
  onClose,
  onSave,
}) {
  const [f, setF] = useState({
    ...computer,
  });

  if (!computer) {
    return null;
  }

  const update = (key, value) => {
    setF((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSave = () => {
    const free = Number(f.free);
    const total = Number(f.total);

    if (
      !f.name.trim() ||
      !f.ip.trim() ||
      free < 0 ||
      total <= 0 ||
      free > total
    ) {
      alert("Please enter valid details.");
      return;
    }

    onSave({
      ...f,
      free,
      total,
    });
  };

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
    >
      <div
        className="modal edit-modal"
        onClick={(e) => e.stopPropagation()}
      >
        {/* HEADER */}
        <div className="modal-header">
          <div>
            <h2>Edit Computer</h2>
            <p>Update computer information</p>
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
          <div className="form-grid">
            <div className="form-group">
              <label>Computer Name</label>

              <input
                value={f.name}
                onChange={(e) =>
                  update("name", e.target.value)
                }
              />
            </div>

            <div className="form-group">
              <label>IP Address</label>

              <input
                value={f.ip}
                onChange={(e) =>
                  update("ip", e.target.value)
                }
              />
            </div>

            <div className="form-group">
              <label>Operating System</label>

              <input
                value={f.os}
                onChange={(e) =>
                  update("os", e.target.value)
                }
              />
            </div>

            <div className="form-group">
              <label>CPU</label>

              <input
                value={f.cpu}
                onChange={(e) =>
                  update("cpu", e.target.value)
                }
              />
            </div>

            <div className="form-group">
              <label>RAM</label>

              <input
                value={f.ram}
                onChange={(e) =>
                  update("ram", e.target.value)
                }
              />
            </div>

            <div className="form-group">
              <label>Free Disk (GB)</label>

              <input
                type="number"
                value={f.free}
                onChange={(e) =>
                  update("free", e.target.value)
                }
              />
            </div>

            <div className="form-group">
              <label>Total Disk (GB)</label>

              <input
                type="number"
                value={f.total}
                onChange={(e) =>
                  update("total", e.target.value)
                }
              />
            </div>

            <div className="form-group">
              <label>Last Seen Date</label>

              <input
                value={f.last}
                onChange={(e) =>
                  update("last", e.target.value)
                }
              />
            </div>

            <div className="form-group">
              <label>Last Seen Time</label>

              <input
                value={f.time}
                onChange={(e) =>
                  update("time", e.target.value)
                }
              />
            </div>

            <div className="form-group">
              <label>Status</label>

              <select
                value={f.status}
                onChange={(e) =>
                  update("status", e.target.value)
                }
              >
                <option>Online</option>
                <option>Offline</option>
              </select>
            </div>

            <div className="form-group">
              <label>Lab</label>

              <select
                value={f.lab}
                onChange={(e) =>
                  update("lab", e.target.value)
                }
              >
                <option>Lab 1</option>
                <option>Lab 2</option>
              </select>
            </div>
          </div>
        </div>

        {/* FOOTER */}
        <div className="modal-footer">
          <button
            className="modal-button secondary"
            onClick={onClose}
          >
            Cancel
          </button>

          <button
            className="modal-button primary"
            onClick={handleSave}
          >
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

export default EditComputerModal;