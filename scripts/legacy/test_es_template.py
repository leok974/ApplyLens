# STATUS: unclear. Mentioned in REPO_AUDIT_PHASE1.md.
# If not used by 2025-12-31, move to scripts/legacy/.
import os
import requests

ES = os.getenv("ES_URL", "http://localhost:9200")
name = "applylens_emails"
r = requests.get(f"{ES}/_index_template/{name}", timeout=10)
r.raise_for_status()
tmpl = r.json()["index_templates"][0]["index_template"]
pipeline = tmpl["template"]["settings"]["index"]["default_pipeline"]
assert pipeline == "applylens_emails_v2", f"default_pipeline is {pipeline}"
print("OK: default_pipeline=applylens_emails_v2")
