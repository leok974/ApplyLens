#!/usr/bin/env python3
"""
Fix Elasticsearch pipeline JSON by replacing triple quotes with regular quotes.
"""

import json

# Read the original file
with open("infra/elasticsearch/pipelines/emails_v3.json", "r", encoding="utf-8") as f:
    content = f.read()

# Replace triple-quoted strings: """...""" becomes "..."
# This keeps the newlines inside the string
content_fixed = content.replace('"""', '"')

# Try to parse as JSON
try:
    data = json.loads(content_fixed)
    print("✅ JSON is valid after removing triple quotes")

    # Save with formatting
    with open(
        "infra/elasticsearch/pipelines/emails_v3_corrected.json", "w", encoding="utf-8"
    ) as f:
        json.dump(data, f, indent=2)

    print("✅ Saved to emails_v3_corrected.json")
    print(f'   Processors: {len(data.get("processors", []))}')

except json.JSONDecodeError as e:
    print(f"❌ Still invalid: {e}")
    # Save for inspection
    with open(
        "infra/elasticsearch/pipelines/emails_v3_corrected.json", "w", encoding="utf-8"
    ) as f:
        f.write(content_fixed)
    print("   Saved partially fixed version for inspection")
