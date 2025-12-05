// content-loader.js - Loads ES module content scripts dynamically
// This is needed because Chrome manifest v3 doesn't support "type": "module" for content_scripts

console.log("[ApplyLens] content-loader.js executing on", location.hostname);

// Expose extension ID to page context via multiple methods for reliability
// 1. Meta tag (CSP-safe, readable from DOM)
const meta = document.createElement('meta');
meta.name = 'applylens-extension-id';
meta.content = chrome.runtime.id;
(document.head || document.documentElement).appendChild(meta);

// 2. Load extension-id.js with data attribute (CSP-safe non-module script)
const idScript = document.createElement('script');
idScript.id = 'applylens-extension-id-script';
idScript.src = chrome.runtime.getURL('extension-id.js');
idScript.dataset.extensionId = chrome.runtime.id;
(document.head || document.documentElement).appendChild(idScript);

console.log("[ApplyLens] Set extension ID:", chrome.runtime.id);

// Create a bridge between chrome.runtime messages and the injected module
// The module runs in page context and doesn't have access to chrome APIs
window.addEventListener('message', (event) => {
  // Only accept messages from same origin
  if (event.source !== window) return;

  // Handle requests from the injected module to chrome APIs
  if (event.data?.type === 'APPLYLENS_TO_EXTENSION') {
    const { action, payload, requestId } = event.data;

    if (action === 'SEND_TO_BACKGROUND') {
      // Forward to background/popup via chrome.runtime
      chrome.runtime.sendMessage(payload, (response) => {
        window.postMessage({
          type: 'APPLYLENS_FROM_EXTENSION',
          requestId,
          response
        }, '*');
      });
    }
  }
});

// Listen for messages from popup/background and forward to injected module
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  console.log("[ApplyLens] Message from extension:", msg.type);

  // Forward to the injected module via postMessage
  window.postMessage({
    type: 'APPLYLENS_EXTENSION_MESSAGE',
    message: msg
  }, '*');

  // Always respond to prevent "message channel closed" errors
  sendResponse({ received: true });
  return false;
});

// Inject contentV2.js as a module script tag instead of dynamic import
// This is more reliable than dynamic import() for content scripts
// IMPORTANT: Wait a tick to ensure the extension ID script has executed
(async () => {
  try {
    // Use setTimeout to ensure the inline script with extension ID executes first
    await new Promise(resolve => setTimeout(resolve, 0));

    console.log("[ApplyLens] Injecting contentV2.js as module script...");
    console.log("[ApplyLens] Verifying extension ID is available:", window.__APPLYLENS_EXTENSION_ID__);

    const script = document.createElement('script');
    script.type = 'module';
    script.src = chrome.runtime.getURL('contentV2.js');

    script.onload = () => {
      console.log("[ApplyLens] contentV2.js module loaded successfully");
    };

    script.onerror = (err) => {
      console.error("[ApplyLens] Error loading contentV2.js module:", err);
    };

    // Inject into page
    (document.head || document.documentElement).appendChild(script);

  } catch (err) {
    console.error("[ApplyLens] Error injecting content script:", err);
    console.error("[ApplyLens] Error stack:", err.stack);
    console.error("[ApplyLens] Error name:", err.name);
    console.error("[ApplyLens] Error message:", err.message);
  }
})();
