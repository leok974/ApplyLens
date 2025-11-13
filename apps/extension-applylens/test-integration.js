/**
 * Simple integration test for Phase 2.1 learning profiles
 * Run this in Chrome DevTools console on a form page to verify integration
 */

(async function testLearningProfileIntegration() {
  console.log("🧪 Testing Phase 2.1 Learning Profile Integration...");

  // Mock the API responses for testing
  const originalFetch = window.fetch;
  let profileFetched = false;
  let generateAnswersFetched = false;

  window.fetch = async (url, options) => {
    console.log("📡 Fetch:", url);

    if (url.includes("/api/extension/learning/profile")) {
      profileFetched = true;
      console.log("✅ Profile endpoint called");
      return new Response(JSON.stringify({
        host: "localhost",
        schema_hash: "test-hash",
        canonical_map: {
          "#full_name": "full_name",
          "#email": "email",
          "#phone": "phone"
        },
        style_hint: {
          gen_style_id: "concise_bullets_v2",
          confidence: 0.9
        }
      }), { status: 200, headers: { 'content-type': 'application/json' } });
    }

    if (url.includes("/api/extension/generate-form-answers")) {
      generateAnswersFetched = true;
      console.log("✅ Generate answers endpoint called");
      return new Response(JSON.stringify({
        job: { title: "Software Engineer", company: "Test Co" },
        answers: [
          { field_id: "full_name", answer: "John Doe" },
          { field_id: "email", answer: "john.doe@example.com" },
          { field_id: "phone", answer: "(555) 123-4567" }
        ]
      }), { status: 200, headers: { 'content-type': 'application/json' } });
    }

    if (url.includes("/api/extension/learning/sync")) {
      console.log("✅ Learning sync endpoint called");
      return new Response(JSON.stringify({ status: "accepted" }), {
        status: 202,
        headers: { 'content-type': 'application/json' }
      });
    }

    return originalFetch(url, options);
  };

  try {
    // Check if the extension functions are available
    if (typeof window.__APPLYLENS__ === "undefined") {
      console.error("❌ Extension not loaded - __APPLYLENS__ global not found");
      return;
    }

    console.log("✅ Extension global found");

    // Run scan and suggest
    console.log("🚀 Running scanAndSuggest...");
    await window.__APPLYLENS__.runScanAndSuggest();

    // Wait a bit for async operations
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Check results
    console.log("📋 Test Results:");
    console.log("  Profile fetched:", profileFetched ? "✅" : "❌");
    console.log("  Generate answers fetched:", generateAnswersFetched ? "✅" : "❌");

    // Check if panel was created
    const panel = document.getElementById("__applylens_panel__");
    console.log("  Panel created:", panel ? "✅" : "❌");

    if (panel) {
      console.log("  Panel content:", panel.querySelector(".body")?.textContent?.slice(0, 100) + "...");
    }

    // Look for integration logs in console
    console.log("🔍 Check console above for '[Learning] Phase 2.1' logs to verify integration");

  } catch (error) {
    console.error("❌ Test failed:", error);
  } finally {
    // Restore fetch
    window.fetch = originalFetch;
  }
})();
