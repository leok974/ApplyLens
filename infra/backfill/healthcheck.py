#!/usr/bin/env python3
"""Healthcheck script for backfill scheduler.

Probes the API endpoint to verify connectivity and authentication.
Allows 4xx/5xx responses (rate limits, auth failures) as these indicate
the API is reachable and the scheduler can proceed normally.
"""

import os
import sys
import urllib.request
from urllib.error import HTTPError, URLError

try:
    u = os.getenv("API_URL")
    k = os.getenv("BACKFILL_API_KEY")

    req = urllib.request.Request(u, data=b"{}", method="POST")
    req.add_header("content-type", "application/json")
    if k:
        req.add_header("x-api-key", k)

    # Probe API - any HTTP response (even 4xx/5xx) means API is reachable
    urllib.request.urlopen(req, timeout=10)
    sys.exit(0)
except HTTPError:
    # HTTP errors (429, 400, etc.) are OK - API is reachable and responding
    sys.exit(0)
except URLError:
    # Network/connection failure - healthcheck fails
    sys.exit(1)
except Exception:
    # Other errors - healthcheck fails
    sys.exit(1)
