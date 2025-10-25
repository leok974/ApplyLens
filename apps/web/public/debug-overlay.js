// Diagnostic script to detect stealth overlays blocking UI interactions
// Paste in browser DevTools Console

(() => {
  const el = document.elementFromPoint(
    Math.round(window.innerWidth * 0.25),
    Math.round(window.innerHeight * 0.35)
  );

  console.log("🔍 Top element under cursor:", el);

  if (!el) {
    console.warn("⚠️ No element found at cursor position");
    return;
  }

  const cs = getComputedStyle(el);

  console.table({
    tag: el.tagName,
    id: el.id || "(none)",
    className: el.className || "(none)",
    zIndex: cs.zIndex,
    opacity: cs.opacity,
    pointerEvents: cs.pointerEvents,
    position: cs.position,
    display: cs.display,
    visibility: cs.visibility
  });

  // Check if element is blocking interactions
  if (cs.pointerEvents === "auto" && parseFloat(cs.opacity) < 0.1) {
    console.error("🚨 FOUND STEALTH OVERLAY: Element has pointer-events: auto but is nearly invisible!");
    console.log("Element:", el);
    console.log("Fix: Add pointer-events-none when hidden");
  } else if (cs.pointerEvents === "none") {
    console.info("✅ Element properly set to pointer-events: none (non-blocking)");
  } else {
    console.info("ℹ️ Element is interactive (pointer-events: auto)");
  }

  // Check for fixed overlays in the document
  console.log("\n🔍 Checking for all fixed/absolute overlays...");
  const overlays = Array.from(document.querySelectorAll('[class*="fixed"], [class*="absolute"]'))
    .filter(el => {
      const style = getComputedStyle(el);
      return (style.position === 'fixed' || style.position === 'absolute') &&
             style.zIndex !== 'auto' &&
             parseInt(style.zIndex) >= 30;
    });

  if (overlays.length > 0) {
    console.log(`Found ${overlays.length} high z-index overlays:`);
    overlays.forEach((overlay, i) => {
      const style = getComputedStyle(overlay);
      console.log(`  ${i + 1}. ${overlay.tagName}.${overlay.className.split(' ')[0]} - z: ${style.zIndex}, pointer-events: ${style.pointerEvents}, opacity: ${style.opacity}`);
    });
  } else {
    console.log("✅ No high z-index overlays found");
  }
})();
