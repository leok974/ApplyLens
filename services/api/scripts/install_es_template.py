#!/usr/bin/env python3
"""
Install Elasticsearch index template for email security fields.

This script installs the emails-template.json template which ensures all new
indices pick up security analysis fields (risk_score, quarantined, flags, etc.).

Usage:
    python scripts/install_es_template.py

Environment Variables:
    ES_URL - Elasticsearch URL (default: http://localhost:9200)
    ES_TEMPLATE_FILE - Path to template JSON (default: es/templates/emails-template.json)
"""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch import Elasticsearch


def load_template(template_file: str) -> dict:
    """Load template JSON from file."""
    path = Path(__file__).parent.parent / template_file
    if not path.exists():
        raise FileNotFoundError(f"Template file not found: {path}")

    with open(path, "r") as f:
        return json.load(f)


def install_template(es_url: str, template_name: str, template_body: dict) -> bool:
    """Install index template in Elasticsearch."""
    try:
        es = Elasticsearch([es_url])

        # Check cluster health
        health = es.cluster.health()
        print(f"✅ Connected to Elasticsearch cluster: {health['cluster_name']}")
        print(f"   Status: {health['status']}, Nodes: {health['number_of_nodes']}")

        # Install template
        print(f"\n🔧 Installing index template '{template_name}'...")
        es.indices.put_index_template(name=template_name, body=template_body)

        print(f"✅ Successfully installed template '{template_name}'")

        # Verify installation
        template = es.indices.get_index_template(name=template_name)
        patterns = template["index_templates"][0]["index_template"]["index_patterns"]
        priority = template["index_templates"][0]["index_template"]["priority"]

        print("\n📋 Template Details:")
        print(f"   Index Patterns: {', '.join(patterns)}")
        print(f"   Priority: {priority}")
        print(
            f"   Mappings: {len(template_body['template']['mappings']['properties'])} properties"
        )

        return True

    except Exception as e:
        print(f"❌ Error installing template: {e}")
        return False


def main():
    """Main entry point."""
    es_url = os.getenv("ES_URL", "http://localhost:9200")
    template_file = os.getenv("ES_TEMPLATE_FILE", "es/templates/emails-template.json")
    template_name = "emails-template"

    print("🚀 Elasticsearch Template Installer")
    print("=" * 60)
    print(f"ES URL: {es_url}")
    print(f"Template File: {template_file}")
    print(f"Template Name: {template_name}")
    print("=" * 60)

    try:
        # Load template
        print(f"\n📖 Loading template from {template_file}...")
        template_body = load_template(template_file)
        print("✅ Template loaded successfully")

        # Install template
        success = install_template(es_url, template_name, template_body)

        if success:
            print("\n" + "=" * 60)
            print("✅ Template installation complete!")
            print("\nNext steps:")
            print("1. New indices matching the pattern will use this template")
            print(
                "2. For existing indices, use: python scripts/update_existing_index_mapping.py"
            )
            print(
                "3. Verify with: curl http://localhost:9200/_index_template/emails-template"
            )
            sys.exit(0)
        else:
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
