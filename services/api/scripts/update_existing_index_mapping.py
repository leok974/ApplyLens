#!/usr/bin/env python3
"""
Update existing Elasticsearch index with security analysis fields.

This script adds security fields to an existing gmail_emails index:
- risk_score (integer)
- quarantined (boolean)  
- flags (nested array of {signal, evidence, weight})
- auth_results (object with spf, dkim, dmarc)
- url_hosts (keyword array)
- domain_tld (keyword)
- domain_first_seen_at (date)
- domain_first_seen_days_ago (integer)
- attachment_types (keyword array)

Usage:
    python scripts/update_existing_index_mapping.py

Environment Variables:
    ES_URL - Elasticsearch URL (default: http://localhost:9200)
    ES_INDEX - Index name to update (default: gmail_emails)
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from elasticsearch import Elasticsearch


# Mapping updates for security fields
SECURITY_FIELDS_MAPPING = {
    "properties": {
        "risk_score": {
            "type": "integer"
        },
        "quarantined": {
            "type": "boolean"
        },
        "flags": {
            "type": "nested",
            "properties": {
                "signal": {"type": "keyword"},
                "evidence": {"type": "text"},
                "weight": {"type": "short"}
            }
        },
        "auth_results": {
            "properties": {
                "spf": {"type": "keyword"},
                "dkim": {"type": "keyword"},
                "dmarc": {"type": "keyword"}
            }
        },
        "url_hosts": {
            "type": "keyword"
        },
        "domain_tld": {
            "type": "keyword"
        },
        "domain_first_seen_at": {
            "type": "date"
        },
        "domain_first_seen_days_ago": {
            "type": "integer"
        },
        "attachment_types": {
            "type": "keyword"
        }
    }
}


def update_index_mapping(es_url: str, index_name: str) -> bool:
    """Update index mapping with security fields."""
    try:
        es = Elasticsearch([es_url])
        
        # Check if index exists
        if not es.indices.exists(index=index_name):
            print(f"❌ Index '{index_name}' does not exist")
            print(f"   Create it first or use install_es_template.py for new indices")
            return False
        
        # Get current mapping
        current_mapping = es.indices.get_mapping(index=index_name)
        print(f"✅ Found index '{index_name}'")
        
        # Check index stats
        stats = es.indices.stats(index=index_name)
        doc_count = stats['_all']['primaries']['docs']['count']
        size_mb = stats['_all']['primaries']['store']['size_in_bytes'] / (1024 * 1024)
        print(f"   Documents: {doc_count:,}")
        print(f"   Size: {size_mb:.2f} MB")
        
        # Update mapping
        print(f"\n🔧 Adding security analysis fields...")
        es.indices.put_mapping(
            index=index_name,
            body=SECURITY_FIELDS_MAPPING
        )
        
        print(f"✅ Successfully updated mapping for '{index_name}'")
        
        # Verify updates
        updated_mapping = es.indices.get_mapping(index=index_name)
        properties = updated_mapping[index_name]['mappings']['properties']
        
        print(f"\n📋 Verified New Fields:")
        security_fields = ['risk_score', 'quarantined', 'flags', 'auth_results', 
                          'url_hosts', 'domain_tld', 'domain_first_seen_at', 
                          'domain_first_seen_days_ago', 'attachment_types']
        
        for field in security_fields:
            if field in properties:
                field_type = properties[field].get('type', 'object')
                print(f"   ✅ {field}: {field_type}")
            else:
                print(f"   ⚠️  {field}: not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating mapping: {e}")
        return False


def main():
    """Main entry point."""
    es_url = os.getenv('ES_URL', 'http://localhost:9200')
    index_name = os.getenv('ES_INDEX', 'gmail_emails')
    
    print("🚀 Elasticsearch Mapping Updater")
    print("=" * 60)
    print(f"ES URL: {es_url}")
    print(f"Index: {index_name}")
    print("=" * 60)
    
    success = update_index_mapping(es_url, index_name)
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Mapping update complete!")
        print("\nNote: Existing documents won't have these fields until re-indexed.")
        print("To backfill security analysis:")
        print("1. Run the security analyzer on existing emails")
        print("2. Or trigger a full re-sync from Gmail")
        print("\nVerify with:")
        print(f"  curl http://localhost:9200/{index_name}/_mapping | jq")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
