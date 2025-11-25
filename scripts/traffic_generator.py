#!/usr/bin/env python3
"""
Traffic generator for ApplyLens hackathon demo.

Generates controlled load with various failure modes to demonstrate
Datadog dashboards and incident management.

Usage:
    python scripts/traffic_generator.py --mode normal_traffic --rate 10 --duration 300
    python scripts/traffic_generator.py --mode latency_injection --rate 20 --duration 120
    python scripts/traffic_generator.py --mode error_injection --rate 15 --duration 90
    python scripts/traffic_generator.py --mode token_bloat --rate 25 --duration 60
"""

import argparse
import asyncio
import random
import time
from typing import Literal
import httpx
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test email samples for classification
SAMPLE_EMAILS = [
    {
        "subject": "Interview Invitation - Senior Engineer",
        "snippet": "We'd like to schedule a technical interview for the Senior Software Engineer position.",
        "sender": "recruiter@techcorp.com",
        "expected_intent": "interview",
    },
    {
        "subject": "Thank you for your application",
        "snippet": "We have received your application for the Software Developer role and will review it shortly.",
        "sender": "careers@startup.io",
        "expected_intent": "job_application",
    },
    {
        "subject": "Job Offer - Staff Engineer",
        "snippet": "Congratulations! We are pleased to offer you the Staff Engineer position at our company.",
        "sender": "hr@megacorp.com",
        "expected_intent": "offer",
    },
    {
        "subject": "Application Status Update",
        "snippet": "Unfortunately, we have decided to move forward with other candidates at this time.",
        "sender": "noreply@jobsite.com",
        "expected_intent": "rejection",
    },
    {
        "subject": "Follow-up on your application",
        "snippet": "Just wanted to check in regarding your interest in the DevOps Engineer role we discussed.",
        "sender": "hiring@cloudcompany.com",
        "expected_intent": "other",
    },
]

# Large text for token bloat injection
TOKEN_BLOAT_TEXT = (
    """
This is an extremely long email with repeated content to simulate token bloat and cost anomalies.
"""
    * 100
)


Mode = Literal["normal_traffic", "latency_injection", "error_injection", "token_bloat"]


class TrafficGenerator:
    """Generates HTTP traffic to ApplyLens API."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        rate: int = 10,
        duration: int = 300,
        mode: Mode = "normal_traffic",
    ):
        self.base_url = base_url
        self.rate = rate  # requests per second
        self.duration = duration  # seconds
        self.mode = mode
        self.client = httpx.AsyncClient(timeout=30.0)

        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_latency_ms = 0

    async def generate_traffic(self):
        """Generate traffic according to configured mode."""
        logger.info(
            f"🚀 Starting traffic generation: mode={self.mode}, rate={self.rate}/s, duration={self.duration}s"
        )

        start_time = time.time()
        end_time = start_time + self.duration

        request_interval = 1.0 / self.rate  # seconds between requests

        while time.time() < end_time:
            loop_start = time.time()

            # Send one request
            await self._send_request()

            # Sleep to maintain target rate
            elapsed = time.time() - loop_start
            sleep_time = max(0, request_interval - elapsed)
            await asyncio.sleep(sleep_time)

        await self.client.aclose()

        # Print summary
        self._print_summary()

    async def _send_request(self):
        """Send a single request based on mode."""
        self.total_requests += 1

        try:
            if self.mode == "normal_traffic":
                await self._normal_request()
            elif self.mode == "latency_injection":
                await self._latency_injection_request()
            elif self.mode == "error_injection":
                await self._error_injection_request()
            elif self.mode == "token_bloat":
                await self._token_bloat_request()

            self.successful_requests += 1

        except Exception as e:
            self.failed_requests += 1
            logger.debug(f"Request failed: {e}")

    async def _normal_request(self):
        """Normal classification request."""
        email = random.choice(SAMPLE_EMAILS)

        start = time.time()
        response = await self.client.post(
            f"{self.base_url}/hackathon/classify",
            json={
                "subject": email["subject"],
                "snippet": email["snippet"],
                "sender": email["sender"],
            },
            headers={"X-Traffic-Type": "HACKATHON_TRAFFIC"},
        )
        latency_ms = int((time.time() - start) * 1000)

        response.raise_for_status()
        self.total_latency_ms += latency_ms

        logger.debug(f"✓ Classified email: {email['expected_intent']} ({latency_ms}ms)")

    async def _latency_injection_request(self):
        """Request with artificial latency to trigger monitors."""
        email = random.choice(SAMPLE_EMAILS)

        # Add random delay before request (simulates slow network)
        if random.random() < 0.3:  # 30% of requests
            await asyncio.sleep(random.uniform(2.0, 5.0))

        start = time.time()
        response = await self.client.post(
            f"{self.base_url}/hackathon/classify",
            json={
                "subject": email["subject"],
                "snippet": email["snippet"],
                "sender": email["sender"],
            },
            headers={"X-Traffic-Type": "HACKATHON_TRAFFIC_LATENCY"},
        )
        latency_ms = int((time.time() - start) * 1000)

        response.raise_for_status()
        self.total_latency_ms += latency_ms

        logger.debug(f"✓ Slow request: {latency_ms}ms")

    async def _error_injection_request(self):
        """Request designed to trigger errors."""
        # 50% chance of malformed request
        if random.random() < 0.5:
            # Send invalid JSON
            try:
                response = await self.client.post(
                    f"{self.base_url}/hackathon/classify",
                    json={
                        # Missing required fields
                        "invalid": "data"
                    },
                    headers={"X-Traffic-Type": "HACKATHON_TRAFFIC_ERROR"},
                )
                response.raise_for_status()
            except httpx.HTTPStatusError:
                logger.debug("✓ Triggered expected error")
                raise
        else:
            # Normal request
            await self._normal_request()

    async def _token_bloat_request(self):
        """Request with massive token count to trigger cost anomaly."""
        start = time.time()
        response = await self.client.post(
            f"{self.base_url}/hackathon/classify",
            json={
                "subject": "Job Application" * 50,  # Repeated text
                "snippet": TOKEN_BLOAT_TEXT,
                "sender": "recruiter@example.com",
            },
            headers={"X-Traffic-Type": "HACKATHON_TRAFFIC_BLOAT"},
        )
        latency_ms = int((time.time() - start) * 1000)

        response.raise_for_status()
        self.total_latency_ms += latency_ms

        logger.debug(f"✓ Token bloat request: {latency_ms}ms")

    def _print_summary(self):
        """Print traffic generation summary."""
        logger.info("=" * 60)
        logger.info("Traffic Generation Summary")
        logger.info("=" * 60)
        logger.info(f"Mode: {self.mode}")
        logger.info(f"Total Requests: {self.total_requests}")
        logger.info(f"Successful: {self.successful_requests}")
        logger.info(f"Failed: {self.failed_requests}")

        if self.successful_requests > 0:
            avg_latency = self.total_latency_ms / self.successful_requests
            logger.info(f"Average Latency: {avg_latency:.0f}ms")

        success_rate = (
            (self.successful_requests / self.total_requests * 100)
            if self.total_requests > 0
            else 0
        )
        logger.info(f"Success Rate: {success_rate:.1f}%")
        logger.info("=" * 60)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="ApplyLens Traffic Generator")
    parser.add_argument(
        "--mode",
        type=str,
        choices=[
            "normal_traffic",
            "latency_injection",
            "error_injection",
            "token_bloat",
        ],
        default="normal_traffic",
        help="Traffic generation mode",
    )
    parser.add_argument("--rate", type=int, default=10, help="Requests per second")
    parser.add_argument("--duration", type=int, default=300, help="Duration in seconds")
    parser.add_argument(
        "--url", type=str, default="http://localhost:8000", help="API base URL"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    generator = TrafficGenerator(
        base_url=args.url,
        rate=args.rate,
        duration=args.duration,
        mode=args.mode,
    )

    await generator.generate_traffic()


if __name__ == "__main__":
    asyncio.run(main())
