#!/usr/bin/env python3
# STATUS: unclear. Mentioned in REPO_AUDIT_PHASE1.md.
# If not used by 2025-12-31, move to scripts/legacy/.
"""
Upload Elasticsearch pipeline using Python requests with proper JSON handling.
"""

import json
import requests
import sys

ES_URL = "http://localhost:9200"
PIPELINE_NAME = "applylens_emails_v3"

# Read the pipeline file with triple quotes
with open("infra/elasticsearch/pipelines/emails_v3.json", "r", encoding="utf-8") as f:
    content = f.read()

# Replace triple quotes with single quotes (keeping newlines as actual newlines)
content = content.replace('"""', '"')

# Now we have a JSON string with literal newlines in the "source" values
# We need to parse this carefully - Python's JSON parser won't accept it either
# So let's manually build the pipeline structure

# For now, let me try reading the already-fixed version if it exists
try:
    with open(
        "infra/elasticsearch/pipelines/emails_v3_final.json", "r", encoding="utf-8"
    ) as f:
        pipeline_data = json.load(f)
except FileNotFoundError:
    print("❌ Need valid JSON file first")
    sys.exit(1)

# Upload using requests
url = f"{ES_URL}/_ingest/pipeline/{PIPELINE_NAME}"
headers = {"Content-Type": "application/json"}

try:
    response = requests.put(url, json=pipeline_data, headers=headers)

    if response.status_code == 200:
        print("✅ Pipeline uploaded successfully")
        print(f"   Name: {PIPELINE_NAME}")
        print(f"   Processors: {len(pipeline_data.get('processors', []))}")
    else:
        print(f"❌ Upload failed: {response.status_code}")
        print(f"   Error: {response.text[:500]}")
        sys.exit(1)

except Exception as e:
    print(f"❌ Request failed: {e}")
    sys.exit(1)
