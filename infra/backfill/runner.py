import os
import time
import json
import random
import sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from datetime import datetime

API = os.getenv("API_URL", "http://applylens-api:8003/gmail/backfill")
KEY = os.getenv("BACKFILL_API_KEY", "")
MINS = int(os.getenv("EVERY_MINUTES", "30"))
DAYS = int(os.getenv("BACKFILL_DAYS", "2"))


def log(level, msg):
    ts = datetime.utcnow().isoformat() + "Z"
    print(f"[backfill] {ts} {level} {msg}", flush=True)


def run_once():
    body = json.dumps({"days": DAYS}).encode("utf-8")
    req = Request(API, data=body, method="POST")
    req.add_header("content-type", "application/json")
    if KEY:
        req.add_header("x-api-key", KEY)
    with urlopen(req, timeout=120) as resp:
        status = resp.status
        text = resp.read(256).decode(errors="replace")
        return status, text


def main():
    # initial small jitter to avoid thundering herd after restart
    time.sleep(random.randint(5, 25))
    while True:
        ok = False
        for attempt in range(1, 4):
            try:
                status, text = run_once()
                log("OK", f"attempt={attempt} status={status} body={text!r}")
                ok = True
                break
            except HTTPError as e:
                log(
                    "ERR", f"attempt={attempt} http={e.code} {getattr(e, 'reason', '')}"
                )
            except URLError as e:
                log("ERR", f"attempt={attempt} urlerror={e.reason}")
            except Exception as e:
                log("ERR", f"attempt={attempt} exception={type(e).__name__}: {e}")
            time.sleep(10 * attempt)

        # sleep until next run
        sleep_seconds = MINS * 60 + random.randint(0, 30)
        log("SLEEP", f"next_in_s={sleep_seconds} success={ok}")
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("EXIT", "keyboard interrupt")
        sys.exit(0)
