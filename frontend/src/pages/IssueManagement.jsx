import { useMemo, useState } from "react";

import StatCard from "../components/StatCard";
import Icon from "../components/Icon";

/* =====================================================
   ISSUE DATA
===================================================== */

const issueData = [
  {
    id: 1,
    computer: "PC-05",
    issue: "High CPU Usage",
    description: "CPU usage remained above 90% for several minutes.",
    priority: "High",
    status: "Open",
    reported: "21 Sep 2026, 09:15 AM",
  },
  {
    id: 2,
    computer: "PC-07",
    issue: "Computer Offline",
    description: "Client agent has not sent a heartbeat.",
    priority: "Critical",
    status: "Open",
    reported: "21 Sep 2026, 09:42 AM",
  },
  {
    id: 3,
    computer: "PC-12",
    issue: "Low Disk Space",
    description: "Available disk space is below the configured threshold.",
    priority: "High",
    status: "In Progress",
    reported: "20 Sep 2026, 02:30 PM",
  },
  {
    id: 4,
    computer: "PC-16",
    issue: "Computer Offline",
    description: "Client agent is currently unreachable.",
    priority: "Critical",
    status: "Open",
    reported: "20 Sep 2026, 04:10 PM",
  },
  {
    id: 5,
    computer: "PC-20",
    issue: "High Memory Usage",
    description: "RAM usage exceeded the configured threshold.",
    priority: "Medium",
    status: "In Progress",
    reported: "19 Sep 2026, 11:20 AM",
  },
  {
    id: 6,
    computer: "PC-24",
    issue: "Outdated Software",
    description: "One or more installed applications require an update.",
    priority: "Low",
    status: "Resolved",
    reported: "18 Sep 2026, 01:45 PM",
  },
  {
    id: 7,
    computer: "PC-03",
    issue: "High CPU Usage",
    description: "CPU usage exceeded 85% during lab operation.",
    priority: "Medium",
    status: "Resolved",
    reported: "17 Sep 2026, 10:30 AM",
  },
  {
    id: 8,
    computer: "PC-09",
    issue: "Low Disk Space",
    description: "Disk usage has crossed the warning threshold.",
    priority: "High",
    status: "Open",
    reported: "16 Sep 2026, 03:25 PM",
  },
];

/* =====================================================
   COMPONENT
===================================================== */

function IssueManagement() {
  const [search, setSearch] =
    useState("");

  const [statusFilter, setStatusFilter] =
    useState("All Status");

  const [priorityFilter, setPriorityFilter] =
    useState("All Priority");

  const [computerFilter, setComputerFilter] =
    useState("All Computers");

  /* =====================================================
     COMPUTERS
  ===================================================== */

  const computers = [
    ...new Set(
      issueData.map(
        (issue) => issue.computer
      )
    ),
  ];

  /* =====================================================
     FILTER ISSUES
  ===================================================== */

  const filteredIssues = useMemo(() => {
    const searchText =
      search.toLowerCase().trim();

    return issueData.filter((issue) => {
      const matchesSearch =
        !searchText ||
        issue.computer
          .toLowerCase()
          .includes(searchText) ||
        issue.issue
          .toLowerCase()
          .includes(searchText) ||
        issue.description
          .toLowerCase()
          .includes(searchText);

      const matchesStatus =
        statusFilter === "All Status" ||
        issue.status === statusFilter;

      const matchesPriority =
        priorityFilter === "All Priority" ||
        issue.priority === priorityFilter;

      const matchesComputer =
        computerFilter === "All Computers" ||
        issue.computer === computerFilter;

      return (
        matchesSearch &&
        matchesStatus &&
        matchesPriority &&
        matchesComputer
      );
    });
  }, [
    search,
    statusFilter,
    priorityFilter,
    computerFilter,
  ]);

  /* =====================================================
     STATISTICS
  ===================================================== */

  const totalIssues =
    issueData.length;

  const openIssues =
    issueData.filter(
      (issue) =>
        issue.status === "Open"
    ).length;

  const inProgressIssues =
    issueData.filter(
      (issue) =>
        issue.status === "In Progress"
    ).length;

  const resolvedIssues =
    issueData.filter(
      (issue) =>
        issue.status === "Resolved"
    ).length;

  /* =====================================================
     RESET
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
      return "issue-critical";
    }

    if (priority === "High") {
      return "issue-high";
    }

    if (priority === "Medium") {
      return "issue-medium";
    }

    return "issue-low";
  };

  /* =====================================================
     STATUS CLASS
  ===================================================== */

  const getStatusClass = (issueStatus) => {
    if (issueStatus === "Resolved") {
      return "issue-status-resolved";
    }

    if (issueStatus === "In Progress") {
      return "issue-status-progress";
    }

    return "issue-status-open";
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
            Issue Management
          </h2>

          <p>
            Monitor and manage problems
            reported by laboratory computers.
          </p>
        </div>

      </div>

      {/* =================================================
          STAT CARDS
      ================================================= */}

      <div className="cards">

        <StatCard
          icon="issue"
          title="Total Issues"
          number={totalIssues}
          footer="All reported issues"
          type="blue"
        />

        <StatCard
          icon="issue"
          title="Open"
          number={openIssues}
          footer="Issues requiring attention"
          type="orange"
        />

        <StatCard
          icon="maintenance"
          title="In Progress"
          number={inProgressIssues}
          footer="Currently being handled"
          type="purple"
        />

        <StatCard
          icon="check"
          title="Resolved"
          number={resolvedIssues}
          footer="Successfully resolved"
          type="green"
        />

      </div>

      {/* =================================================
          ISSUE TABLE
      ================================================= */}

      <div className="table-card">

        {/* TABLE HEADER */}

        <div className="page-section-header">

          <div>
            <h3>
              Reported Issues
            </h3>

            <p>
              Problems reported by client
              agents are displayed here.
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
              placeholder="Search issues or computers..."
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
              Open
            </option>

            <option>
              In Progress
            </option>

            <option>
              Resolved
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
            {filteredIssues.length}
          </strong>{" "}
          issue records
        </div>

        {/* =================================================
            TABLE
        ================================================= */}

        {filteredIssues.length > 0 ? (

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
                    Description
                  </th>

                  <th>
                    Priority
                  </th>

                  <th>
                    Reported
                  </th>

                  <th>
                    Status
                  </th>

                </tr>

              </thead>

              <tbody>

                {filteredIssues.map(
                  (issue) => (

                    <tr
                      key={issue.id}
                    >

                      {/* COMPUTER */}

                      <td>

                        <strong>
                          {issue.computer}
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
                            className="issue-icon"
                          >
                            <Icon
                              type="issue"
                              size={17}
                            />
                          </div>

                          <strong>
                            {issue.issue}
                          </strong>

                        </div>

                      </td>

                      {/* DESCRIPTION */}

                      <td>

                        <span
                          className="issue-description"
                        >
                          {issue.description}
                        </span>

                      </td>

                      {/* PRIORITY */}

                      <td>

                        <span
                          className={
                            `issue-priority ${getPriorityClass(
                              issue.priority
                            )}`
                          }
                        >
                          {issue.priority}
                        </span>

                      </td>

                      {/* REPORTED */}

                      <td>
                        {issue.reported}
                      </td>

                      {/* STATUS */}

                      <td>

                        <span
                          className={
                            `issue-status ${getStatusClass(
                              issue.status
                            )}`
                          }
                        >

                          <i />

                          {issue.status}

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
              type="issue"
              size={40}
            />

            <h3>
              No issues found
            </h3>

            <p>
              No issues match the
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

export default IssueManagement;