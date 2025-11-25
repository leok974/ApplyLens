#!/usr/bin/env python3
"""
Test Datadog Metrics Integration
Sends test metrics to verify Datadog agent is receiving data
"""

from datadog import initialize, statsd
import time
import random

# Initialize Datadog
initialize(statsd_host="dd-agent", statsd_port=8125, statsd_namespace="applylens")

print("🧪 Testing Datadog Metrics Integration...\n")

# Test 1: Counter
print("1️⃣ Sending counter metrics...")
for i in range(5):
    statsd.increment(
        "llm.test.requests", tags=["env:hackathon", "test:true", "task_type:classify"]
    )
    time.sleep(0.1)
print("   ✅ Sent 5 counter increments\n")

# Test 2: Gauge
print("2️⃣ Sending gauge metrics...")
for i in range(5):
    value = random.randint(100, 500)
    statsd.gauge(
        "llm.test.tokens_used",
        value,
        tags=["env:hackathon", "test:true", "model:gemini-1.5-flash"],
    )
    print(f"   📊 Tokens: {value}")
    time.sleep(0.1)
print("   ✅ Sent 5 gauge values\n")

# Test 3: Histogram (latency)
print("3️⃣ Sending histogram metrics...")
latencies = [450, 520, 380, 1200, 890, 650, 2100, 540, 610, 720]
for latency in latencies:
    statsd.histogram(
        "llm.latency_ms",
        latency,
        tags=["env:hackathon", "test:true", "task_type:classify"],
    )
    print(f"   ⏱️ Latency: {latency}ms")
    time.sleep(0.1)
print("   ✅ Sent 10 histogram values\n")

# Test 4: Timing
print("4️⃣ Sending timing metrics...")


@statsd.timed("llm.test.operation_duration", tags=["env:hackathon", "test:true"])
def slow_operation():
    time.sleep(random.uniform(0.1, 0.3))
    return "done"


for i in range(3):
    result = slow_operation()
    print(f"   ⏲️ Operation {i+1} completed")
print("   ✅ Sent 3 timed operations\n")

# Test 5: Error metrics
print("5️⃣ Sending error metrics...")
error_types = ["timeout", "invalid_response", "api_error"]
for error_type in error_types:
    statsd.increment(
        "llm.error_total",
        tags=["env:hackathon", "test:true", f"error_type:{error_type}"],
    )
    print(f"   ❌ Error: {error_type}")
    time.sleep(0.1)
print("   ✅ Sent 3 error counts\n")

# Summary
print("=" * 60)
print("✅ Test Complete! Metrics sent to Datadog\n")
print("📊 Metrics Summary:")
print("   - applylens.llm.test.requests (counter): 5 increments")
print("   - applylens.llm.test.tokens_used (gauge): 5 values")
print("   - applylens.llm.latency_ms (histogram): 10 values")
print("   - applylens.llm.test.operation_duration (timing): 3 values")
print("   - applylens.llm.error_total (counter): 3 increments")
print("\n📈 View in Datadog:")
print("   1. Go to: https://us5.datadoghq.com/metric/explorer")
print("   2. Search for: applylens.llm.*")
print("   3. Filter by tag: env:hackathon")
print("\n⏳ Wait 30-60 seconds for metrics to appear in Datadog UI")
print("=" * 60)
