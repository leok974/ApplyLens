#!/usr/bin/env python3
"""
Generate realistic-looking test emails that trigger the v3/v3.1 phishing signals
and bulk index them through the applylens_emails_v3 pipeline.

Usage:
  ES_URL=http://localhost:9200 python scripts/generate_test_emails.py
"""

import json
import os
import time

import requests
from datetime import datetime

ES = os.environ.get("ES_URL", "http://localhost:9200")
INDEX = os.environ.get("ES_INDEX", "gmail_emails-999999")  # scratch index for tests
PIPELINE = os.environ.get("ES_PIPELINE", "applylens_emails_v3")


def bulk(actions):
    payload = []
    for a in actions:
        payload.append(json.dumps({"index": {"_index": INDEX, "_id": a["_id"]}}))
        payload.append(json.dumps(a["_source"]))
    data = "\n".join(payload) + "\n"
    r = requests.post(
        f"{ES}/_bulk?pipeline={PIPELINE}",
        data=data,
        headers={"Content-Type": "application/x-ndjson"},
    )
    r.raise_for_status()
    resp = r.json()
    if resp.get("errors"):
        raise SystemExit(json.dumps(resp, indent=2))
    return resp


def doc(_id, **src):
    src.setdefault("received_at", datetime.utcnow().isoformat() + "Z")
    src.setdefault("labels_norm", [])
    return {"_id": _id, "_source": src}


def main():
    # 0) ensure index exists (simple dev settings)
    requests.put(
        f"{ES}/{INDEX}",
        json={"settings": {"number_of_shards": 1, "number_of_replicas": 0}},
    )

    tests = []

    # 1) Brand mismatch + non-canonical domain + risky phrases (your sample)
    tests.append(
        doc(
            "tc1-brand-mismatch",
            subject="You're Invited: Software Developer Interview",
            from_="Terell Johnson <remotetech@careers-finetunelearning.com>",
            **{
                "from": "Terell Johnson <remotetech@careers-finetunelearning.com>",
                "reply_to": "interview@careers-finetunelearning.com",
                "headers_authentication_results": "mx.google.com; spf=neutral; dkim=pass header.d=careers-finetunelearning.com; dmarc=none",
                "headers_received_spf": "neutral (google.com: 203.0.113.8 is neither permitted nor denied)",
                "body_text": (
                    "Thank you for your interest in Prometric / Finetune. "
                    "A mini home office will be arranged for you. Please reply with your name, phone, location. "
                    "The executive team will assign projects. Work from anywhere. Flexible hours."
                ),
                "body_html": (
                    "<p>Thanks for your interest in <b>Prometric</b> / <b>Finetune</b>."
                    " A <i>mini home office</i> will be arranged. "
                    "Please reply with your name, phone, location.</p>"
                ),
                "attachments": [],
            },
        )
    )

    # 2) Reply-To mismatch → points to proton.me
    tests.append(
        doc(
            "tc2-replyto-mismatch",
            subject="Next steps for interview (Finetune by Prometric)",
            **{
                "from": "hr@finetunelearning.com",
                "reply_to": "recruiting.screen@safe-proton.proton.me",
                "headers_authentication_results": "mx.google.com; spf=pass; dkim=pass header.d=finetunelearning.com; dmarc=pass",
                "headers_received_spf": "pass (google.com: domain of finetunelearning.com designates 198.51.100.2 as permitted sender)",
                "body_text": "Please respond to our screening team at the address above for your equipment shipment.",
                "body_html": "<p>Please reply to confirm.</p>",
                "attachments": [],
            },
        )
    )

    # 3) SPF fail + DMARC fail
    tests.append(
        doc(
            "tc3-spf-dmarc-fail",
            subject="HR Update from Prometric",
            **{
                "from": "hiring@prometric.com",
                "reply_to": "hiring@prometric.com",
                "headers_authentication_results": "mx.google.com; spf=fail; dkim=fail; dmarc=fail (p=reject)",
                "headers_received_spf": "fail (google.com: 198.51.100.200 is not permitted by domain prometric.com SPF)",
                "body_text": "Please confirm your onboarding details.",
                "body_html": "<p>Please confirm your onboarding details.</p>",
                "attachments": [],
            },
        )
    )

    # 4) Shortener + anchor mismatch (text says prometric.com, href goes to bit.ly)
    tests.append(
        doc(
            "tc4-shortener-anchor-mismatch",
            subject="Schedule Interview",
            **{
                "from": "talent@prometric.com",
                "reply_to": "talent@prometric.com",
                "headers_authentication_results": "mx.google.com; spf=pass; dkim=pass; dmarc=pass",
                "headers_received_spf": "pass",
                "body_html": (
                    '<p>Schedule here: <a href="https://bit.ly/schedule123">https://prometric.com/interview</a></p>'
                    '<p>Or visit <a href="https://lnkd.in/somehash">Careers</a></p>'
                ),
                "body_text": "Schedule here: https://bit.ly/schedule123",
                "attachments": [],
            },
        )
    )

    # 5) Risky attachments (.docm & .zip)
    tests.append(
        doc(
            "tc5-risky-attachments",
            subject="Offer Letter and Equipment Invoice",
            **{
                "from": "offers@prometric.com",
                "reply_to": "offers@prometric.com",
                "headers_authentication_results": "mx.google.com; spf=pass; dkim=pass; dmarc=pass",
                "headers_received_spf": "pass",
                "body_text": "See attached offer and equipment invoice.",
                "body_html": "<p>See attached offer and equipment invoice.</p>",
                "attachments": [
                    {
                        "filename": "Offer_Letter.docm",
                        "mime": "application/vnd.ms-word.document.macroEnabled.12",
                    },
                    {"filename": "Equipment_Invoice.zip", "mime": "application/zip"},
                ],
            },
        )
    )

    # 6) Newly-registered offbrand domain (simulate via from_domain)
    tests.append(
        doc(
            "tc6-young-domain",
            subject="Interview Invite",
            **{
                "from": "recruit@new-hire-team-hr.com",
                "reply_to": "recruit@new-hire-team-hr.com",
                "from_domain": "new-hire-team-hr.com",
                "headers_authentication_results": "mx.google.com; spf=neutral; dkim=neutral; dmarc=none",
                "headers_received_spf": "neutral",
                "body_text": "We're excited to proceed quickly. Please share ID images to expedite.",
                "body_html": "<p>We're excited to proceed quickly. Please share ID images to expedite.</p>",
                "attachments": [],
            },
        )
    )

    # 7) Low-risk control (should be OK)
    tests.append(
        doc(
            "tc7-ok-control",
            subject="Interview with Prometric — Backend Engineer",
            **{
                "from": "first.last@prometric.com",
                "reply_to": "first.last@prometric.com",
                "headers_authentication_results": "mx.google.com; spf=pass; dkim=pass header.d=prometric.com; dmarc=pass",
                "headers_received_spf": "pass",
                "body_text": "Please join the Zoom link in the calendar invite. Job ID #12345. Tech stack: Python, FastAPI, ES.",
                "body_html": '<p>Calendar invite attached from @prometric.com. Tech stack: Python, FastAPI, ES.</p><p><a href="https://prometric.com/careers/12345">Posting</a></p>',
                "attachments": [],
            },
        )
    )

    # Bulk index
    bulk(tests)
    print(f"Indexed {len(tests)} test docs into {INDEX} via pipeline {PIPELINE}")
    # brief wait for ingest
    time.sleep(1.0)

    # Show quick counts (suspicious vs not) if the index is the alias
    try:
        q = {"size": 0, "aggs": {"suspicious": {"terms": {"field": "suspicious"}}}}
        r = requests.post(f"{ES}/{INDEX}/_search", json=q).json()
        print("Agg suspicious:", json.dumps(r.get("aggregations", {}), indent=2))
    except Exception as e:
        print("Aggregation skipped:", e)


if __name__ == "__main__":
    main()
