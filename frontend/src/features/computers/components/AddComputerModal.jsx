import { useState } from "react";
import Icon from "../../../components/ui/Icon";
import { generateEnrollmentKey } from "../../../services/computerService";
import "./AddComputerModal.css";

function AddComputerModal({ onClose, onComputerAdded }) {
  const [loading, setLoading] = useState(false);
  const [enrollmentKey, setEnrollmentKey] = useState(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState("");

  const handleGenerateKey = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await generateEnrollmentKey();
      if (res && res.enrollment_key) {
        setEnrollmentKey(res.enrollment_key);
      } else {
        throw new Error("Invalid response from server.");
      }
    } catch (err) {
      setError(
        err.message ||
          "Failed to generate enrollment key. Ensure you have the PROVISION_AGENT permission."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleCopyCommand = () => {
    const cmd = `python main.py --enroll ${enrollmentKey}`;
    navigator.clipboard?.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="add-modal-title"
    >
      <div className="add-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="add-modal__header">
          <h2 id="add-modal-title" className="add-modal__title">
            Add Lab Computer
          </h2>
          <button
            type="button"
            className="add-modal__close-btn"
            onClick={onClose}
            aria-label="Close dialog"
          >
            ×
          </button>
        </div>

        <div className="add-modal__body">
          <p className="add-modal__desc">
            In SLMS, laboratory computers automatically enroll and start reporting real-time
            hardware telemetry by running the client agent with a provisioning key.
          </p>

          {!enrollmentKey ? (
            <div className="add-modal__box">
              <div className="add-modal__box-title">
                <Icon type="computer" size={16} />
                Generate Provisioning Token
              </div>
              <p style={{ margin: "4px 0 12px", fontSize: "12.5px", color: "#64748b" }}>
                Generate a single-use agent enrollment key to provision a new lab computer.
              </p>
              <button
                type="button"
                className="btn-primary"
                onClick={handleGenerateKey}
                disabled={loading}
              >
                <Icon type="plus" size={15} />
                {loading ? "Generating Key..." : "Generate Enrollment Key"}
              </button>
            </div>
          ) : (
            <div className="add-modal__box">
              <div className="add-modal__box-title" style={{ color: "#16a34a" }}>
                <Icon type="pulse" size={16} />
                Agent Enrollment Key Ready
              </div>
              <p style={{ margin: "4px 0 8px", fontSize: "12.5px", color: "#475569" }}>
                Run the following command on the target lab workstation terminal:
              </p>
              <div className="add-modal__code-block">
                <span>python main.py --enroll {enrollmentKey}</span>
                <button
                  type="button"
                  className="add-modal__copy-btn"
                  onClick={handleCopyCommand}
                >
                  {copied ? "Copied! ✓" : "Copy"}
                </button>
              </div>
              <p style={{ margin: "10px 0 0", fontSize: "11.5px", color: "#94a3b8" }}>
                Once executed, the computer will automatically register and appear in the
                Computers inventory table.
              </p>
            </div>
          )}

          {error && (
            <div style={{ color: "#dc2626", marginTop: "12px", fontSize: "12.5px" }}>
              {error}
            </div>
          )}
        </div>

        <div className="add-modal__footer">
          <button type="button" className="btn-cancel" onClick={onClose}>
            Close
          </button>
          {enrollmentKey && (
            <button
              type="button"
              className="btn-primary"
              onClick={() => {
                onClose();
                onComputerAdded?.();
              }}
            >
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default AddComputerModal;
