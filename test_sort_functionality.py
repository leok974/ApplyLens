import requests
import json

print("=" * 70)
print("TESTING SORTABLE TIME-TO-RESPONSE (TTR)")
print("=" * 70)

# Test 1: Fastest responses first (only replied)
print("\n📊 TEST 1: Fastest response times (ttr_asc + replied=true)")
print("-" * 70)

r = requests.get('http://localhost:8003/search', params={
    'q': 'interview',
    'replied': 'true',
    'sort': 'ttr_asc',
    'size': '3'
})

if r.ok:
    data = r.json()
    print(f"Found {len(data.get('hits', []))} results")
    for i, hit in enumerate(data.get('hits', [])[:3], 1):
        ttr = hit.get('time_to_response_hours')
        subject = hit.get('subject', 'N/A')[:60]
        print(f"{i}. {subject}")
        print(f"   TTR: {ttr:.1f}h" if ttr else "   TTR: N/A")
        print(f"   Replied: {hit.get('replied')}, Count: {hit.get('user_reply_count')}")
else:
    print(f"❌ Error: {r.status_code} - {r.text}")

# Test 2: Slowest / no-reply first
print("\n📊 TEST 2: Slowest or no-reply first (ttr_desc)")
print("-" * 70)

r = requests.get('http://localhost:8003/search', params={
    'q': 'interview',
    'sort': 'ttr_desc',
    'size': '3'
})

if r.ok:
    data = r.json()
    print(f"Found {len(data.get('hits', []))} results")
    for i, hit in enumerate(data.get('hits', [])[:3], 1):
        ttr = hit.get('time_to_response_hours')
        subject = hit.get('subject', 'N/A')[:60]
        replied = hit.get('replied')
        print(f"{i}. {subject}")
        if replied:
            print(f"   TTR: {ttr:.1f}h" if ttr else "   TTR: N/A")
        else:
            print(f"   No reply yet")
        print(f"   Replied: {replied}")
else:
    print(f"❌ Error: {r.status_code} - {r.text}")

# Test 3: Newest first
print("\n📊 TEST 3: Newest first (received_desc)")
print("-" * 70)

r = requests.get('http://localhost:8003/search', params={
    'q': 'offer',
    'sort': 'received_desc',
    'size': '3'
})

if r.ok:
    data = r.json()
    print(f"Found {len(data.get('hits', []))} results")
    for i, hit in enumerate(data.get('hits', [])[:3], 1):
        subject = hit.get('subject', 'N/A')[:60]
        received = hit.get('received_at', 'N/A')[:19]  # Just date/time part
        print(f"{i}. {subject}")
        print(f"   Received: {received}")
else:
    print(f"❌ Error: {r.status_code} - {r.text}")

# Test 4: Oldest first
print("\n📊 TEST 4: Oldest first (received_asc)")
print("-" * 70)

r = requests.get('http://localhost:8003/search', params={
    'q': 'application',
    'sort': 'received_asc',
    'size': '3'
})

if r.ok:
    data = r.json()
    print(f"Found {len(data.get('hits', []))} results")
    for i, hit in enumerate(data.get('hits', [])[:3], 1):
        subject = hit.get('subject', 'N/A')[:60]
        received = hit.get('received_at', 'N/A')[:19]
        print(f"{i}. {subject}")
        print(f"   Received: {received}")
else:
    print(f"❌ Error: {r.status_code} - {r.text}")

# Test 5: Default relevance
print("\n📊 TEST 5: Relevance (default scoring)")
print("-" * 70)

r = requests.get('http://localhost:8003/search', params={
    'q': 'interview',
    'sort': 'relevance',
    'size': '3'
})

if r.ok:
    data = r.json()
    print(f"Found {len(data.get('hits', []))} results")
    for i, hit in enumerate(data.get('hits', [])[:3], 1):
        subject = hit.get('subject', 'N/A')[:60]
        score = hit.get('score', 0)
        print(f"{i}. {subject}")
        print(f"   Score: {score:.2f}")
else:
    print(f"❌ Error: {r.status_code} - {r.text}")

print("\n" + "=" * 70)
print("✅ All sorting tests complete!")
print("=" * 70)
print("\n💡 Next: Open http://localhost:5175/search and test the Sort dropdown")
