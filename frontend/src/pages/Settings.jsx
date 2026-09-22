import { useState } from "react";

import Icon from "../components/Icon";

/* =====================================================
   SETTINGS PAGE
===================================================== */

function Settings() {
  /* =====================================================
     LAB SETTINGS
  ===================================================== */

  const [labName, setLabName] =
    useState("Computer Laboratory");

  const [labLocation, setLabLocation] =
    useState("Andhra Polytechnic");

  const [labNetwork, setLabNetwork] =
    useState("LAN / Ethernet");

  /* =====================================================
     MONITORING SETTINGS
  ===================================================== */

  const [cpuThreshold, setCpuThreshold] =
    useState(85);

  const [ramThreshold, setRamThreshold] =
    useState(85);

  const [diskThreshold, setDiskThreshold] =
    useState(90);

  const [heartbeatInterval, setHeartbeatInterval] =
    useState(30);

  /* =====================================================
     NOTIFICATION SETTINGS
  ===================================================== */

  const [diskAlerts, setDiskAlerts] =
    useState(true);

  const [offlineAlerts, setOfflineAlerts] =
    useState(true);

  const [issueAlerts, setIssueAlerts] =
    useState(true);

  const [softwareAlerts, setSoftwareAlerts] =
    useState(false);

  /* =====================================================
     AGENT SETTINGS
  ===================================================== */

  const [autoStartAgent, setAutoStartAgent] =
    useState(true);

  const [collectProcesses, setCollectProcesses] =
    useState(true);

  const [collectSoftware, setCollectSoftware] =
    useState(true);

  /* =====================================================
     SAVE MESSAGE
  ===================================================== */

  const [saved, setSaved] =
    useState(false);

  /* =====================================================
     SAVE SETTINGS
  ===================================================== */

  const handleSave = () => {
    setSaved(true);

    setTimeout(() => {
      setSaved(false);
    }, 3000);
  };

  /* =====================================================
     RESET SETTINGS
  ===================================================== */

  const handleReset = () => {
    setLabName(
      "Computer Laboratory"
    );

    setLabLocation(
      "Andhra Polytechnic"
    );

    setLabNetwork(
      "LAN / Ethernet"
    );

    setCpuThreshold(85);
    setRamThreshold(85);
    setDiskThreshold(90);
    setHeartbeatInterval(30);

    setDiskAlerts(true);
    setOfflineAlerts(true);
    setIssueAlerts(true);
    setSoftwareAlerts(false);

    setAutoStartAgent(true);
    setCollectProcesses(true);
    setCollectSoftware(true);
  };

  /* =====================================================
     TOGGLE COMPONENT
  ===================================================== */

  const Toggle = ({
    checked,
    onChange,
  }) => {
    return (
      <button
        type="button"
        className={
          `settings-toggle ${
            checked
              ? "active"
              : ""
          }`
        }
        onClick={() =>
          onChange(!checked)
        }
        aria-label="Toggle setting"
      >
        <span />
      </button>
    );
  };

  /* =====================================================
     RETURN
  ===================================================== */

  return (
    <div className="content">

      {/* =================================================
          PAGE HEADER
      ================================================= */}

      <div className="page-top">

        <div>
          <h2>
            Settings
          </h2>

          <p>
            Configure SLMS monitoring,
            laboratory, agent, and
            notification settings.
          </p>
        </div>

        <div className="settings-actions">

          <button
            className="settings-reset"
            onClick={handleReset}
          >
            <Icon
              type="refresh"
              size={16}
            />

            Reset
          </button>

          <button
            className="settings-save"
            onClick={handleSave}
          >
            <Icon
              type="check"
              size={16}
            />

            Save Changes
          </button>

        </div>

      </div>

      {/* =================================================
          SAVE MESSAGE
      ================================================= */}

      {saved && (
        <div className="settings-success">

          <Icon
            type="check"
            size={17}
          />

          Settings saved successfully.

        </div>
      )}

      {/* =================================================
          LAB CONFIGURATION
      ================================================= */}

      <div className="settings-panel">

        <div className="settings-panel-header">

          <div className="settings-section-icon blue">
            <Icon
              type="computer"
              size={20}
            />
          </div>

          <div>
            <h3>
              Laboratory Configuration
            </h3>

            <p>
              Configure the basic information
              used by the SLMS system.
            </p>
          </div>

        </div>

        <div className="settings-form-grid">

          <div className="settings-field">

            <label>
              Laboratory Name
            </label>

            <input
              type="text"
              value={labName}
              onChange={(event) =>
                setLabName(
                  event.target.value
                )
              }
            />

          </div>

          <div className="settings-field">

            <label>
              Laboratory Location
            </label>

            <input
              type="text"
              value={labLocation}
              onChange={(event) =>
                setLabLocation(
                  event.target.value
                )
              }
            />

          </div>

          <div className="settings-field">

            <label>
              Network Type
            </label>

            <select
              value={labNetwork}
              onChange={(event) =>
                setLabNetwork(
                  event.target.value
                )
              }
            >
              <option>
                LAN / Ethernet
              </option>

              <option>
                Wi-Fi
              </option>

            </select>

          </div>

        </div>

      </div>

      {/* =================================================
          MONITORING SETTINGS
      ================================================= */}

      <div className="settings-panel">

        <div className="settings-panel-header">

          <div className="settings-section-icon orange">
            <Icon
              type="issue"
              size={20}
            />
          </div>

          <div>
            <h3>
              Monitoring Thresholds
            </h3>

            <p>
              Configure when SLMS should
              report resource usage problems.
            </p>
          </div>

        </div>

        <div className="settings-form-grid">

          {/* CPU */}

          <div className="settings-field">

            <label>
              CPU Warning Threshold (%)
            </label>

            <input
              type="number"
              min="1"
              max="100"
              value={cpuThreshold}
              onChange={(event) =>
                setCpuThreshold(
                  event.target.value
                )
              }
            />

            <small>
              Alert when CPU usage
              exceeds this value.
            </small>

          </div>

          {/* RAM */}

          <div className="settings-field">

            <label>
              RAM Warning Threshold (%)
            </label>

            <input
              type="number"
              min="1"
              max="100"
              value={ramThreshold}
              onChange={(event) =>
                setRamThreshold(
                  event.target.value
                )
              }
            />

            <small>
              Alert when memory usage
              exceeds this value.
            </small>

          </div>

          {/* DISK */}

          <div className="settings-field">

            <label>
              Disk Warning Threshold (%)
            </label>

            <input
              type="number"
              min="1"
              max="100"
              value={diskThreshold}
              onChange={(event) =>
                setDiskThreshold(
                  event.target.value
                )
              }
            />

            <small>
              Alert when disk usage
              exceeds this value.
            </small>

          </div>

          {/* HEARTBEAT */}

          <div className="settings-field">

            <label>
              Agent Heartbeat (seconds)
            </label>

            <input
              type="number"
              min="5"
              max="300"
              value={heartbeatInterval}
              onChange={(event) =>
                setHeartbeatInterval(
                  event.target.value
                )
              }
            />

            <small>
              Time between client agent
              heartbeat messages.
            </small>

          </div>

        </div>

      </div>

      {/* =================================================
          NOTIFICATIONS
      ================================================= */}

      <div className="settings-panel">

        <div className="settings-panel-header">

          <div className="settings-section-icon purple">
            <Icon
              type="notification"
              size={20}
            />
          </div>

          <div>
            <h3>
              Notifications
            </h3>

            <p>
              Choose which system events
              should generate notifications.
            </p>
          </div>

        </div>

        <div className="settings-options">

          {/* DISK ALERT */}

          <div className="settings-option">

            <div>

              <strong>
                Low Disk Space Alerts
              </strong>

              <p>
                Notify when a computer's
                disk usage exceeds the threshold.
              </p>

            </div>

            <Toggle
              checked={diskAlerts}
              onChange={
                setDiskAlerts
              }
            />

          </div>

          {/* OFFLINE ALERT */}

          <div className="settings-option">

            <div>

              <strong>
                Computer Offline Alerts
              </strong>

              <p>
                Notify when a client computer
                stops sending heartbeats.
              </p>

            </div>

            <Toggle
              checked={offlineAlerts}
              onChange={
                setOfflineAlerts
              }
            />

          </div>

          {/* ISSUE ALERT */}

          <div className="settings-option">

            <div>

              <strong>
                Issue Notifications
              </strong>

              <p>
                Notify when a client agent
                reports a system problem.
              </p>

            </div>

            <Toggle
              checked={issueAlerts}
              onChange={
                setIssueAlerts
              }
            />

          </div>

          {/* SOFTWARE ALERT */}

          <div className="settings-option">

            <div>

              <strong>
                Software Update Alerts
              </strong>

              <p>
                Notify when outdated software
                is detected.
              </p>

            </div>

            <Toggle
              checked={softwareAlerts}
              onChange={
                setSoftwareAlerts
              }
            />

          </div>

        </div>

      </div>

      {/* =================================================
          CLIENT AGENT
      ================================================= */}

      <div className="settings-panel">

        <div className="settings-panel-header">

          <div className="settings-section-icon green">
            <Icon
              type="computer"
              size={20}
            />
          </div>

          <div>
            <h3>
              Client Agent
            </h3>

            <p>
              Configure information collected
              by the SLMS client agent.
            </p>
          </div>

        </div>

        <div className="settings-options">

          {/* AUTO START */}

          <div className="settings-option">

            <div>

              <strong>
                Start Agent Automatically
              </strong>

              <p>
                Start the SLMS client agent
                when Windows starts.
              </p>

            </div>

            <Toggle
              checked={autoStartAgent}
              onChange={
                setAutoStartAgent
              }
            />

          </div>

          {/* PROCESSES */}

          <div className="settings-option">

            <div>

              <strong>
                Process Monitoring
              </strong>

              <p>
                Collect running process
                information from client computers.
              </p>

            </div>

            <Toggle
              checked={collectProcesses}
              onChange={
                setCollectProcesses
              }
            />

          </div>

          {/* SOFTWARE */}

          <div className="settings-option">

            <div>

              <strong>
                Software Inventory
              </strong>

              <p>
                Collect installed software
                information from client computers.
              </p>

            </div>

            <Toggle
              checked={collectSoftware}
              onChange={
                setCollectSoftware
              }
            />

          </div>

        </div>

      </div>

    </div>
  );
}

export default Settings;