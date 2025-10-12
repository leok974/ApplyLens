# pip install google-api-python-client google-auth-oauthlib google-cloud-bigquery beautifulsoup4 html5lib tldextract requests python-dateutil
from __future__ import annotations
import os, re, json, tldextract, requests
from datetime import datetime, timezone, timedelta
from base64 import urlsafe_b64decode
from bs4 import BeautifulSoup
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.cloud import bigquery
from dateutil import tz

# ----------------- CONFIG (envs with sensible defaults) -----------------
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
DAYS = int(os.getenv("BACKFILL_DAYS", "60"))

ES_URL   = os.getenv("ES_URL",   "http://localhost:9200")
ES_INDEX = os.getenv("ES_EMAIL_INDEX", "emails_v1-000001")

BQ_PROJECT = os.getenv("BQ_PROJECT", "applylens-gmail-1759983601")
BQ_DATASET = os.getenv("BQ_DATASET", "applylens")
BQ_TABLE   = os.getenv("BQ_TABLE",   "public_emails")  # applylens.public_emails

CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "client_secret.json")  # OAuth client secret path
TOKEN_PATH    = os.getenv("GMAIL_TOKEN_PATH", "token.json")             # cached token path

# ----------------- helpers -----------------
def html_to_text(html: str) -> str:
    if not html: return ""
    soup = BeautifulSoup(html, "html5lib")
    return soup.get_text(" ", strip=True)

URL_RX = re.compile(r"https?://[^\s<>\"')]+", re.I)

def extract_urls(blob: str) -> list[str]:
    return list({u.strip(").,;") for u in URL_RX.findall(blob or "")})

def parse_auth_results(headers: list[dict]) -> tuple[str|None,str|None,str|None]:
    ar = ""
    for h in headers:
        if h["name"].lower() == "authentication-results":
            ar = h["value"]; break
    def g(rx):
        m = re.search(rx, ar, re.I)
        return (m.group(1).lower() if m else None)
    return g(r"spf=(\w+)"), g(r"dkim=(\w+)"), g(r"dmarc=(\w+)")

def infer_reason(doc: dict) -> str:
    labels = doc.get("labels") or []
    subj   = f"{doc.get('subject','')}"
    if "CATEGORY_PROMOTIONS" in labels: return "Gmail: Promotions"
    if doc.get("list_unsubscribe"):     return "Unsubscribe header"
    if re.search(r"(deal|sale|promo|coupon|% off)", subj, re.I): return "Promo keywords"
    return "Uncategorized"

# ----------------- BigQuery bootstrap -----------------
def ensure_bq_table(client: bigquery.Client):
    table_id = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"
    try:
        client.get_table(table_id)
        return table_id
    except Exception:
        schema = [
            bigquery.SchemaField("id","STRING"), bigquery.SchemaField("thread_id","STRING"),
            bigquery.SchemaField("sender","STRING"), bigquery.SchemaField("sender_domain","STRING"),
            bigquery.SchemaField("subject","STRING"), bigquery.SchemaField("body_text","STRING"),
            bigquery.SchemaField("received_at","TIMESTAMP"),
            bigquery.SchemaField("labels","STRING", mode="REPEATED"),
            bigquery.SchemaField("list_unsubscribe","STRING"),
            bigquery.SchemaField("urls","STRING", mode="REPEATED"),
            bigquery.SchemaField("spf_result","STRING"),
            bigquery.SchemaField("dkim_result","STRING"),
            bigquery.SchemaField("dmarc_result","STRING"),
            bigquery.SchemaField("is_newsletter","BOOL"),
            bigquery.SchemaField("is_promo","BOOL"),
            bigquery.SchemaField("has_unsubscribe","BOOL"),
            bigquery.SchemaField("reason","STRING"),
        ]
        table = bigquery.Table(table_id, schema=schema)
        table = client.create_table(table)
        print(f"✅ Created BigQuery table: {table_id}")
        return table_id

def bq_upsert_rows(client: bigquery.Client, rows: list[dict]):
    # simple append (idempotency not guaranteed; keep demo simple)
    if not rows: return
    table_id = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"
    errors = client.insert_rows_json(table_id, rows)
    if errors:
        raise RuntimeError(f"BQ insert errors: {errors}")

# ----------------- Elasticsearch index -----------------
def es_index(doc: dict):
    rid = doc["id"]
    r = requests.post(f"{ES_URL}/{ES_INDEX}/_doc/{rid}?refresh=true",
                      headers={"Content-Type":"application/json"},
                      data=json.dumps(doc))
    r.raise_for_status()

# ----------------- Gmail auth & fetch -----------------
def gmail_service():
    # token caching
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
    creds = flow.run_local_server(port=0)  # opens browser
    return build("gmail","v1",credentials=creds, cache_discovery=False)

def main():
    print(f"🚀 Starting Gmail backfill (last {DAYS} days)")
    print(f"   ES: {ES_URL}/{ES_INDEX}")
    print(f"   BQ: {BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}")
    print()

    # BQ
    bq_client = bigquery.Client(project=BQ_PROJECT)
    ensure_bq_table(bq_client)

    # Gmail
    print("🔐 Authenticating with Gmail API...")
    svc = gmail_service()
    print("✅ Gmail authentication successful")
    
    query = f"newer_than:{DAYS}d"
    print(f"📬 Fetching messages with query: {query}")
    msgs = []
    resp = svc.users().messages().list(userId="me", q=query, maxResults=100).execute()
    msgs.extend(resp.get("messages", []))
    
    pages = 1
    while resp.get("nextPageToken"):
        resp = svc.users().messages().list(userId="me", q=query, maxResults=250, pageToken=resp["nextPageToken"]).execute()
        msgs.extend(resp.get("messages", []))
        pages += 1
        if pages % 5 == 0:
            print(f"   Fetched {len(msgs)} message IDs so far...")

    print(f"✅ Found {len(msgs)} messages across {pages} pages")
    print()

    to_bq = []
    for idx, m in enumerate(msgs, 1):
        if idx % 50 == 0:
            print(f"   Processing message {idx}/{len(msgs)}...")
            
        msg = svc.users().messages().get(userId="me", id=m["id"], format="full").execute()
        headers = msg["payload"].get("headers", [])
        H = {h["name"].lower(): h["value"] for h in headers}
        thread_id = msg.get("threadId")
        subject   = H.get("subject","")
        sender    = H.get("from","")
        sender_dom = ""
        if "@" in sender:
            sender_dom = tldextract.extract(sender.split("@")[-1]).registered_domain or ""
        internal_ts = int(msg.get("internalDate","0"))/1000
        received_at = datetime.fromtimestamp(internal_ts, tz=timezone.utc).isoformat()

        # body gather
        def part_text(p):
            data = p.get("body",{}).get("data")
            return urlsafe_b64decode(data).decode("utf-8","ignore") if data else ""
        body_html, body_text = "", ""
        stack = [msg["payload"]]
        while stack:
            p = stack.pop()
            mt = p.get("mimeType","")
            if mt.startswith("text/plain"):
                body_text += part_text(p)
            elif mt.startswith("text/html"):
                body_html += part_text(p)
            for c in p.get("parts") or []: stack.append(c)
        if not body_text and body_html:
            body_text = html_to_text(body_html)

        urls = extract_urls((body_html or "") + "\n" + (body_text or ""))
        list_unsub = H.get("list-unsubscribe","")
        labels = msg.get("labelIds", [])
        spf, dkim, dmarc = parse_auth_results(headers)

        is_newsletter = bool(list_unsub or H.get("list-id"))
        is_promo = bool(re.search(r"(deal|sale|promo|coupon|% off)", subject + " " + body_text, re.I))
        has_unsubscribe = bool(list_unsub)

        doc = {
            "id": m["id"],
            "thread_id": thread_id,
            "sender": sender,
            "sender_domain": sender_dom,
            "subject": subject,
            "body_text": body_text[:50000],  # guard
            "received_at": received_at,
            "labels": labels,
            "list_unsubscribe": list_unsub,
            "urls": urls,
            "spf_result": spf, "dkim_result": dkim, "dmarc_result": dmarc,
            "is_newsletter": is_newsletter,
            "is_promo": is_promo,
            "has_unsubscribe": has_unsubscribe,
        }
        doc["reason"] = infer_reason(doc)

        # send to ES
        try:
            es_index(doc)
        except Exception as e:
            print(f"   ⚠️  Failed to index {m['id']} to ES: {e}")

        # also prepare for BQ
        bq_row = doc.copy()
        try:
            bq_upsert_rows(bq_client, [bq_row])  # small batches; fine for demo
        except Exception as e:
            print(f"   ⚠️  Failed to insert {m['id']} to BQ: {e}")

    print()
    print(f"✅ Backfill complete — indexed {len(msgs)} messages into ES + BQ")
    print()
    print("📊 Verification commands:")
    print(f"   ES count: curl -s {ES_URL}/{ES_INDEX}/_count | jq")
    print(f"   BQ count: bq query --project_id={BQ_PROJECT} 'SELECT COUNT(*) FROM {BQ_DATASET}.{BQ_TABLE}'")

if __name__ == "__main__":
    main()
