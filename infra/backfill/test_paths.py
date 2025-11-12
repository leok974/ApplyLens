import os
import json
import urllib.request
from urllib.error import HTTPError

KEY = os.getenv("BACKFILL_API_KEY")

# Test both paths
apis = [
    "http://applylens-api-prod:8003/api/gmail/backfill",
    "http://applylens-api-prod:8003/gmail/backfill",
]

for API in apis:
    print(f"\nTesting: {API}")

    body = json.dumps({"days": 2}).encode("utf-8")
    req = urllib.request.Request(API, data=body, method="POST")
    req.add_header("content-type", "application/json")
    if KEY:
        req.add_header("x-api-key", KEY)

    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(f"  ✓ Status {r.status}: {r.read(256).decode()}")
            break
    except HTTPError as e:
        print(f"  ✗ HTTP {e.code}: {e.read(128).decode()}")
    except Exception as e:
        print(f"  ✗ {type(e).__name__}: {e}")
