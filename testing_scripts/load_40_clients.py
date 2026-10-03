#!/usr/bin/env python3
"""
SLMS 40-Client Load Simulator (J-11, J-12 / Stage 7).

Headless, high-concurrency simulator that stress-tests the SLMS backend
with up to 40+ concurrent clients over real HTTP and WebSocket connections.

Features:
- Completely headless (no GUI dependencies)
- Isolated simulated client identities (unique MAC, IP, hostname)
- Real HTTP registration & JWT authentication
- Real persistent WebSocket connections with heartbeat pings
- Real periodic telemetry ingestion (metrics)
- Simulated network drop and reconnect
- Real-time performance & latency metrics collection (p50, p95, p99)
- Detection and reporting of SQLite lock/busy contention and server errors

Usage:
  python testing_scripts/load_40_clients.py --clients 40 --duration 30 --url http://127.0.0.1:8000
"""

import argparse
import asyncio
import json
import logging
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Any

try:
    import httpx
    import websockets
except ImportError:
    print("Error: load_40_clients requires httpx and websockets.")
    print("Install with: uv pip install httpx websockets")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("LoadSimulator")


@dataclass
class SimulatorMetrics:
    start_time: float = 0.0
    end_time: float = 0.0
    target_clients: int = 40
    enroll_attempts: int = 0
    enroll_success: int = 0
    enroll_failures: int = 0
    auth_attempts: int = 0
    auth_success: int = 0
    auth_failures: int = 0
    ws_connections_attempted: int = 0
    ws_connections_established: int = 0
    ws_connections_failed: int = 0
    ws_pings_sent: int = 0
    telemetry_uploads_attempted: int = 0
    telemetry_uploads_succeeded: int = 0
    telemetry_uploads_failed: int = 0
    reconnect_attempts: int = 0
    reconnect_success: int = 0
    reconnect_failures: int = 0
    http_latencies_ms: list[float] = field(default_factory=list)
    ws_ping_latencies_ms: list[float] = field(default_factory=list)
    server_errors: list[str] = field(default_factory=list)
    sqlite_lock_errors: int = 0

    def record_error(self, err_msg: str):
        self.server_errors.append(err_msg)
        if "database is locked" in err_msg.lower() or "sqlite_busy" in err_msg.lower():
            self.sqlite_lock_errors += 1

    def print_summary(self):
        duration = self.end_time - self.start_time if self.end_time else 0.0
        print("\n" + "=" * 70)
        print("          SLMS 40-CLIENT SIMULATOR MEASURED RESULTS")
        print("=" * 70)
        print(f"Total Simulation Duration:      {duration:.2f} s")
        print(f"Target Concurrent Clients:      {self.target_clients}")
        print("-" * 70)
        print(f"Enrollments (Attempt/Success):  {self.enroll_attempts} / {self.enroll_success} "
              f"({(self.enroll_success / max(1, self.enroll_attempts))*100:.1f}%)")
        print(f"Authentications (Att/Success):  {self.auth_attempts} / {self.auth_success} "
              f"({(self.auth_success / max(1, self.auth_attempts))*100:.1f}%)")
        print(f"WebSockets Connected:           {self.ws_connections_established} / {self.ws_connections_attempted} "
              f"({(self.ws_connections_established / max(1, self.ws_connections_attempted))*100:.1f}%)")
        print(f"Telemetry Uploads:              {self.telemetry_uploads_succeeded} / {self.telemetry_uploads_attempted} "
              f"({(self.telemetry_uploads_succeeded / max(1, self.telemetry_uploads_attempted))*100:.1f}%)")
        if self.reconnect_attempts > 0:
            print(f"Simulated Reconnects:           {self.reconnect_success} / {self.reconnect_attempts} "
                  f"({(self.reconnect_success / max(1, self.reconnect_attempts))*100:.1f}%)")
        print("-" * 70)

        # Latency statistics
        if self.http_latencies_ms:
            sorted_http = sorted(self.http_latencies_ms)
            p50 = sorted_http[int(len(sorted_http) * 0.50)]
            p95 = sorted_http[int(len(sorted_http) * 0.95)]
            p99 = sorted_http[int(len(sorted_http) * 0.99)]
            avg_http = statistics.mean(self.http_latencies_ms)
            print(f"HTTP Latency (ms):              Avg: {avg_http:.1f} | p50: {p50:.1f} | p95: {p95:.1f} | p99: {p99:.1f}")
        else:
            print("HTTP Latency (ms):              No HTTP samples recorded")

        if self.ws_ping_latencies_ms:
            sorted_ws = sorted(self.ws_ping_latencies_ms)
            p50_ws = sorted_ws[int(len(sorted_ws) * 0.50)]
            p95_ws = sorted_ws[int(len(sorted_ws) * 0.95)]
            avg_ws = statistics.mean(self.ws_ping_latencies_ms)
            print(f"WebSocket Ping Latency (ms):    Avg: {avg_ws:.1f} | p50: {p50_ws:.1f} | p95: {p95_ws:.1f}")
        else:
            print("WebSocket Ping Latency (ms):    No WS ping samples recorded")

        print("-" * 70)
        print(f"Total Server / HTTP Errors:     {len(self.server_errors)}")
        print(f"SQLite Lock/Busy Contention:    {self.sqlite_lock_errors}")
        if self.server_errors:
            print("\nSample Errors:")
            for e in self.server_errors[:5]:
                print(f"  - {e}")
        print("=" * 70 + "\n")


class SimulatedClient:
    """Represents an independent workstation running the SLMS agent."""

    def __init__(
        self,
        client_index: int,
        base_url: str,
        enrollment_key: str,
        metrics: SimulatorMetrics,
        telemetry_interval: float,
        duration: float,
        test_reconnect: bool,
    ):
        self.index = client_index
        self.base_url = base_url.rstrip("/")
        self.ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.enrollment_key = enrollment_key
        self.metrics = metrics
        self.interval = telemetry_interval
        self.duration = duration
        self.test_reconnect = test_reconnect

        # Unique identity
        self.hostname = f"SIM-WORKSTATION-{self.index:03d}"
        self.ip_address = f"10.10.{(self.index // 250) + 1}.{(self.index % 250) + 1}"
        self.mac_address = f"02:00:00:{self.index // 65536:02x}:{(self.index // 256) % 256:02x}:{self.index % 256:02x}"

        self.agent_id: str | None = None
        self.client_secret: str | None = None
        self.computer_id: int | None = None
        self.access_token: str | None = None

    async def run(self, http_client: httpx.AsyncClient):
        """Execute full client lifecycle: enroll -> auth -> ws connect -> telemetry -> teardown."""
        try:
            # 1. Enroll
            enrolled = await self._enroll(http_client)
            if not enrolled:
                return

            # 2. Authenticate
            authed = await self._authenticate(http_client)
            if not authed:
                return

            # 3. Start Telemetry Loop and WebSocket Loop concurrently
            await asyncio.gather(
                self._run_websocket_session(),
                self._run_telemetry_loop(http_client),
                return_exceptions=True,
            )

        except Exception as e:
            self.metrics.record_error(f"Client {self.index} fatal: {e}")

    async def _enroll(self, http_client: httpx.AsyncClient) -> bool:
        self.metrics.enroll_attempts += 1
        payload = {
            "enrollment_key": self.enrollment_key,
            "device": {
                "hostname": self.hostname,
                "ip_address": self.ip_address,
                "mac_address": self.mac_address,
                "os_name": "Windows",
                "os_version": "11 Pro",
            },
        }
        t0 = time.perf_counter()
        try:
            resp = await http_client.post(f"{self.base_url}/api/agent/register", json=payload, timeout=10.0)
            elapsed = (time.perf_counter() - t0) * 1000.0
            self.metrics.http_latencies_ms.append(elapsed)

            if resp.status_code == 201:
                data = resp.json()
                self.agent_id = data["agent_id"]
                self.client_secret = data["client_secret"]
                self.computer_id = data["computer_id"]
                self.metrics.enroll_success += 1
                return True
            else:
                self.metrics.enroll_failures += 1
                self.metrics.record_error(f"Client {self.index} enroll {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            self.metrics.enroll_failures += 1
            self.metrics.record_error(f"Client {self.index} enroll exception: {e}")
            return False

    async def _authenticate(self, http_client: httpx.AsyncClient) -> bool:
        self.metrics.auth_attempts += 1
        payload = {
            "agent_id": self.agent_id,
            "client_secret": self.client_secret,
        }
        t0 = time.perf_counter()
        try:
            resp = await http_client.post(f"{self.base_url}/api/agent/auth", json=payload, timeout=10.0)
            elapsed = (time.perf_counter() - t0) * 1000.0
            self.metrics.http_latencies_ms.append(elapsed)

            if resp.status_code == 200:
                data = resp.json()
                self.access_token = data["access_token"]
                self.metrics.auth_success += 1
                return True
            else:
                self.metrics.auth_failures += 1
                self.metrics.record_error(f"Client {self.index} auth {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            self.metrics.auth_failures += 1
            self.metrics.record_error(f"Client {self.index} auth exception: {e}")
            return False

    async def _run_telemetry_loop(self, http_client: httpx.AsyncClient):
        """Periodically upload metrics to /api/metrics."""
        deadline = time.monotonic() + self.duration
        while time.monotonic() < deadline:
            await asyncio.sleep(self.interval)
            if not self.access_token:
                continue

            self.metrics.telemetry_uploads_attempted += 1
            metric_payload = {
                "cpu_usage": 10.0 + (self.index % 50),
                "ram_usage": 30.0 + (self.index % 40),
                "disk_usage": 55.0,
                "network_sent": 1024 * (self.index + 1),
                "network_received": 2048 * (self.index + 1),
            }
            headers = {"Authorization": f"Bearer {self.access_token}"}
            t0 = time.perf_counter()
            try:
                resp = await http_client.post(
                    f"{self.base_url}/api/metrics",
                    json=metric_payload,
                    headers=headers,
                    timeout=10.0,
                )
                elapsed = (time.perf_counter() - t0) * 1000.0
                self.metrics.http_latencies_ms.append(elapsed)

                if resp.status_code in (200, 201):
                    self.metrics.telemetry_uploads_succeeded += 1
                else:
                    self.metrics.telemetry_uploads_failed += 1
                    self.metrics.record_error(f"Client {self.index} telemetry {resp.status_code}: {resp.text}")
            except Exception as e:
                self.metrics.telemetry_uploads_failed += 1
                self.metrics.record_error(f"Client {self.index} telemetry error: {e}")

    async def _run_websocket_session(self):
        """Maintain persistent WebSocket connection with heartbeat pings and reconnect."""
        if not self.computer_id or not self.access_token:
            return

        ws_endpoint = f"{self.ws_url}/ws/client/{self.computer_id}"
        extra_headers = {"Authorization": f"Bearer {self.access_token}"}

        # First connection phase
        self.metrics.ws_connections_attempted += 1
        t_mid = self.duration / 2.0 if self.test_reconnect else self.duration

        try:
            async with websockets.connect(ws_endpoint, additional_headers=extra_headers) as ws:
                self.metrics.ws_connections_established += 1
                await self._ws_heartbeat_loop(ws, duration=t_mid)
        except Exception as e:
            self.metrics.ws_connections_failed += 1
            self.metrics.record_error(f"Client {self.index} WS error: {e}")

        # Reconnect phase if enabled
        if self.test_reconnect and self.duration > 5.0:
            await asyncio.sleep(1.0)
            self.metrics.reconnect_attempts += 1
            try:
                async with websockets.connect(ws_endpoint, additional_headers=extra_headers) as ws:
                    self.metrics.reconnect_success += 1
                    remaining = max(1.0, self.duration - t_mid - 1.0)
                    await self._ws_heartbeat_loop(ws, duration=remaining)
            except Exception as e:
                self.metrics.reconnect_failures += 1
                self.metrics.record_error(f"Client {self.index} reconnect error: {e}")

    async def _ws_heartbeat_loop(self, ws, duration: float):
        """Send periodic pings on the WebSocket."""
        stop_time = time.monotonic() + duration
        while time.monotonic() < stop_time:
            t0 = time.perf_counter()
            await ws.send("ping")
            self.metrics.ws_pings_sent += 1
            elapsed = (time.perf_counter() - t0) * 1000.0
            self.metrics.ws_ping_latencies_ms.append(elapsed)
            await asyncio.sleep(min(3.0, max(0.5, stop_time - time.monotonic())))


async def run_simulation(
    base_url: str,
    client_count: int,
    enrollment_key: str,
    telemetry_interval: float,
    duration: float,
    test_reconnect: bool,
) -> SimulatorMetrics:
    """Run all simulated client agents concurrently."""
    metrics = SimulatorMetrics(target_clients=client_count, start_time=time.time())
    logger.info(f"Starting simulation of {client_count} concurrent clients against {base_url} for {duration}s...")

    limits = httpx.Limits(max_keepalive_connections=client_count + 10, max_connections=client_count * 2)
    async with httpx.AsyncClient(limits=limits) as http_client:
        clients = [
            SimulatedClient(
                client_index=i,
                base_url=base_url,
                enrollment_key=enrollment_key,
                metrics=metrics,
                telemetry_interval=telemetry_interval,
                duration=duration,
                test_reconnect=test_reconnect,
            )
            for i in range(client_count)
        ]

        # Stagger client startup slightly (10-20ms) to simulate real-world boot spread
        tasks = []
        for i, c in enumerate(clients):
            await asyncio.sleep(0.015)
            tasks.append(asyncio.create_task(c.run(http_client)))

        await asyncio.gather(*tasks, return_exceptions=True)

    metrics.end_time = time.time()
    return metrics


def main():
    parser = argparse.ArgumentParser(description="SLMS 40-Client Load Simulator")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Backend base URL")
    parser.add_argument("--clients", type=int, default=40, help="Number of simulated clients")
    parser.add_argument("--key", default="SLMS-LOAD-TEST-KEY-0001", help="Pre-seeded enrollment key")
    parser.add_argument("--interval", type=float, default=5.0, help="Telemetry interval (seconds)")
    parser.add_argument("--duration", type=float, default=30.0, help="Test duration (seconds)")
    parser.add_argument("--no-reconnect", dest="reconnect", action="store_false", help="Disable reconnect test")
    parser.set_defaults(reconnect=True)

    args = parser.parse_args()

    metrics = asyncio.run(
        run_simulation(
            base_url=args.url,
            client_count=args.clients,
            enrollment_key=args.key,
            telemetry_interval=args.interval,
            duration=args.duration,
            test_reconnect=args.reconnect,
        )
    )

    metrics.print_summary()

    # Pass/fail criterion: at least 90% telemetry success if any attempts were made
    if metrics.telemetry_uploads_attempted > 0:
        rate = metrics.telemetry_uploads_succeeded / metrics.telemetry_uploads_attempted
        if rate < 0.90 or metrics.sqlite_lock_errors > 0:
            sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
