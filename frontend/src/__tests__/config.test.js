import { describe, it, expect } from "vitest";
import {
  normalizeApiUrl,
  normalizeWsUrl,
  buildApiUrl,
} from "../services/config";

describe("Configuration Service", () => {
  describe("API Base URL Normalization", () => {
    it("handles standard local development URL", () => {
      expect(normalizeApiUrl("http://127.0.0.1:8000/api")).toBe(
        "http://127.0.0.1:8000/api"
      );
    });

    it("appends /api when missing from base URL", () => {
      expect(normalizeApiUrl("http://127.0.0.1:8000")).toBe(
        "http://127.0.0.1:8000/api"
      );
      expect(normalizeApiUrl("http://localhost:8000/")).toBe(
        "http://localhost:8000/api"
      );
    });

    it("normalizes trailing slashes without duplicating /api", () => {
      expect(normalizeApiUrl("http://127.0.0.1:8000/api/")).toBe(
        "http://127.0.0.1:8000/api"
      );
      expect(normalizeApiUrl("https://slms.example.com/api///")).toBe(
        "https://slms.example.com/api"
      );
    });

    it("handles LAN and production host URLs", () => {
      expect(normalizeApiUrl("http://192.168.1.100:8000")).toBe(
        "http://192.168.1.100:8000/api"
      );
      expect(normalizeApiUrl("https://api.slms.org")).toBe(
        "https://api.slms.org/api"
      );
      expect(normalizeApiUrl("https://api.slms.org/custom/prefix")).toBe(
        "https://api.slms.org/custom/prefix/api"
      );
    });

    it("throws a descriptive error on invalid protocol or malformed URL", () => {
      expect(() => normalizeApiUrl("ftp://127.0.0.1:8000")).toThrow(
        /Invalid API protocol/
      );
      expect(() => normalizeApiUrl("not-a-valid-url")).toThrow(
        /Invalid API base URL/
      );
      expect(() => normalizeApiUrl("")).toThrow(/Invalid API base URL/);
      expect(() => normalizeApiUrl(null)).toThrow(/Invalid API base URL/);
    });
  });

  describe("WebSocket Base URL Normalization", () => {
    const apiBase = "http://127.0.0.1:8000/api";

    it("normalizes explicitly configured ws URL", () => {
      expect(
        normalizeWsUrl("ws://127.0.0.1:8000/ws/dashboard", apiBase)
      ).toBe("ws://127.0.0.1:8000/ws/dashboard");

      expect(normalizeWsUrl("ws://127.0.0.1:8000", apiBase)).toBe(
        "ws://127.0.0.1:8000/ws/dashboard"
      );

      expect(normalizeWsUrl("ws://127.0.0.1:8000/", apiBase)).toBe(
        "ws://127.0.0.1:8000/ws/dashboard"
      );
    });

    it("normalizes secure wss URL for production", () => {
      expect(
        normalizeWsUrl("wss://slms.example.com/ws/dashboard", apiBase)
      ).toBe("wss://slms.example.com/ws/dashboard");
    });

    it("safely derives ws URL from API base URL when not provided", () => {
      expect(normalizeWsUrl("", "http://127.0.0.1:8000/api")).toBe(
        "ws://127.0.0.1:8000/ws/dashboard"
      );

      expect(normalizeWsUrl(null, "http://192.168.1.50:8000/api")).toBe(
        "ws://192.168.1.50:8000/ws/dashboard"
      );

      expect(normalizeWsUrl(undefined, "https://slms.org/api")).toBe(
        "wss://slms.org/ws/dashboard"
      );
    });

    it("throws on invalid WebSocket protocol", () => {
      expect(() =>
        normalizeWsUrl("http://127.0.0.1:8000/ws", apiBase)
      ).toThrow(/Invalid WebSocket protocol/);

      expect(() =>
        normalizeWsUrl("invalid-ws", apiBase)
      ).toThrow(/Invalid WebSocket base URL/);
    });
  });

  describe("buildApiUrl", () => {
    it("safely constructs endpoint URL without duplicating /api", () => {
      expect(buildApiUrl("/clients")).toContain("/api/clients");
      expect(buildApiUrl("clients")).toContain("/api/clients");
      expect(buildApiUrl("/api/clients")).toContain("/api/clients");
      expect(buildApiUrl("/api/reports/export")).toContain(
        "/api/reports/export"
      );
      expect(buildApiUrl("api/reports/export")).toContain(
        "/api/reports/export"
      );
    });

    it("returns full external URLs as-is", () => {
      expect(buildApiUrl("https://external.com/api/test")).toBe(
        "https://external.com/api/test"
      );
      expect(buildApiUrl("http://external.com/api/test")).toBe(
        "http://external.com/api/test"
      );
    });
  });
});
