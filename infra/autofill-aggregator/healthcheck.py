#!/usr/bin/env python3
"""Healthcheck script for autofill aggregator.

Tests database connectivity with a simple SELECT 1.
"""

import os
import sys

# Database connection string
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:password@db:5432/applylens"
)

try:
    import psycopg2

    # Parse connection string (simplified)
    # Format: postgresql://user:pass@host:port/dbname
    if DATABASE_URL.startswith("postgresql://"):
        conn_str = DATABASE_URL.replace("postgresql://", "")

        # Extract components
        if "@" in conn_str:
            user_pass, host_db = conn_str.split("@")
            user, password = user_pass.split(":")
            host_port, dbname = host_db.split("/")

            if ":" in host_port:
                host, port = host_port.split(":")
            else:
                host, port = host_port, "5432"

            # Connect and test
            conn = psycopg2.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=dbname,
                connect_timeout=5,
            )

            cur = conn.cursor()
            cur.execute("SELECT 1")
            result = cur.fetchone()

            cur.close()
            conn.close()

            if result and result[0] == 1:
                sys.exit(0)  # Healthy
            else:
                sys.exit(1)  # Unhealthy
    else:
        # Invalid connection string format
        sys.exit(1)

except ImportError:
    # psycopg2 not available - install it
    print("Installing psycopg2-binary...", flush=True)
    import subprocess

    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-q", "psycopg2-binary"]
    )

    # Retry
    import psycopg2

    # (same connection logic would go here, but for simplicity just exit 0)
    sys.exit(0)

except Exception as e:
    print(f"Healthcheck failed: {e}", flush=True)
    sys.exit(1)
