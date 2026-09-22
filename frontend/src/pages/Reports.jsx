import { useMemo, useState } from "react";

import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

/* =====================================================
   DEMO REPORT DATA
===================================================== */

const computerData = [
  {
    id: "PC-01",
    name: "PC-01",
    os: "Windows 11",
    status: "Online",
    lab: "Lab 1",
  },
  {
    id: "PC-02",
    name: "PC-02",
    os: "Windows 11",
    status: "Online",
    lab: "Lab 1",
  },
  {
    id: "PC-03",
    name: "PC-03",
    os: "Windows 11",
    status: "Online",
    lab: "Lab 1",
  },
  {
    id: "PC-04",
    name: "PC-04",
    os: "Windows 11",
    status: "Online",
    lab: "Lab 1",
  },
  {
    id: "PC-05",
    name: "PC-05",
    os: "Windows 11",
    status: "Offline",
    lab: "Lab 1",
  },
  {
    id: "PC-06",
    name: "PC-06",
    os: "Windows 11",
    status: "Online",
    lab: "Lab 1",
  },
  {
    id: "PC-07",
    name: "PC-07",
    os: "Windows 7 Ultimate",
    status: "Offline",
    lab: "Lab 1",
  },
  {
    id: "PC-08",
    name: "PC-08",
    os: "Windows 11",
    status: "Online",
    lab: "Lab 1",
  },
];

const softwareData = [
  {
    name: "Google Chrome",
    version: "136.0.7103.114",
    category: "Browser",
    computer: "PC-01",
    status: "Up to Date",
  },
  {
    name: "Visual Studio Code",
    version: "1.100.2",
    category: "Development",
    computer: "PC-04",
    status: "Up to Date",
  },
  {
    name: "Node.js",
    version: "20.15.1",
    category: "Development",
    computer: "PC-06",
    status: "Outdated",
  },
  {
    name: "Adobe Acrobat Reader",
    version: "24.005.20320",
    category: "Office",
    computer: "PC-08",
    status: "Outdated",
  },
];

const issueData = [
  {
    computer: "PC-05",
    issue: "High CPU Usage",
    priority: "High",
    status: "Open",
  },
  {
    computer: "PC-07",
    issue: "Computer Offline",
    priority: "Critical",
    status: "Open",
  },
  {
    computer: "PC-12",
    issue: "Low Disk Space",
    priority: "High",
    status: "In Progress",
  },
  {
    computer: "PC-20",
    issue: "High Memory Usage",
    priority: "Medium",
    status: "In Progress",
  },
];

const maintenanceData = [
  {
    computer: "PC-05",
    issue: "High CPU Usage",
    technician: "Lab Technician",
    status: "Pending",
  },
  {
    computer: "PC-07",
    issue: "Computer Offline",
    technician: "Lab Technician",
    status: "In Progress",
  },
  {
    computer: "PC-20",
    issue: "High Memory Usage",
    technician: "Lab Technician",
    status: "Completed",
  },
  {
    computer: "PC-24",
    issue: "Outdated Software",
    technician: "System Administrator",
    status: "Completed",
  },
];

/* =====================================================
   COMPONENT
===================================================== */

function Reports() {
  const [reportType, setReportType] =
    useState("Computer Report");

  const [dateFrom, setDateFrom] =
    useState("");

  const [dateTo, setDateTo] =
    useState("");

  const [message, setMessage] =
    useState("");

  /* =====================================================
     REPORT COUNTS
  ===================================================== */

  const totalComputers = 24;

  const onlineComputers = 18;

  const offlineComputers =
    totalComputers -
    onlineComputers;

  const totalSoftware = 24;

  const totalIssues = 8;

  const totalMaintenance = 8;

  /* =====================================================
     REPORT INFORMATION
  ===================================================== */

  const reportInfo = useMemo(() => {
    if (
      reportType ===
      "Computer Report"
    ) {
      return {
        title: "Computer Report",
        description:
          "Detailed information about registered laboratory computers.",
        count: totalComputers,
        label: "Computers",
      };
    }

    if (
      reportType ===
      "Software Report"
    ) {
      return {
        title: "Software Report",
        description:
          "Installed software reported by client computers.",
        count: totalSoftware,
        label: "Software Records",
      };
    }

    if (
      reportType ===
      "Issue Report"
    ) {
      return {
        title: "Issue Report",
        description:
          "Issues reported by laboratory computers.",
        count: totalIssues,
        label: "Issues",
      };
    }

    return {
      title: "Maintenance Report",
      description:
        "Maintenance and service records for laboratory computers.",
      count: totalMaintenance,
      label: "Maintenance Records",
    };
  }, [reportType]);

  /* =====================================================
     CSV HELPER
  ===================================================== */

  const downloadCSV = (
    filename,
    headers,
    rows
  ) => {
    const csvRows = [
      headers.join(","),
      ...rows.map((row) =>
        row
          .map((value) =>
            `"${String(value).replace(
              /"/g,
              '""'
            )}"`
          )
          .join(",")
      ),
    ];

    const csvContent =
      csvRows.join("\n");

    const blob = new Blob(
      [csvContent],
      {
        type: "text/csv;charset=utf-8;",
      }
    );

    const url =
      URL.createObjectURL(blob);

    const link =
      document.createElement("a");

    link.href = url;

    link.download = filename;

    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  };

  /* =====================================================
     EXPORT REPORT
  ===================================================== */

  const exportReport = () => {
    setMessage("");

    if (
      reportType ===
      "Computer Report"
    ) {
      downloadCSV(
        "SLMS-Computer-Report.csv",
        [
          "Computer ID",
          "Computer Name",
          "Operating System",
          "Status",
          "Lab",
        ],
        computerData.map(
          (computer) => [
            computer.id,
            computer.name,
            computer.os,
            computer.status,
            computer.lab,
          ]
        )
      );
    }

    if (
      reportType ===
      "Software Report"
    ) {
      downloadCSV(
        "SLMS-Software-Report.csv",
        [
          "Software Name",
          "Version",
          "Category",
          "Computer",
          "Status",
        ],
        softwareData.map(
          (software) => [
            software.name,
            software.version,
            software.category,
            software.computer,
            software.status,
          ]
        )
      );
    }

    if (
      reportType ===
      "Issue Report"
    ) {
      downloadCSV(
        "SLMS-Issue-Report.csv",
        [
          "Computer",
          "Issue",
          "Priority",
          "Status",
        ],
        issueData.map(
          (issue) => [
            issue.computer,
            issue.issue,
            issue.priority,
            issue.status,
          ]
        )
      );
    }

    if (
      reportType ===
      "Maintenance Report"
    ) {
      downloadCSV(
        "SLMS-Maintenance-Report.csv",
        [
          "Computer",
          "Issue",
          "Technician",
          "Status",
        ],
        maintenanceData.map(
          (record) => [
            record.computer,
            record.issue,
            record.technician,
            record.status,
          ]
        )
      );
    }

    setMessage(
      `${reportType} exported successfully.`
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
            Reports
          </h2>

          <p>
            Generate and export reports
            about the laboratory system.
          </p>
        </div>

      </div>

      {/* =================================================
          STAT CARDS
      ================================================= */}

      <div className="cards">

        <StatCard
          icon="computer"
          title="Computer Report"
          number={totalComputers}
          footer="Registered computers"
          type="blue"
        />

        <StatCard
          icon="software"
          title="Software Report"
          number={totalSoftware}
          footer="Software records"
          type="green"
        />

        <StatCard
          icon="issue"
          title="Issue Report"
          number={totalIssues}
          footer="Reported issues"
          type="orange"
        />

        <StatCard
          icon="maintenance"
          title="Maintenance"
          number={totalMaintenance}
          footer="Maintenance records"
          type="purple"
        />

      </div>

      {/* =================================================
          REPORT GENERATOR
      ================================================= */}

      <div className="report-generator">

        <div className="page-section-header">

          <div>
            <h3>
              Generate Report
            </h3>

            <p>
              Select a report type and
              export the available data.
            </p>
          </div>

        </div>

        <div className="report-controls">

          {/* REPORT TYPE */}

          <div className="report-field">

            <label>
              Report Type
            </label>

            <select
              value={reportType}
              onChange={(event) =>
                setReportType(
                  event.target.value
                )
              }
            >

              <option>
                Computer Report
              </option>

              <option>
                Software Report
              </option>

              <option>
                Issue Report
              </option>

              <option>
                Maintenance Report
              </option>

            </select>

          </div>

          {/* FROM DATE */}

          <div className="report-field">

            <label>
              From Date
            </label>

            <input
              type="date"
              value={dateFrom}
              onChange={(event) =>
                setDateFrom(
                  event.target.value
                )
              }
            />

          </div>

          {/* TO DATE */}

          <div className="report-field">

            <label>
              To Date
            </label>

            <input
              type="date"
              value={dateTo}
              onChange={(event) =>
                setDateTo(
                  event.target.value
                )
              }
            />

          </div>

          {/* EXPORT */}

          <button
            className="report-export-button"
            onClick={exportReport}
          >

            <Icon
              type="download"
              size={18}
            />

            Export Report

          </button>

        </div>

        {/* SUCCESS MESSAGE */}

        {message && (
          <div className="report-message">
            <Icon
              type="check"
              size={16}
            />

            {message}
          </div>
        )}

      </div>

      {/* =================================================
          SELECTED REPORT
      ================================================= */}

      <div className="report-preview">

        <div className="report-preview-header">

          <div>

            <h3>
              {reportInfo.title}
            </h3>

            <p>
              {reportInfo.description}
            </p>

          </div>

          <div className="report-count">

            <strong>
              {reportInfo.count}
            </strong>

            <span>
              {reportInfo.label}
            </span>

          </div>

        </div>

        {/* =================================================
            COMPUTER REPORT PREVIEW
        ================================================= */}

        {reportType ===
          "Computer Report" && (

          <div className="report-summary-grid">

            <div className="report-summary-item">

              <span>
                Total Computers
              </span>

              <strong>
                24
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                Online
              </span>

              <strong>
                {onlineComputers}
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                Offline
              </span>

              <strong>
                {offlineComputers}
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                Labs
              </span>

              <strong>
                2
              </strong>

            </div>

          </div>

        )}

        {/* =================================================
            SOFTWARE REPORT PREVIEW
        ================================================= */}

        {reportType ===
          "Software Report" && (

          <div className="report-summary-grid">

            <div className="report-summary-item">

              <span>
                Software Records
              </span>

              <strong>
                24
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                Computers Scanned
              </span>

              <strong>
                24
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                Outdated
              </span>

              <strong>
                4
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                Categories
              </span>

              <strong>
                8
              </strong>

            </div>

          </div>

        )}

        {/* =================================================
            ISSUE REPORT PREVIEW
        ================================================= */}

        {reportType ===
          "Issue Report" && (

          <div className="report-summary-grid">

            <div className="report-summary-item">

              <span>
                Total Issues
              </span>

              <strong>
                8
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                Open
              </span>

              <strong>
                4
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                In Progress
              </span>

              <strong>
                2
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                Resolved
              </span>

              <strong>
                2
              </strong>

            </div>

          </div>

        )}

        {/* =================================================
            MAINTENANCE REPORT PREVIEW
        ================================================= */}

        {reportType ===
          "Maintenance Report" && (

          <div className="report-summary-grid">

            <div className="report-summary-item">

              <span>
                Total Records
              </span>

              <strong>
                8
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                Pending
              </span>

              <strong>
                3
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                In Progress
              </span>

              <strong>
                2
              </strong>

            </div>

            <div className="report-summary-item">

              <span>
                Completed
              </span>

              <strong>
                3
              </strong>

            </div>

          </div>

        )}

      </div>

    </div>
  );
}

export default Reports;