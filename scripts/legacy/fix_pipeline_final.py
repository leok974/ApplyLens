#!/usr/bin/env python3
"""
Convert Elasticsearch pipeline with triple-quoted Pain

less scripts to valid JSON.
Properly escapes newlines and quotes within the scripts.
"""

import json
import re


def convert_triple_quoted_to_json_string(source_code):
    """Convert multi-line Painless code to a JSON-safe single-line string."""
    # Keep actual newlines as \n
    lines = source_code.strip().split("\n")
    # Join lines, keeping indentation meaningful but removing excess spaces
    cleaned_lines = []
    for line in lines:
        # Keep the line structure but normalize indentation
        stripped = line.strip()
        if stripped:
            cleaned_lines.append(stripped)

    # Join with actual newlines
    joined = "\n".join(cleaned_lines)

    # Escape backslashes first, then quotes
    escaped = joined.replace("\\", "\\\\").replace('"', '\\"')

    return escaped


# Read the file with triple quotes
with open("infra/elasticsearch/pipelines/emails_v3.json", "r", encoding="utf-8") as f:
    content = f.read()

# Find and replace all triple-quoted source blocks
pattern = r'"source":\s*"""(.*?)"""'


def replace_source(match):
    source_code = match.group(1)
    escaped_source = convert_triple_quoted_to_json_string(source_code)
    return f'"source": "{escaped_source}"'


# Replace all occurrences
fixed_content = re.sub(pattern, replace_source, content, flags=re.DOTALL)

# Validate JSON
try:
    data = json.loads(fixed_content)
    print("✅ JSON is now valid")

    # Save with pretty formatting
    with open(
        "infra/elasticsearch/pipelines/emails_v3_final.json", "w", encoding="utf-8"
    ) as f:
        json.dump(data, f, indent=2)

    print("✅ Saved to emails_v3_final.json")
    print(f'   Description: {data.get("description", "N/A")}')
    print(f'   Processors: {len(data.get("processors", []))}')

except json.JSONDecodeError as e:
    print(f"❌ Still invalid: {e}")
    print(f"   Position: line {e.lineno}, column {e.colno}")
    # Save for debugging
    with open(
        "infra/elasticsearch/pipelines/emails_v3_final.json", "w", encoding="utf-8"
    ) as f:
        f.write(fixed_content)
    print("   Saved partially fixed version for debugging")
