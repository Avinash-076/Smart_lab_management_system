import { useState } from "react";
import "./EditComputerModal.css";

function EditComputerModal({ computer, onClose, onSave }) {
  const [f, setF] = useState(() => ({
    name: computer?.hostname || computer?.name || "",
    ip: computer?.ip_address || computer?.ip || "",
    os: computer?.os_name
      ? `${computer.os_name} ${computer.os_version || ""}`.trim()
      : computer?.os || "",
    cpu: computer?.cpu || "",
    ram: computer?.ram || "",
    free:
      computer?.disk_free !== undefined
        ? computer.disk_free
        : computer?.free !== undefined
        ? computer.free
        : "",
    total:
      computer?.disk_total !== undefined
        ? computer.disk_total
        : computer?.total !== undefined
        ? computer.total
        : "",
    status:
      (computer?.status || "offline").toLowerCase() === "online"
        ? "Online"
        : "Offline",
    lab: computer?.lab || "Lab 1",
    ...computer,
  }));

  if (!computer) return null;

  const update = (key, value) => {
    setF((prev) => ({
      ...prev,
      [key]: value,
    }));
  };

  const handleSave = () => {
    if (!f.name?.trim() || !f.ip?.trim()) {
      alert("Please enter a valid computer name and IP address.");
      return;
    }

    const freeNum = f.free !== "" ? Number(f.free) : undefined;
    const totalNum = f.total !== "" ? Number(f.total) : undefined;

    if (totalNum !== undefined && freeNum !== undefined && freeNum > totalNum) {
      alert("Free disk cannot exceed total disk.");
      return;
    }

    onSave({
      ...computer,
      ...f,
      hostname: f.name.trim(),
      name: f.name.trim(),
      ip_address: f.ip.trim(),
      ip: f.ip.trim(),
      os_name: f.os.trim(),
      status: f.status.toLowerCase(),
      disk_free: freeNum,
      disk_total: totalNum,
      free: freeNum,
      total: totalNum,
    });
  };

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="edit-dialog-title"
    >
      <div className="edit-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="edit-modal__header">
          <div>
            <h2 id="edit-dialog-title" className="edit-modal__title">
              Edit Computer
            </h2>
            <p className="edit-modal__subtitle">Update computer information</p>
          </div>
          <button
            type="button"
            className="edit-modal__close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            ×
          </button>
        </div>

        <div className="edit-modal__body">
          <div className="edit-modal__grid">
            <div className="edit-modal__form-group">
              <label htmlFor="edit-name">Computer Name</label>
              <input
                id="edit-name"
                className="edit-modal__input"
                value={f.name}
                onChange={(e) => update("name", e.target.value)}
              />
            </div>

            <div className="edit-modal__form-group">
              <label htmlFor="edit-ip">IP Address</label>
              <input
                id="edit-ip"
                className="edit-modal__input"
                value={f.ip}
                onChange={(e) => update("ip", e.target.value)}
              />
            </div>

            <div className="edit-modal__form-group">
              <label htmlFor="edit-os">Operating System</label>
              <input
                id="edit-os"
                className="edit-modal__input"
                value={f.os}
                onChange={(e) => update("os", e.target.value)}
              />
            </div>

            <div className="edit-modal__form-group">
              <label htmlFor="edit-status">Status</label>
              <select
                id="edit-status"
                className="edit-modal__select"
                value={f.status}
                onChange={(e) => update("status", e.target.value)}
              >
                <option value="Online">Online</option>
                <option value="Offline">Offline</option>
              </select>
            </div>

            <div className="edit-modal__form-group">
              <label htmlFor="edit-cpu">CPU</label>
              <input
                id="edit-cpu"
                className="edit-modal__input"
                value={f.cpu}
                onChange={(e) => update("cpu", e.target.value)}
              />
            </div>

            <div className="edit-modal__form-group">
              <label htmlFor="edit-ram">RAM</label>
              <input
                id="edit-ram"
                className="edit-modal__input"
                value={f.ram}
                onChange={(e) => update("ram", e.target.value)}
              />
            </div>

            <div className="edit-modal__form-group">
              <label htmlFor="edit-free">Free Disk (GB)</label>
              <input
                id="edit-free"
                type="number"
                className="edit-modal__input"
                value={f.free}
                onChange={(e) => update("free", e.target.value)}
              />
            </div>

            <div className="edit-modal__form-group">
              <label htmlFor="edit-total">Total Disk (GB)</label>
              <input
                id="edit-total"
                type="number"
                className="edit-modal__input"
                value={f.total}
                onChange={(e) => update("total", e.target.value)}
              />
            </div>

            <div className="edit-modal__form-group" style={{ gridColumn: "span 2" }}>
              <label htmlFor="edit-lab">Lab Assignment</label>
              <select
                id="edit-lab"
                className="edit-modal__select"
                value={f.lab}
                onChange={(e) => update("lab", e.target.value)}
              >
                <option value="Lab 1">Lab 1</option>
                <option value="Lab 2">Lab 2</option>
                <option value="Lab 3">Lab 3</option>
              </select>
            </div>
          </div>
        </div>

        <div className="edit-modal__footer">
          <button type="button" className="btn-cancel" onClick={onClose}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={handleSave}>
            Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}

export default EditComputerModal;