#!/usr/bin/env python3
"""
Grafana Alert Webhook Listener

Simple HTTP server that listens for Grafana alert notifications on port 9000.
Used for testing Grafana contact points locally.

Usage:
    python tools/grafana_webhook.py

Then in Grafana:
    Alerting → Contact points → Default → Test

The webhook will print the alert payload to console.
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import sys
from datetime import datetime


class AlertHandler(BaseHTTPRequestHandler):
    """Handle incoming webhook POST requests from Grafana"""

    def log_message(self, format, *args):
        """Suppress default HTTP logging"""
        pass

    def do_POST(self):
        """Handle POST requests with alert payloads"""
        length = int(self.headers.get("content-length", 0))
        body = self.rfile.read(length).decode("utf-8")

        try:
            payload = json.loads(body)
        except Exception:
            payload = {"raw": body}

        # Print formatted alert
        print("\n" + "=" * 70)
        print(
            f"🚨 GRAFANA ALERT RECEIVED - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print("=" * 70)

        if isinstance(payload, dict):
            # Pretty print common fields
            if "status" in payload:
                status_emoji = "🔥" if payload["status"] == "firing" else "✅"
                print(f"\n{status_emoji} Status: {payload['status'].upper()}")

            if "alerts" in payload:
                print(f"\n📊 Alerts ({len(payload['alerts'])}):")
                for i, alert in enumerate(payload["alerts"], 1):
                    print(f"\n  Alert #{i}:")
                    if "labels" in alert:
                        print(f"    Labels: {json.dumps(alert['labels'], indent=6)}")
                    if "annotations" in alert:
                        print(
                            f"    Annotations: {json.dumps(alert['annotations'], indent=6)}"
                        )
                    if "status" in alert:
                        print(f"    Status: {alert['status']}")
                    if "startsAt" in alert:
                        print(f"    Started: {alert['startsAt']}")

            print("\n📦 Full Payload:")
            print(json.dumps(payload, indent=2))
        else:
            print(payload)

        print("\n" + "=" * 70 + "\n")

        # Send response
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

    def do_GET(self):
        """Handle GET requests (health check)"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "listening", "path": "/webhook"}')


if __name__ == "__main__":
    port = 9000
    server_address = ("0.0.0.0", port)

    print("\n" + "=" * 70)
    print("🎧 GRAFANA WEBHOOK LISTENER")
    print("=" * 70)
    print(f"\n✓ Listening on http://0.0.0.0:{port}/webhook")
    print(f"✓ Health check: http://localhost:{port}/")
    print("\nConfigured in Grafana contact point as:")
    print(f"  http://host.docker.internal:{port}/webhook")
    print("\nPress Ctrl+C to stop")
    print("=" * 70 + "\n")

    try:
        httpd = HTTPServer(server_address, AlertHandler)
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down webhook listener...\n")
        sys.exit(0)
