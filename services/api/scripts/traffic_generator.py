#!/usr/bin/env python3
"""
ApplyLens Traffic Generator for Hackathon Demo
Generates controlled load to demonstrate Datadog monitoring
"""

import requests
import time
import random
import argparse
import logging
from datetime import datetime

# Sample job application emails
SAMPLE_EMAILS = [
    {
        "subject": "Application for Senior Python Developer Position",
        "body": "I am writing to apply for the Senior Python Developer role at your company. I have 5 years of experience with Django, FastAPI, and cloud deployments.",
        "sender": "john.doe@example.com",
    },
    {
        "subject": "RE: Frontend Engineer Opening",
        "body": "Thank you for considering my application. I have expertise in React, TypeScript, and modern CSS frameworks. Looking forward to hearing from you.",
        "sender": "jane.smith@techmail.com",
    },
    {
        "subject": "Data Scientist Role - Application Materials",
        "body": "Attached is my resume for the Data Scientist position. I have experience with Python, TensorFlow, and large-scale ML pipelines.",
        "sender": "data.scientist@mlpro.com",
    },
    {
        "subject": "DevOps Engineer Application",
        "body": "I am interested in the DevOps Engineer role. My background includes Kubernetes, Terraform, CI/CD pipelines, and AWS/GCP infrastructure.",
        "sender": "ops.engineer@cloudops.io",
    },
    {
        "subject": "Product Manager Position Inquiry",
        "body": "I would like to apply for the Product Manager role. I have led multiple B2B SaaS products with 7+ years of experience in roadmap planning and user research.",
        "sender": "pm.leader@saas.com",
    },
]

# Large email for token bloat mode
BLOAT_EMAIL = {
    "subject": "Application with Extensive Background Details",
    "body": """I am writing to express my interest in this position. """
    + "My extensive experience includes " * 500
    + "various technical skills across multiple domains. " * 300
    + "I have worked on numerous projects involving cutting-edge technologies. " * 200,
    "sender": "verbose.applicant@example.com",
}


class TrafficGenerator:
    def __init__(self, api_url, mode, rate, duration, verbose=False):
        self.api_url = api_url.rstrip("/")
        self.mode = mode
        self.rate = rate
        self.duration = duration
        self.verbose = verbose

        # Setup logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

        # Stats tracking
        self.stats = {
            "total_requests": 0,
            "successful": 0,
            "failed": 0,
            "total_latency_ms": 0,
        }

    def generate_request_payload(self):
        """Generate request payload based on mode"""
        if self.mode == "token_bloat":
            email = BLOAT_EMAIL
        else:
            email = random.choice(SAMPLE_EMAILS)

        payload = {
            "subject": email["subject"],
            "snippet": email["body"],  # EmailSample uses 'snippet' not 'body'
            "sender": email["sender"],
        }

        # Error injection: malform 50% of requests
        if self.mode == "error_injection" and random.random() < 0.5:
            payload = {"invalid": "data"}  # Will cause 422/400 error

        return payload

    def send_request(self):
        """Send single request with mode-specific behavior"""
        payload = self.generate_request_payload()

        # Latency injection: add delay to 30% of requests
        if self.mode == "latency_injection" and random.random() < 0.3:
            delay = random.uniform(2, 5)
            self.logger.debug(f"Injecting {delay:.2f}s latency")
            time.sleep(delay)

        try:
            start = time.time()
            response = requests.post(
                f"{self.api_url}/hackathon/classify", json=payload, timeout=30
            )
            latency_ms = (time.time() - start) * 1000

            self.stats["total_requests"] += 1
            self.stats["total_latency_ms"] += latency_ms

            if response.status_code == 200:
                self.stats["successful"] += 1
                self.logger.debug(f"✅ Request successful ({latency_ms:.0f}ms)")
            else:
                self.stats["failed"] += 1
                self.logger.warning(
                    f"❌ Request failed: {response.status_code} ({latency_ms:.0f}ms)"
                )

        except requests.exceptions.RequestException as e:
            self.stats["failed"] += 1
            self.logger.error(f"❌ Request exception: {e}")

    def run(self):
        """Run traffic generator"""
        interval = 1.0 / self.rate  # Time between requests
        end_time = time.time() + self.duration

        print("=" * 70)
        print("🚀 ApplyLens Traffic Generator")
        print(f"   Mode: {self.mode}")
        print(f"   Rate: {self.rate} req/s")
        print(f"   Duration: {self.duration}s")
        print(f"   Target: {self.api_url}")
        print(f"   Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()

        request_count = 0
        while time.time() < end_time:
            self.send_request()
            request_count += 1

            # Progress update every 10 requests
            if request_count % 10 == 0:
                elapsed = self.duration - (end_time - time.time())
                avg_latency = (
                    self.stats["total_latency_ms"] / self.stats["total_requests"]
                    if self.stats["total_requests"] > 0
                    else 0
                )
                print(
                    f"📊 {request_count} requests | "
                    f"✅ {self.stats['successful']} | "
                    f"❌ {self.stats['failed']} | "
                    f"⏱️  {avg_latency:.0f}ms avg | "
                    f"⏳ {elapsed:.0f}s elapsed"
                )

            # Sleep to maintain rate
            time.sleep(interval)

        # Final stats
        print()
        print("=" * 70)
        print("✅ Traffic Generation Complete")
        print()
        print("📊 Summary:")
        print(f"   Total Requests: {self.stats['total_requests']}")
        print(
            f"   Successful: {self.stats['successful']} "
            f"({100 * self.stats['successful'] / max(self.stats['total_requests'], 1):.1f}%)"
        )
        print(
            f"   Failed: {self.stats['failed']} "
            f"({100 * self.stats['failed'] / max(self.stats['total_requests'], 1):.1f}%)"
        )

        if self.stats["total_requests"] > 0:
            avg_latency = self.stats["total_latency_ms"] / self.stats["total_requests"]
            print(f"   Average Latency: {avg_latency:.0f}ms")

        print()
        print("📈 View metrics in Datadog:")
        print("   https://us5.datadoghq.com/metric/explorer")
        print("   Search: applylens.llm.*")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="ApplyLens Traffic Generator")
    parser.add_argument(
        "--mode",
        choices=[
            "normal_traffic",
            "latency_injection",
            "error_injection",
            "token_bloat",
        ],
        default="normal_traffic",
        help="Traffic generation mode",
    )
    parser.add_argument("--rate", type=float, default=10.0, help="Requests per second")
    parser.add_argument("--duration", type=int, default=300, help="Duration in seconds")
    parser.add_argument(
        "--api-url", default="http://localhost:8000", help="API base URL"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    generator = TrafficGenerator(
        api_url=args.api_url,
        mode=args.mode,
        rate=args.rate,
        duration=args.duration,
        verbose=args.verbose,
    )

    try:
        generator.run()
    except KeyboardInterrupt:
        print("\n\n⚠️  Traffic generation interrupted by user")
        print(f"📊 Partial stats: {generator.stats['total_requests']} requests sent")


if __name__ == "__main__":
    main()
