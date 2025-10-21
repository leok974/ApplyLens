#!/usr/bin/env python3
"""
Test Elasticsearch Email Template Configuration
Ensures the email index template uses the correct pipeline version.
"""
import json
import sys
import requests

ES = "http://localhost:9200"
TEMPLATE_NAME = "applylens_emails"
EXPECTED_PIPELINE = "applylens_emails_v2"

def test_email_template():
    """Verify email index template is configured with correct pipeline."""
    print(f"Testing Elasticsearch template: {TEMPLATE_NAME}")
    
    try:
        # Get the index template
        r = requests.get(f"{ES}/_index_template/{TEMPLATE_NAME}", timeout=5)
        r.raise_for_status()
        
        # Parse response
        data = r.json()
        if not data.get("index_templates"):
            print(f"❌ FAIL: Template '{TEMPLATE_NAME}' not found")
            return False
        
        tmpl = data["index_templates"][0]["index_template"]
        
        # Extract pipeline setting
        pipeline = tmpl["template"]["settings"]["index"]["default_pipeline"]
        
        # Verify pipeline version
        if pipeline != EXPECTED_PIPELINE:
            print(f"❌ FAIL: default_pipeline is '{pipeline}', expected '{EXPECTED_PIPELINE}'")
            return False
        
        # Additional checks
        version = tmpl.get("version", 0)
        priority = tmpl.get("priority", 0)
        ilm_policy = tmpl["template"]["settings"]["index"]["lifecycle"]["name"]
        
        print(f"✅ PASS: default_pipeline = {pipeline}")
        print(f"  Version: {version}")
        print(f"  Priority: {priority}")
        print(f"  ILM Policy: {ilm_policy}")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ FAIL: Cannot connect to Elasticsearch at {ES}")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ FAIL: Elasticsearch request timed out")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"❌ FAIL: HTTP error {e.response.status_code}: {e.response.text}")
        return False
    except KeyError as e:
        print(f"❌ FAIL: Missing expected field in template: {e}")
        return False
    except Exception as e:
        print(f"❌ FAIL: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_email_template()
    sys.exit(0 if success else 1)
