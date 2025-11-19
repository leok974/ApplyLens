"""
Quick smoke script for Mailbox Agent V2.

Runs one query per intent against /api/v2/agent/run and prints a compact summary.
Use this to eyeball responses and tune prompts / cards.
"""

import json
import uuid
from typing import Dict

import httpx

API_BASE = "http://localhost:8003"  # inside host; nginx proxies /api → FastAPI

INTENT_QUERIES: Dict[str, str] = {
    "suspicious": "Show suspicious or scam emails from the last 14 days",
    "bills": "Show my bills and invoices from the last 30 days",
    "interviews": "Show my interview and recruiter emails from the last 30 days",
    "followups": "Which recruiter or interview threads should I follow up on?",
    "profile": "Give me a profile and stats overview of my job-search inbox for the last 60 days",
    "generic": "Show me my recent job application emails and what I should prioritize next",
}


def run_one(query: str, time_window_days: int = 30) -> dict:
    payload = {
        "run_id": f"smoke-{uuid.uuid4()}",
        "user_id": "leoklemet.pa@gmail.com",  # User with ES data
        "mode": "preview_only",
        "context": {
            "time_window_days": time_window_days,
            "filters": {},
        },
        "query": query,
    }

    url = f"{API_BASE}/agent/mailbox/run"  # Correct path without /api prefix
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def main() -> None:
    all_results = {}
    for intent_key, query in INTENT_QUERIES.items():
        print(f"\n=== Running intent={intent_key!r} query ===")
        print(query)
        print("----")

        result = run_one(query, time_window_days=30)
        all_results[intent_key] = result

        tools = result.get("tools_used", [])
        cards = result.get("cards", [])

        print(f"intent (reported): {result.get('intent')}")
        print(f"tools_used: {tools}")
        print(f"answer (first 240 chars): {result.get('answer', '')[:240]!r}")
        print(f"cards: {len(cards)} total")
        for idx, card in enumerate(cards[:3]):
            print(
                f"  [{idx}] kind={card.get('kind')} "
                f"title={card.get('title')!r} "
                f"emails={len(card.get('email_ids', []))}"
            )

    # Optionally dump everything to a file for later inspection
    with open("agent_v2_intent_samples.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print("\nWrote detailed samples to agent_v2_intent_samples.json")


if __name__ == "__main__":
    main()
