#!/usr/bin/env python3
"""
Healthcheck for Agent Feedback Aggregator

Verifies the cron container is running and responsive.
Used by Docker healthcheck.
"""

import sys

# Simple healthcheck - if Python can run this script, container is healthy
print("OK")
sys.exit(0)
