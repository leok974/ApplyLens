import requests

# Test 1: Search for replied emails
print("=" * 60)
print("TEST 1: Search for replied emails")
print("=" * 60)

r = requests.get(
    "http://localhost:8003/search",
    params={"q": "interview", "replied": "true", "size": "2"},
)

data = r.json()
print(f"Found {len(data.get('hits', []))} replied emails")

for i, hit in enumerate(data.get("hits", [])[:2], 1):
    ttr = hit.get("time_to_response_hours")
    ttr_display = f"{ttr:.1f}h" if ttr else "N/A"
    print(f"\n{i}. {hit.get('subject')}")
    print(f"   Replied: {hit.get('replied')}")
    print(f"   Reply count: {hit.get('user_reply_count')}")
    print(f"   Time to response: {ttr_display}")
    print(f"   Received: {hit.get('received_at')}")
    print(f"   First reply: {hit.get('first_user_reply_at')}")

# Test 2: Search for not-replied emails
print("\n" + "=" * 60)
print("TEST 2: Search for not-replied emails")
print("=" * 60)

r = requests.get(
    "http://localhost:8003/search",
    params={"q": "interview", "replied": "false", "size": "2"},
)

data = r.json()
print(f"Found {len(data.get('hits', []))} not-replied emails")

for i, hit in enumerate(data.get("hits", [])[:2], 1):
    print(f"\n{i}. {hit.get('subject')}")
    print(f"   Replied: {hit.get('replied')}")
    print(f"   Reply count: {hit.get('user_reply_count')}")

print("\n" + "=" * 60)
print("✅ API tests complete!")
print("=" * 60)
