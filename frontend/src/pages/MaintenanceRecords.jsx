import { useMemo, useState } from "react";

import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

/* =====================================================
   MAINTENANCE DATA
===================================================== */

const maintenanceData = [
  {
    id: 1,
    computer: "PC-05",
    issue: "High CPU Usage",
    technician: "Lab Technician",
    priority: "High",
    status: "Pending",
    scheduled: "22 Sep 2026",
    completed: "-",
    notes: "Check background processes and CPU-intensive applications.",
  },
  {
    id: 2,
    computer: "PC-07",
    issue: "Computer Offline",
    technician: "Lab Technician",
    priority: "Critical",
    status: "In Progress",
    scheduled: "21 Sep 2026",
    completed: "-",
    notes: "Check network connection and client agent service.",
  },
  {
    id: 3,
    computer: "PC-12",
    issue: "Low Disk Space",
    technician: "System Administrator",
    priority: "High",
    status: "In Progress",
    scheduled: "21 Sep 2026",
    completed: "-",
    notes: "Remove temporary files and unnecessary applications.",
  },
  {
    id: 4,
    computer: "PC-16",
    issue: "Computer Offline",
    technician: "Lab Technician",
    priority: "Critical",
    status: "Pending",
    scheduled: "23 Sep 2026",
    completed: "-",
    notes: "Verify power and LAN connectivity.",
  },
  {
    id: 5,
    computer: "PC-20",
    issue: "High Memory Usage",
    technician: "Lab Technician",
    priority: "Medium",
    status: "Completed",
    scheduled: "18 Sep 2026",
    completed: "18 Sep 2026",
    notes: "Closed unnecessary applications and reviewed startup programs.",
  },
  {
    id: 6,
    computer: "PC-24",
    issue: "Outdated Software",
    technician: "System Administrator",
    priority: "Low",
    status: "Completed",
    scheduled: "17 Sep 2026",
    completed: "17 Sep 2026",
    notes: "Updated the reported software packages.",
  },
  {
    id: 7,
    computer: "PC-03",
    issue: "High CPU Usage",
    technician: "Lab Technician",
    priority: "Medium",
    status: "Completed",
    scheduled: "16 Sep 2026",
    completed: "16 Sep 2026",
    notes: "Identified and closed unnecessary background processes.",
  },
  {
    id: 8,
    computer: "PC-09",
    issue: "Low Disk Space",
    technician: "System Administrator",
    priority: "High",
    status: "Pending",
    scheduled: "24 Sep 2026",
    completed: "-",
    notes: "Disk cleanup and storage inspection required.",
  },
];

/* =====================================================
   COMPONENT
===================================================== */

function MaintenanceRecords() {
  const [search, setSearch] =
    useState("");

  const [statusFilter, setStatusFilter] =
    useState("All Status");

  const [priorityFilter, setPriorityFilter] =
    useState("All Priority");

  const [computerFilter, setComputerFilter] =
    useState("All Computers");

  /* =====================================================
     COMPUTER LIST
  ===================================================== */

  const computers = [
    ...new Set(
      maintenanceData.map(
        (record) => record.computer
      )
    ),
  ];

  /* =====================================================
     FILTER RECORDS
  ===================================================== */

  const filteredRecords = useMemo(() => {
    const searchText =
      search.toLowerCase().trim();

    return maintenanceData.filter(
      (record) => {
        const matchesSearch =
          !searchText ||
          record.computer
            .toLowerCase()
            .includes(searchText) ||
          record.issue
            .toLowerCase()
            .includes(searchText) ||
          record.technician
            .toLowerCase()
            .includes(searchText);

        const matchesStatus =
          statusFilter === "All Status" ||
          record.status === statusFilter;

        const matchesPriority =
          priorityFilter === "All Priority" ||
          record.priority === priorityFilter;

        const matchesComputer =
          computerFilter === "All Computers" ||
          record.computer === computerFilter;

        return (
          matchesSearch &&
          matchesStatus &&
          matchesPriority &&
          matchesComputer
        );
      }
    );
  }, [
    search,
    statusFilter,
    priorityFilter,
    computerFilter,
  ]);

  /* =====================================================
     STATISTICS
  ===================================================== */

  const totalRecords =
    maintenanceData.length;

  const pendingRecords =
    maintenanceData.filter(
      (record) =>
        record.status === "Pending"
    ).length;

  const inProgressRecords =
    maintenanceData.filter(
      (record) =>
        record.status === "In Progress"
    ).length;

  const completedRecords =
    maintenanceData.filter(
      (record) =>
        record.status === "Completed"
    ).length;

  /* =====================================================
     RESET FILTERS
  ===================================================== */

  const resetFilters = () => {
    setSearch("");
    setStatusFilter("All Status");
    setPriorityFilter("All Priority");
    setComputerFilter("All Computers");
  };

  /* =====================================================
     PRIORITY CLASS
  ===================================================== */

  const getPriorityClass = (priority) => {
    if (priority === "Critical") {
      return "maintenance-critical";
    }

    if (priority === "High") {
      return "maintenance-high";
    }

    if (priority === "Medium") {
      return "maintenance-medium";
    }

    return "maintenance-low";
  };

  /* =====================================================
     STATUS CLASS
  ===================================================== */

  const getStatusClass = (recordStatus) => {
    if (recordStatus === "Completed") {
      return "maintenance-completed";
    }

    if (recordStatus === "In Progress") {
      return "maintenance-progress";
    }

    return "maintenance-pending";
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
            Maintenance Records
          </h2>

          <p>
            Track computer maintenance,
            repairs, and service activities.
          </p>
        </div>

      </div>

      {/* =================================================
          STAT CARDS
      ================================================= */}

      <div className="cards">

        <StatCard
          icon="maintenance"
          title="Total Records"
          number={totalRecords}
          footer="All maintenance records"
          type="blue"
        />

        <StatCard
          icon="issue"
          title="Pending"
          number={pendingRecords}
          footer="Waiting for maintenance"
          type="orange"
        />

        <StatCard
          icon="maintenance"
          title="In Progress"
          number={inProgressRecords}
          footer="Currently being serviced"
          type="purple"
        />

        <StatCard
          icon="check"
          title="Completed"
          number={completedRecords}
          footer="Completed maintenance"
          type="green"
        />

      </div>

      {/* =================================================
          MAINTENANCE TABLE
      ================================================= */}

      <div className="table-card">

        {/* TABLE HEADER */}

        <div className="page-section-header">

          <div>
            <h3>
              Maintenance Records
            </h3>

            <p>
              Track reported problems and
              maintenance activities.
            </p>
          </div>

        </div>

        {/* =================================================
            FILTERS
        ================================================= */}

        <div className="filters">

          {/* SEARCH */}

          <div className="table-search">

            <input
              type="text"
              value={search}
              onChange={(event) =>
                setSearch(
                  event.target.value
                )
              }
              placeholder="Search computer, issue, technician..."
            />

            <Icon
              type="search"
              size={18}
            />

          </div>

          {/* STATUS */}

          <select
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(
                event.target.value
              )
            }
          >
            <option>
              All Status
            </option>

            <option>
              Pending
            </option>

            <option>
              In Progress
            </option>

            <option>
              Completed
            </option>

          </select>

          {/* PRIORITY */}

          <select
            value={priorityFilter}
            onChange={(event) =>
              setPriorityFilter(
                event.target.value
              )
            }
          >
            <option>
              All Priority
            </option>

            <option>
              Critical
            </option>

            <option>
              High
            </option>

            <option>
              Medium
            </option>

            <option>
              Low
            </option>

          </select>

          {/* COMPUTER */}

          <select
            value={computerFilter}
            onChange={(event) =>
              setComputerFilter(
                event.target.value
              )
            }
          >
            <option>
              All Computers
            </option>

            {computers.map(
              (computer) => (
                <option
                  key={computer}
                  value={computer}
                >
                  {computer}
                </option>
              )
            )}

          </select>

          {/* RESET */}

          <button
            className="refresh"
            onClick={resetFilters}
          >
            <Icon
              type="refresh"
              size={17}
            />

            Reset
          </button>

        </div>

        {/* =================================================
            RESULT COUNT
        ================================================= */}

        <div
          style={{
            padding:
              "0 20px 15px",
            fontSize: "12px",
            color: "#718099",
          }}
        >
          Showing{" "}
          <strong>
            {filteredRecords.length}
          </strong>{" "}
          maintenance records
        </div>

        {/* =================================================
            TABLE
        ================================================= */}

        {filteredRecords.length > 0 ? (

          <div className="table-scroll">

            <table>

              <thead>

                <tr>

                  <th>
                    Computer
                  </th>

                  <th>
                    Issue
                  </th>

                  <th>
                    Technician
                  </th>

                  <th>
                    Priority
                  </th>

                  <th>
                    Scheduled
                  </th>

                  <th>
                    Completed
                  </th>

                  <th>
                    Status
                  </th>

                </tr>

              </thead>

              <tbody>

                {filteredRecords.map(
                  (record) => (

                    <tr
                      key={record.id}
                    >

                      {/* COMPUTER */}

                      <td>

                        <strong>
                          {record.computer}
                        </strong>

                      </td>

                      {/* ISSUE */}

                      <td>

                        <div
                          style={{
                            display:
                              "flex",
                            alignItems:
                              "center",
                            gap: "9px",
                          }}
                        >

                          <div
                            className="maintenance-icon"
                          >

                            <Icon
                              type="maintenance"
                              size={17}
                            />

                          </div>

                          <strong>
                            {record.issue}
                          </strong>

                        </div>

                      </td>

                      {/* TECHNICIAN */}

                      <td>
                        {record.technician}
                      </td>

                      {/* PRIORITY */}

                      <td>

                        <span
                          className={
                            `maintenance-priority ${getPriorityClass(
                              record.priority
                            )}`
                          }
                        >
                          {record.priority}
                        </span>

                      </td>

                      {/* SCHEDULED */}

                      <td>
                        {record.scheduled}
                      </td>

                      {/* COMPLETED */}

                      <td>
                        {record.completed}
                      </td>

                      {/* STATUS */}

                      <td>

                        <span
                          className={
                            `maintenance-status ${getStatusClass(
                              record.status
                            )}`
                          }
                        >

                          <i />

                          {record.status}

                        </span>

                      </td>

                    </tr>

                  )
                )}

              </tbody>

            </table>

          </div>

        ) : (

          /* =================================================
             EMPTY STATE
          ================================================= */

          <div className="empty-state">

            <Icon
              type="maintenance"
              size={40}
            />

            <h3>
              No maintenance records found
            </h3>

            <p>
              No records match the
              selected filters.
            </p>

            <button
              className="modal-button"
              onClick={resetFilters}
            >
              Clear Filters
            </button>

          </div>

        )}

      </div>

    </div>
  );
}

export default MaintenanceRecords;