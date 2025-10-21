#!/usr/bin/env python3
"""
Fix emails_v3.json by converting triple-quoted Painless scripts to escaped strings.
"""

import json
import re
import sys


def main():
    input_file = "infra/elasticsearch/pipelines/emails_v3.json"
    output_file = "infra/elasticsearch/pipelines/emails_v3_fixed.json"

    # Read the file
    with open(input_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace triple-quoted strings with escaped single strings
    pattern = r'"source":\s*"""(.*?)"""'

    def escape_source(match):
        source_code = match.group(1)
        # Remove leading/trailing whitespace from each line
        lines = source_code.strip().split("\n")
        # Remove indentation and join with actual newlines
        cleaned_lines = [line.strip() for line in lines if line.strip()]
        # Join with \n and escape properly
        escaped = "\\n".join(cleaned_lines)
        # Escape backslashes and quotes
        escaped = escaped.replace("\\", "\\\\").replace('"', '\\"')
        return f'"source": "{escaped}"'

    # Apply replacement
    fixed_content = re.sub(pattern, escape_source, content, flags=re.DOTALL)

    # Verify it's valid JSON
    try:
        data = json.loads(fixed_content)
        print("✅ JSON is now valid")

        # Save with pretty printing
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"✅ Saved to {output_file}")
        print(f'   Processors: {len(data["processors"])}')

        return 0
    except json.JSONDecodeError as e:
        print(f"❌ Still invalid JSON: {e}")
        # Save anyway for debugging
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(fixed_content)
        print(f"   Saved partially fixed version to {output_file} for debugging")
        return 1


if __name__ == "__main__":
    sys.exit(main())
