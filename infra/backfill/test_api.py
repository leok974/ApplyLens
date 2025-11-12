import os
import json
import urllib.request
from urllib.error import HTTPError, URLError

API = os.getenv("API_URL")
KEY = os.getenv("BACKFILL_API_KEY")

print(f"Testing API: {API}")
print(f"API Key present: {'Yes' if KEY else 'No'}")

body = json.dumps({"days": 2}).encode("utf-8")
req = urllib.request.Request(API, data=body, method="POST")
req.add_header("content-type", "application/json")
if KEY:
    req.add_header("x-api-key", KEY)

try:
    with urllib.request.urlopen(req, timeout=60) as r:
        print(f"\n✓ Success! Status: {r.status}")
        print(f"Response: {r.read().decode()}")
except HTTPError as e:
    print(f"\n✗ HTTP Error {e.code}: {e.reason}")
    print(f"Response: {e.read().decode()}")
except URLError as e:
    print(f"\n✗ URL Error: {e.reason}")
except Exception as e:
    print(f"\n✗ Exception: {type(e).__name__}: {e}")
