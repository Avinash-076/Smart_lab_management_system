import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderToString } from "react-dom/server";
import LiveResourceHeader from "../features/computers/components/LiveResourceHeader";
import MatrixChartsGrid from "../features/computers/components/MatrixChartsGrid";
import ResourceDetailsRow from "../features/computers/components/ResourceDetailsRow";
import TopProcessesRow from "../features/computers/components/TopProcessesRow";
import { getComputerMetricSummary } from "../services/computerService";
import { getComputerProcessRankings } from "../services/processService";
import { setTokens } from "../services/api";

function createFakeJwt(payload) {
  const header = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.sig`;
}

describe("Matrix Tab Component & Service Tests", () => {
  let originalFetch;
  let mockStorage = {};
  let lastFetchCall = null;

  beforeEach(() => {
    mockStorage = {};
    lastFetchCall = null;
    vi.stubGlobal("localStorage", {
      getItem: (key) => mockStorage[key] || null,
      setItem: (key, val) => {
        mockStorage[key] = String(val);
      },
      removeItem: (key) => {
        delete mockStorage[key];
      },
      clear: () => {
        mockStorage = {};
      },
    });

    originalFetch = globalThis.fetch;
    const nowSec = Math.floor(Date.now() / 1000);
    const validToken = createFakeJwt({ exp: nowSec + 3600, sub: "1" });
    setTokens(validToken, validToken);

    globalThis.fetch = vi.fn(async (url, options = {}) => {
      lastFetchCall = { url: String(url), options };
      return {
        ok: true,
        status: 200,
        headers: new Headers({ "content-type": "application/json" }),
        json: async () => ({ success: true, url: String(url) }),
      };
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllGlobals();
  });

  const sampleSummary = {
    computer_id: 8,
    sample_count: 10,
    time_series: [
      {
        timestamp: "2026-10-14T06:00:00Z",
        cpu_usage: 25.0,
        ram_usage: 48.0,
        disk_usage: 62.0,
        download_mbps: 12.4,
        upload_mbps: 3.6,
      },
      {
        timestamp: "2026-10-14T06:10:00Z",
        cpu_usage: 30.0,
        ram_usage: 50.0,
        disk_usage: 62.0,
        download_mbps: 15.0,
        upload_mbps: 4.2,
      },
    ],
    cpu: { current: 30.0, average: 27.5, max: 30.0, min: 25.0 },
    memory: { current: 50.0, average: 49.0, max: 50.0, min: 48.0 },
    disk: { current: 62.0, average: 62.0, max: 62.0, min: 62.0 },
    network: {
      current_download_mbps: 15.0,
      current_upload_mbps: 4.2,
      average_download_mbps: 13.7,
      average_upload_mbps: 3.9,
      max_download_mbps: 15.0,
      min_download_mbps: 12.4,
      max_upload_mbps: 4.2,
      min_upload_mbps: 3.6,
    },
    disk_partitions: [
      {
        name: "C: (System)",
        total_gb: 512,
        used_gb: 317,
        free_gb: 195,
        percent: 62,
      },
      {
        name: "D: (Data)",
        total_gb: 500,
        used_gb: 142,
        free_gb: 358,
        percent: 28,
      },
    ],
    memory_details: {
      total_gb: 16.0,
      in_use_gb: 7.7,
      available_gb: 8.3,
      in_use_percent: 48.0,
    },
    network_details: {
      download_mbps: 12.4,
      upload_mbps: 3.6,
      total_sent_gb: 1.2,
      total_received_gb: 4.8,
    },
  };

  const sampleRankings = {
    top_cpu: [
      { name: "chrome.exe", cpu_percent: 12.4, memory_mb: 412.0, username: "LabUser" },
      { name: "code.exe", cpu_percent: 6.7, memory_mb: 356.0, username: "LabUser" },
    ],
    top_memory: [
      { name: "chrome.exe", cpu_percent: 12.4, memory_mb: 412.0, username: "LabUser" },
      { name: "code.exe", cpu_percent: 6.7, memory_mb: 356.0, username: "LabUser" },
    ],
    network_attribution: {
      supported: false,
      message: "Windows user-mode agents cannot reliably attribute individual socket I/O",
    },
  };

  it("renders LiveResourceHeader with preset buttons", () => {
    const html = renderToString(
      <LiveResourceHeader
        activeRange="1h"
        onSelectRange={() => {}}
        customDates={{ start: "", end: "" }}
        onCustomDateChange={() => {}}
        onApplyCustomRange={() => {}}
      />
    );

    expect(html).toContain("Live Resource Usage");
    expect(html).toContain("Live");
    expect(html).toContain("1 Hour");
    expect(html).toContain("6 Hours");
    expect(html).toContain("24 Hours");
    expect(html).toContain("Custom Range");
    expect(html).toContain("time-filter-btn active");
  });

  it("renders MatrixChartsGrid with 4 metrics and stats", () => {
    const html = renderToString(
      <MatrixChartsGrid summary={sampleSummary} activeRange="1h" />
    );

    expect(html).toContain("CPU Usage (%)");
    expect(html).toContain("Memory Usage (%)");
    expect(html).toContain("Disk Usage (%)");
    expect(html).toContain("Network Usage (Mbps)");
    // Stats
    expect(html).toContain("30%"); // CPU current
    expect(html).toContain("50%"); // RAM current
    expect(html).toContain("62%"); // Disk current
    expect(html).toContain("15 Mbps"); // Down
    expect(html).toContain("4.2 Mbps"); // Up
  });

  it("renders MatrixChartsGrid with empty state gracefully", () => {
    const html = renderToString(
      <MatrixChartsGrid summary={null} activeRange="1h" />
    );

    expect(html).toContain("CPU Usage (%)");
    expect(html).toContain("No metrics recorded in this window");
    expect(html).toContain("—");
  });

  it("renders ResourceDetailsRow with partition bars, memory breakdown, and network totals", () => {
    const html = renderToString(
      <ResourceDetailsRow
        diskPartitions={sampleSummary.disk_partitions}
        memoryDetails={sampleSummary.memory_details}
        networkDetails={sampleSummary.network_details}
      />
    );

    expect(html).toContain("Disk Space Usage");
    expect(html).toContain("C: (System)");
    expect(html).toContain("used of");
    expect(html).toContain("317");
    expect(html).toContain("512");
    expect(html).toContain("D: (Data)");
    expect(html).toContain("Memory Details");
    expect(html).toContain("7.7 GB (48%)");
    expect(html).toContain("8.3 GB (52%)");
    expect(html).toContain("16 GB");
    expect(html).toContain("Network Details");
    expect(html).toContain("12.4 Mbps");
    expect(html).toContain("3.6 Mbps");
    expect(html).toContain("1.2 GB");
    expect(html).toContain("4.8 GB");
  });

  it("renders TopProcessesRow with CPU, memory, and network attribution notice", () => {
    const html = renderToString(
      <TopProcessesRow rankings={sampleRankings} onViewAll={() => {}} />
    );

    expect(html).toContain("Top CPU Usage Processes");
    expect(html).toContain("Memory Usage by Process");
    expect(html).toContain("Network Usage by Process");
    expect(html).toContain("chrome.exe");
    expect(html).toContain("code.exe");
    expect(html).toContain("12.4%");
    expect(html).toContain("412 MB");
    expect(html).toContain("Per-Process Network Attribution");
  });

  it("calls getComputerMetricSummary with correct range params", async () => {
    await getComputerMetricSummary(8, { range_preset: "6h" });
    expect(lastFetchCall).toBeTruthy();
    expect(lastFetchCall.url).toContain("/api/metrics/8/summary?range_preset=6h");
  });

  it("calls getComputerProcessRankings with computer ID and limit", async () => {
    await getComputerProcessRankings(8, 5);
    expect(lastFetchCall).toBeTruthy();
    expect(lastFetchCall.url).toContain("/api/clients/8/processes/rankings?limit=5");
  });
});
