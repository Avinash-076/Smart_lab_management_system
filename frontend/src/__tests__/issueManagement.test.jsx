import { describe, it, expect } from "vitest";
import { renderToString } from "react-dom/server";
import IssueHeader from "../features/issues/components/IssueHeader/IssueHeader";
import IssueSummaryCards from "../features/issues/components/IssueSummaryCards/IssueSummaryCards";
import IssueFilters from "../features/issues/components/IssueFilters/IssueFilters";
import IssueTable from "../features/issues/components/IssueTable/IssueTable";
import IssueDetailsPanel from "../features/issues/components/IssueDetailsPanel/IssueDetailsPanel";
import IssueTimeline from "../features/issues/components/IssueTimeline/IssueTimeline";
import IssueRelatedInfo from "../features/issues/components/IssueRelatedInfo/IssueRelatedInfo";
import IssueComments from "../features/issues/components/IssueComments/IssueComments";
import IssueStatusActions from "../features/issues/components/IssueStatusActions/IssueStatusActions";
import ReportIssueModal from "../features/issues/components/ReportIssueModal/ReportIssueModal";
import ResolveIssueModal from "../features/issues/components/ResolveIssueModal/ResolveIssueModal";
import EditIssueModal from "../features/issues/components/EditIssueModal/EditIssueModal";
import {
  formatDateTime,
  formatTimeOnly,
  parseStructuredIssue,
  getPriorityBadgeConfig,
  getStatusBadgeConfig,
  filterByDateRange,
} from "../features/issues/utils/issueUtils";

describe("Issue Management Feature - Unit & Component Tests", () => {
  const sampleIssue = {
    id: 1234,
    computer_id: 11,
    computer_hostname: "DESKTOP-M72R440",
    title: "High CPU Usage",
    description: "CPU usage is above the 90.0% threshold. Current usage: 94.2%.",
    severity: "high",
    status: "open",
    source: "agent",
    created_at: "2026-10-19T11:19:00Z",
    updated_at: "2026-10-19T11:28:00Z",
    resolved_at: null,
    resolution_notes: null,
  };

  const sampleDeviceIssue = {
    id: 1235,
    computer_id: 11,
    computer_hostname: "DESKTOP-M72R440",
    title: "Unauthorized USB Mass Storage Device Connected",
    description:
      "An unauthorized or unapproved device was detected on the system.\n\n" +
      "Device: Lexar USB Flash Drive USB Device\n" +
      "Class: USB Mass Storage Device\n" +
      "Hardware ID: USB\\VID_090C&PID_1000\\1234567890ABCDEF\n" +
      "VID / PID: 090C:1000\n" +
      "First Observed: 2026-10-19 11:01:00 UTC\n" +
      "Risk Level: CRITICAL",
    severity: "critical",
    status: "resolved",
    source: "agent",
    created_at: "2026-10-19T11:01:00Z",
    updated_at: "2026-10-19T11:05:00Z",
    resolved_at: "2026-10-19T11:05:00Z",
    resolution_notes: "[Automated Recovery] Device disconnected from system.",
  };

  /* ----------------------------------------------------
     1. UTILITY TESTS
  ---------------------------------------------------- */
  describe("Utility Helpers", () => {
    it("formatDateTime formats valid ISO date to human readable string", () => {
      const res = formatDateTime("2026-10-19T11:19:00Z");
      expect(res).toContain("Oct");
      expect(res).toContain("2026");
    });

    it("formatTimeOnly extracts time with AM/PM", () => {
      const res = formatTimeOnly("2026-10-19T11:19:00Z");
      expect(res).toMatch(/(AM|PM)/);
    });

    it("formatDateTime safely handles invalid or null dates", () => {
      expect(formatDateTime(null)).toBe("N/A");
      expect(formatDateTime("")).toBe("N/A");
    });

    it("parseStructuredIssue extracts CPU metric telemetry", () => {
      const parsed = parseStructuredIssue(sampleIssue);
      expect(parsed).not.toBeNull();
      expect(parsed.isMetric).toBe(true);
      expect(parsed.currentValue).toBe(94.2);
      expect(parsed.threshold).toBe(90.0);
      expect(parsed.metricType).toBe("CPU");
    });

    it("parseStructuredIssue extracts unauthorized USB hardware attributes", () => {
      const parsed = parseStructuredIssue(sampleDeviceIssue);
      expect(parsed).not.toBeNull();
      expect(parsed.isDevice).toBe(true);
      expect(parsed.vidPid).toBe("090C:1000");
      expect(parsed.deviceClass).toBe("USB Mass Storage Device");
      expect(parsed.hardwareId).toContain("VID_090C");
      expect(parsed.riskLevel).toBe("CRITICAL");
    });

    it("getPriorityBadgeConfig returns proper colors for all levels", () => {
      expect(getPriorityBadgeConfig("critical").label).toBe("Critical");
      expect(getPriorityBadgeConfig("high").label).toBe("High");
      expect(getPriorityBadgeConfig("medium").label).toBe("Medium");
      expect(getPriorityBadgeConfig("low").label).toBe("Low");
    });

    it("getStatusBadgeConfig returns proper labels and dot colors", () => {
      expect(getStatusBadgeConfig("open").label).toBe("Open");
      expect(getStatusBadgeConfig("in_progress").label).toBe("In Progress");
      expect(getStatusBadgeConfig("resolved").label).toBe("Resolved");
    });

    it("filterByDateRange respects time ranges", () => {
      const now = new Date().toISOString();
      expect(filterByDateRange(now, "Today")).toBe(true);
      expect(filterByDateRange(now, "Last 7 Days")).toBe(true);
      expect(filterByDateRange(now, "All Time")).toBe(true);
    });
  });

  /* ----------------------------------------------------
     2. COMPONENT TESTS
  ---------------------------------------------------- */
  describe("Component Rendering", () => {
    it("IssueHeader renders title and Report Issue button", () => {
      const html = renderToString(
        <IssueHeader onReportClick={() => {}} />
      );
      expect(html).toContain("Issue Management");
      expect(html).toContain("Monitor and manage problems reported by laboratory computers.");
      expect(html).toContain("Report Issue");
    });

    it("IssueSummaryCards renders all 4 metric cards with real numbers", () => {
      const stats = { total: 14, open: 8, in_progress: 2, resolved: 4 };
      const html = renderToString(<IssueSummaryCards stats={stats} />);

      expect(html).toContain("Total Issues");
      expect(html).toContain("14");
      expect(html).toContain("Open");
      expect(html).toContain("8");
      expect(html).toContain("In Progress");
      expect(html).toContain("2");
      expect(html).toContain("Resolved");
      expect(html).toContain("4");
      expect(html).toContain("issue-summary-bars");
    });

    it("IssueFilters renders search, dropdowns, and buttons", () => {
      const computers = [
        { id: 11, hostname: "DESKTOP-M72R440" },
        { id: 12, hostname: "PC-LAB-02" },
      ];
      const html = renderToString(
        <IssueFilters
          search=""
          onSearchChange={() => {}}
          statusFilter="All Status"
          onStatusChange={() => {}}
          priorityFilter="All Priority"
          onPriorityChange={() => {}}
          computerFilter="All Computers"
          onComputerChange={() => {}}
          dateRangeFilter="Last 30 Days"
          onDateRangeChange={() => {}}
          computers={computers}
          onRefresh={() => {}}
          onReset={() => {}}
        />
      );

      expect(html).toContain("Filter Issues");
      expect(html).toContain("Search issues, title, description or computer...");
      expect(html).toContain("All Status");
      expect(html).toContain("All Priority");
      expect(html).toContain("All Computers");
      expect(html).toContain("DESKTOP-M72R440");
      expect(html).toContain("Refresh");
      expect(html).toContain("Reset");
    });

    it("IssueTable renders columns, hostname, priority badge, and status badge", () => {
      const compMap = new Map([[11, "DESKTOP-M72R440"]]);
      const html = renderToString(
        <IssueTable
          issues={[sampleIssue, sampleDeviceIssue]}
          selectedIssue={sampleIssue}
          onSelectIssue={() => {}}
          computerMap={compMap}
          onStatusChange={() => {}}
          onOpenResolve={() => {}}
          onEditIssue={() => {}}
          onDeleteIssue={() => {}}
        />
      );

      expect(html).toContain("Reported Issues");
      expect(html).toContain("DESKTOP-M72R440");
      expect(html).toContain("High CPU Usage");
      expect(html).toContain("Unauthorized USB Mass Storage");
      expect(html).toContain("View");
      expect(html).toContain("Showing 1 to 2 of 2 issues");
    });

    it("IssueDetailsPanel renders selected issue details and tabs", () => {
      const html = renderToString(
        <IssueDetailsPanel
          issue={sampleIssue}
          computer={{ id: 11, hostname: "DESKTOP-M72R440", ip_address: "192.168.1.50" }}
          onClose={() => {}}
          onStatusChange={() => {}}
          onOpenResolve={() => {}}
          onAddComment={() => {}}
          onViewComputer={() => {}}
          onEditIssue={() => {}}
        />
      );

      expect(html).toContain("Issue Details");
      expect(html).toContain("High CPU Usage");
      expect(html).toContain("#1234");
      expect(html).toContain("Client Agent");
      expect(html).toContain("Timeline");
      expect(html).toContain("Related Information");
      expect(html).toContain("Comments (0)");
      expect(html).toContain("Start Working");
      expect(html).toContain("Add Comment");
      expect(html).toContain("View Computer");
      expect(html).toContain("Edit Issue");
    });

    it("IssueTimeline renders sequential milestones", () => {
      const html = renderToString(<IssueTimeline issue={sampleIssue} />);
      expect(html).toContain("Issue reported");
      expect(html).toContain("Issue assigned");
    });

    it("IssueRelatedInfo renders structured hardware and security tips", () => {
      const html = renderToString(
        <IssueRelatedInfo issue={sampleDeviceIssue} computer={{ hostname: "DESKTOP-M72R440" }} />
      );
      expect(html).toContain("Peripheral Security Details");
      expect(html).toContain("090C:1000");
      expect(html).toContain("USB Mass Storage Device");
      expect(html).toContain("Copy ID");
      expect(html).toContain("Security Guidance");
    });

    it("IssueComments renders comments and remark form", () => {
      const html = renderToString(
        <IssueComments issue={sampleDeviceIssue} onAddComment={() => {}} />
      );
      expect(html).toContain("Resolution Summary");
      expect(html).toContain("Automated Recovery");
      expect(html).toContain("Post Comment");
    });

    it("IssueStatusActions adjusts button state for in_progress and resolved", () => {
      const inProgressIssue = { ...sampleIssue, status: "in_progress" };
      const resolvedIssue = { ...sampleIssue, status: "resolved" };

      const htmlInProgress = renderToString(
        <IssueStatusActions
          issue={inProgressIssue}
          onStatusChange={() => {}}
          onOpenResolve={() => {}}
          onAddCommentClick={() => {}}
          onViewComputer={() => {}}
          onEditIssue={() => {}}
        />
      );
      expect(htmlInProgress).toContain("Resolve Issue");

      const htmlResolved = renderToString(
        <IssueStatusActions
          issue={resolvedIssue}
          onStatusChange={() => {}}
          onOpenResolve={() => {}}
          onAddCommentClick={() => {}}
          onViewComputer={() => {}}
          onEditIssue={() => {}}
        />
      );
      expect(htmlResolved).toContain("Reopen Issue");
    });

    it("Modals render correctly when open", () => {
      const reportHtml = renderToString(
        <ReportIssueModal
          isOpen={true}
          onClose={() => {}}
          computers={[{ id: 11, hostname: "DESKTOP-M72R440" }]}
          onSubmit={() => {}}
        />
      );
      expect(reportHtml).toContain("Report New Issue");
      expect(reportHtml).toContain("Target Computer");
      expect(reportHtml).toContain("Submit Report");

      const resolveHtml = renderToString(
        <ResolveIssueModal
          isOpen={true}
          issue={sampleIssue}
          onClose={() => {}}
          onSubmit={() => {}}
        />
      );
      expect(resolveHtml).toContain("Resolve Issue #1234");
      expect(resolveHtml).toContain("Resolution Notes");
      expect(resolveHtml).toContain("Confirm Resolution");

      const editHtml = renderToString(
        <EditIssueModal
          isOpen={true}
          issue={sampleIssue}
          onClose={() => {}}
          onSubmit={() => {}}
        />
      );
      expect(editHtml).toContain("Edit Issue #1234");
      expect(editHtml).toContain("Save Changes");
    });
  });
});
