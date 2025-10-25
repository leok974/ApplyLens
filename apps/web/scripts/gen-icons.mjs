// Generate all icon sizes from PNG master with aggressive trim
// Run: pnpm --filter @apps/web icons

import sharp from "sharp";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

const SRC = "public/ApplyLensLogo.png"; // PNG master
const OUT = "public";
mkdirSync(OUT, { recursive: true });

// Helper: load -> trim transparent padding -> square -> resize
async function render(size, outName) {
  const buf = await sharp(SRC)
    .trim() // remove outer transparent padding (max visual size)
    .resize(size, size, { fit: "cover" }) // fill square
    .png({ compressionLevel: 9 })
    .toBuffer();
  await sharp(buf).toFile(join(OUT, outName));
  console.log(`✓ Generated ${outName} (${size}x${size})`);
}

console.log("🎨 Generating icons from PNG...\n");

// Standard icon sizes for PWA
const sizes = [16, 32, 48, 64, 180, 192, 256, 384, 512];
for (const s of sizes) {
  await render(s, `icon-${s}x${s}.png`);
}

// Separate favicon sizes (browsers pick best)
await render(16, "favicon-16.png");
await render(32, "favicon-32.png");
await render(48, "favicon-48.png");

// Note: Sharp doesn't support .ico output, but modern browsers prefer PNG anyway
// For legacy .ico support, use favicon-48.png as fallback
console.log("\n💡 Note: Modern browsers use PNG favicons. Legacy .ico not needed.");

// Maskable icons (Android - full bleed with safe zone)
console.log("\n🤖 Creating maskable icons for Android...");
await render(192, "icon-192x192-maskable.png");
await render(512, "icon-512x512-maskable.png");

console.log("\n✅ All PNG-based icons generated in", OUT);
console.log("📱 Re-add to home screen on mobile to see updated icons");
