// extension-id.js - Non-module script to expose extension ID in page context
// This file is injected by content-loader.js to provide the extension ID
// to web_accessible_resources scripts running in page context

// The extension ID is set via data-extension-id attribute on the script tag
// Read it and make it available globally
(function() {
  const script = document.currentScript || document.getElementById('applylens-extension-id-script');
  if (script && script.dataset.extensionId) {
    window.__APPLYLENS_EXTENSION_ID__ = script.dataset.extensionId;
    console.log('[ApplyLens] Extension ID set in page context:', window.__APPLYLENS_EXTENSION_ID__);
  } else {
    console.error('[ApplyLens] Could not set extension ID - script or data attribute not found');
  }
})();
